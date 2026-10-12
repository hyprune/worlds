#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Resident (world format 0.9 character) audit of a world package.

Core and hyprune-world-check own route walkability (RFC-0004 0.9 amendment,
RFC-0011 "Walkability (routes)"). This tool re-applies the same per-sample
rules offline and adds the release gates the tooling owns:

- render-only props: the same body box clear of every visible triangle above step
  height, so a route never walks through, and a seat never sits in, a prop without
  collision (core's checks see collision only);
- walkability, core's rules: every 0.25 m along the route an upward collision
  surface (normal y >= 0.65) within 0.35 m of the previous floor; the body box
  (0.85 r across, from 0.21 m to the body height) clear of collision; inside
  the playable union; the probe (0.5 r, 0.2-1.0 m) outside screen approach
  zones (each anchor's width + 0.3 m a side, 1.5 m deep, floor + 0.1 m to its
  top edge);
- navmesh: every route sample on the default spawn's Recast island (agent 0.3 m,
  climb 0.35 m, route slope 0.4), and at least DOOR (1.2 m) clear width across
  the route between collision faces;
- stops: not in keepClear volumes, and at least STOP_MARGIN from every approach
  zone, so a resident never waits in front of a screen;
- seats: each seat stop's legs (route point -> approach point -> anchor) pass
  the walkability rules (the last step, into the seat, against collision only),
  the seated pelvis (core moves the root back from the anchor by the sit clip's
  travel, hips over the root) has seat top under it with at least SEAT_MARGIN to
  the seat's front edge and to both ends, the bench clears all other geometry
  (render and collision, stairs and rails included) by BENCH_CLEARANCE from its
  floor to SITTER_HEIGHT above the seat,
  and with --npc-check (core's hyprune-npc-check) the character fits the anchor
  (feet clearance = height - seatHeight - ankle sink within [-0.03, 0.45] m,
  core's seat fit; otherwise core turns the stop into a plain stop);
- guides: the join leg from every route sample of the guiding resident to the
  guide path's start is walkable (core refuses a guide whose join is blocked);
- limits: 16 characters, 8 per path, 1-8 say lines of 1-160 characters, and at most
  CAPTION characters per line: core draws the line as a one-line caption (440 px at
  1080p) and cuts longer ones.

  check-residents.py PACKAGE [--npc-check BIN] [--output REPORT.json]
"""
import argparse, json, math, subprocess, sys
from pathlib import Path
import numpy as np
sys.path.insert(0, str(Path(__file__).parent))
from gltf_io import load
from raycast import Triangles
import navmesh_io

STEP, MAX_STEP, NAV_SAMPLE, DOOR, STOP_MARGIN, CAPTION = .25, .35, .5, 1.2, .5, 38
SEAT_MARGIN, BENCH_CLEARANCE, SITTER_HEIGHT = .15, .3, 1.3
DESIGN_SLOPE = math.degrees(math.atan(.4))
TOL = (.15, .5, .15)

p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
p.add_argument('package', type=Path); p.add_argument('--npc-check', type=Path); p.add_argument('--output', type=Path)
a = p.parse_args()
scene = load(a.package); m = scene.manifest
tri = navmesh_io.collision_triangles(scene)
C = object.__new__(Triangles); C._set(tri, np.array(['collision']*len(tri)), np.ones(len(tri), bool))
R = Triangles(scene)
nrm = np.cross(tri[:, 1]-tri[:, 0], tri[:, 2]-tri[:, 0]); nrm /= np.maximum(np.linalg.norm(nrm, axis=1), 1e-12)[:, None]


def rnd(v, n=2): return [round(float(x), n) for x in v]


def qrot(q, v):
    x, y, z, w = q; u = np.array([x, y, z]); v = np.asarray(v, float)
    return v + 2*np.cross(u, np.cross(u, v) + w*v)


# ---- core's segment geometry (sim/Route.hpp): 24 samples per segment -------
def route(points, closed):
    pos = [np.array(pt['position'], float) for pt in points]; types = [pt.get('type', 'line') for pt in points]
    closed = closed and len(pos) > 2; n = len(pos); samples = [pos[0]]; dist = [0.]; marks = [0.]
    for i in range(1, n + (1 if closed else 0)):
        A, B, before = pos[(i-1) % n], pos[i % n], pos[(i-2 if i > 1 else 0) % n]; kind = types[i % n]
        for k in range(1, 25):
            t = k/24; q = A + (B-A)*t
            if kind == 'curve':
                tan = (B-before)*.5
                q = A*(2*t**3-3*t**2+1) + tan*(t**3-2*t**2+t) + B*(-2*t**3+3*t**2) + (B-A)*(t**3-t**2)
            if kind == 'arc':
                c = np.cross(B-A, [0, 1, 0]); q = q + c/max(np.linalg.norm(c), 1e-9)*math.sin(t*math.pi)*np.linalg.norm(B-A)*.3
            dist.append(dist[-1] + float(np.linalg.norm(q-samples[-1]))); samples.append(q)
        marks.append(dist[-1])
    return np.array(samples), np.array(dist), marks


def at(samples, dist, s):
    i = min(max(int(np.searchsorted(dist, s, 'right'))-1, 0), len(samples)-2); span = dist[i+1]-dist[i]
    return samples[i] + (samples[i+1]-samples[i])*(0 if span < 1e-6 else min(max((s-dist[i])/span, 0), 1))


def tangent(samples, dist, s):
    i = min(max(int(np.searchsorted(dist, s, 'right'))-1, 0), len(samples)-2); d = samples[i+1]-samples[i]; d[1] = 0
    n = np.linalg.norm(d); return d/n if n > 1e-9 else np.array([0, 0, 1.])


# ---- core's walkability (interaction/Walkability.cpp) ----------------------
def floor_below(origin, down):
    lo = origin - [1e-3, down+1e-3, 1e-3]; hi = origin + [1e-3, 1e-3, 1e-3]; cand = C.near(lo, hi)
    if not len(cand): return None
    t = tri[cand]; d = np.array([0, -down, 0.]); e1 = t[:, 1]-t[:, 0]; e2 = t[:, 2]-t[:, 0]; pv = np.cross(d, e2); det = (e1*pv).sum(1)
    ok = np.abs(det) > 1e-12; inv = np.divide(1, det, out=np.zeros_like(det), where=ok); s = origin-t[:, 0]
    u = (s*pv).sum(1)*inv; qv = np.cross(s, e1); v = (qv@d)*inv; h = (e2*qv).sum(1)*inv
    hit = ok & (u >= 0) & (v >= 0) & (u+v <= 1) & (h >= 0) & (h <= 1)
    if not hit.any(): return None
    i = np.argmin(np.where(hit, h, np.inf))
    return None if abs(nrm[cand[i], 1]) < .65 else float(origin[1]-h[i]*down)


def floor_at(root, within=MAX_STEP): return floor_below(np.asarray(root, float)+[0, within+.05, 0], 2*within+.05)


def aabb_hits(centre, half, T=None):
    """Triangle / axis-aligned box SAT against collision (or another Triangles set)."""
    T = T or C; cand = T.near(centre-half, centre+half)
    if not len(cand): return False
    v = T.tri[cand]-centre; e = [v[:, 1]-v[:, 0], v[:, 2]-v[:, 1], v[:, 0]-v[:, 2]]; sep = np.zeros(len(cand), bool)
    for k in range(3):
        sep |= (v[:, :, k].min(1) > half[k]) | (v[:, :, k].max(1) < -half[k])
    n = np.cross(e[0], e[1]); r = np.abs(n)@half; d = (n*v[:, 0]).sum(1); sep |= np.abs(d) > r
    for ei in e:
        for ax in np.eye(3):
            axis = np.cross(ax, ei); pr = np.einsum('nk,nvk->nv', axis, v); r = np.abs(axis)@half
            sep |= (pr.min(1) > r) | (pr.max(1) < -r)
    return bool((~sep).any())


def obb_overlap(c1, ax1, h1, c2, ax2, h2):
    ax1 = np.asarray(ax1); ax2 = np.asarray(ax2); d = c2-c1
    axes = list(ax1)+list(ax2)+[np.cross(x, y) for x in ax1 for y in ax2]
    for L in axes:
        if np.linalg.norm(L) < 1e-6: continue
        r1 = sum(h*abs(np.dot(x, L)) for h, x in zip(h1, ax1)); r2 = sum(h*abs(np.dot(x, L)) for h, x in zip(h2, ax2))
        if abs(np.dot(d, L)) > r1+r2: return False
    return True


def approach_zones():
    zones = []
    for an in m['anchors']:
        if 'pose' not in an or 'size' not in an: continue
        c = np.array(an['pose']['position'], float); q = an['pose']['rotation']; w, h = an['size']
        n = qrot(q, [0, 0, 1]); hn = np.array([n[0], 0, n[2]])
        if np.linalg.norm(hn) < .5: continue
        hn /= np.linalg.norm(hn); right = np.cross([0, 1, 0], hn); front = c+n*.75; top = c[1]+h/2
        fl = floor_below(front, 60); fl = c[1]-h/2 if fl is None else fl; low = fl+.1
        if top <= low: continue
        zones.append({'id': an['id'], 'centre': np.array([front[0], (low+top)/2, front[2]]), 'axes': [right, np.array([0, 1., 0]), hn],
                      'half': [w/2+.3, (top-low)/2, .75]})
    return zones


ZONES = approach_zones(); EYE3 = np.eye(3)
playable = [(np.array(v['min'], float), np.array(v['max'], float)) for ar in m.get('areas', []) for v in ar.get('playable', {}).get('volumes', [])]
cap = m.get('playable', {}).get('maxFlyHeight')


def in_playable(p):
    if cap is not None and p[1] > cap: return False
    return not playable or any(np.all(p >= lo) and np.all(p <= hi) for lo, hi in playable)


def zone_gap(feet, radius=.35):
    """Distance from the approach probe to the nearest zone (0 = inside), coarse."""
    best = math.inf
    for z in ZONES:
        rel = feet+[0, .6, 0]-z['centre']; out = 0.
        for ax, h in zip(z['axes'], z['half']): out = math.hypot(out, max(0., abs(float(np.dot(rel, ax)))-h-(radius*.5 if ax[1] == 0 else .4)))
        best = min(best, out)
    return best


def check_spot(root, body, keep=None, render=True):
    fl = floor_at(root)
    if fl is None: return ('floor', root)
    feet = np.array([root[0], fl, root[2]])
    bottom, top = MAX_STEP*.6, body['height']; half = np.array([body['radius']*.85, (top-bottom)/2, body['radius']*.85])
    if aabb_hits(feet+[0, (bottom+top)/2, 0], half): return ('walls', feet)
    if render and aabb_hits(feet+[0, (bottom+top)/2, 0], half, R): return ('render', feet)
    if not in_playable(feet+[0, .05, 0]): return ('playable', feet)
    probe_c, probe_h = feet+[0, .6, 0], [body['radius']*.5, .4, body['radius']*.5]
    for z in ZONES:
        if obb_overlap(probe_c, EYE3, probe_h, z['centre'], z['axes'], z['half']): return ('approach', feet)
    for k in keep or []:
        if obb_overlap(probe_c, EYE3, probe_h, (k[0]+k[1])/2, EYE3, (k[1]-k[0])/2): return ('keep-clear', feet)
    return None


def check_samples(pts, body, limit=8, render=True):
    out = []; previous = None
    for p0 in pts:
        p = np.array(p0, float)
        if previous is not None: p[1] = previous
        prob = check_spot(p, body, render=render)
        if prob:
            rule = 'ledge' if prob[0] == 'floor' and previous is not None else prob[0]
            out.append({'rule': rule, 'at': rnd(prob[1])}); previous = None
            if len(out) >= limit: break
            continue
        previous = floor_at(p)
    return out


def walk(samples, dist, body, limit=8):
    L = dist[-1]; along = list(np.arange(0, L, STEP))+[L]
    return check_samples([at(samples, dist, s) for s in along], body, limit)


def leg(a_, b_, body, render=True):
    a_, b_ = np.asarray(a_, float), np.asarray(b_, float); L = float(np.linalg.norm(b_-a_))
    return check_samples([a_+(b_-a_)*(s/L if L > 0 else 0) for s in list(np.arange(0, L, STEP))+[L]], body, 1, render)


# ---- seats: where the pelvis lands, and room around the bench ---------------
def seat_top(p, top):
    """Is there seat surface (render geometry) at p, at height `top` (within 4 cm)?"""
    hit = R.first_hit(np.array([p[0], top+.25, p[2]]), np.array([p[0], top-.25, p[2]]))
    return bool(hit) and abs(hit['point'][1]-top) <= .04


def march(p, d, top, reach=3.0):
    """Distance from p along d to where the seat top ends (0: no seat at p)."""
    if not seat_top(p, top): return 0.
    for k in range(1, int(reach/.01)+1):
        if not seat_top(p+d*(k*.01), top): return round((k-1)*.01, 3)
    return reach


def bench_obstacles(rect, top, floor):
    """Geometry within BENCH_CLEARANCE of a seat rectangle, other than the bench."""
    c, fwd, right, (f0, f1), (r0, r1) = rect
    out = []
    for T, kind in [(R, 'render'), (C, 'collision')]:
        g0, g1 = f0-BENCH_CLEARANCE, f1+BENCH_CLEARANCE; h0, h1 = r0-BENCH_CLEARANCE, r1+BENCH_CLEARANCE
        corners = [c+fwd*f+right*r for f in (g0, g1) for r in (h0, h1)]
        lo = np.min(corners, 0); hi = np.max(corners, 0); lo[1] = floor+.05; hi[1] = top+SITTER_HEIGHT
        for i in T.near(lo, hi):
            v = T.tri[i]; lf = (v-c)@fwd; lr = (v-c)@right
            if v[:, 1].max() <= floor+.05: continue                               # the floor
            if lf.min() >= f0-.05 and lf.max() <= f1+.05 and lr.min() >= r0-.05 and lr.max() <= r1+.05 and v[:, 1].max() <= top+.02:
                continue                                                           # the bench itself
            if lf.max() < g0 or lf.min() > g1 or lr.max() < h0 or lr.min() > h1 or v[:, 1].max() < floor+.05 or v[:, 1].min() > top+SITTER_HEIGHT:
                continue
            out.append({'kind': kind, 'key': str(T.keys[i]), 'at': rnd(v.mean(0))})
    return out


# ---- clear width (check-navmesh.py's metric) --------------------------------
def clear_width(pt, side, reach=10):
    best = [reach, reach]
    for h in np.linspace(MAX_STEP+.05, 1.75, 5):
        o = np.array(pt)+[0, h, 0]
        for k, sg in enumerate((1, -1)):
            hit = C.first_hit(o, o+np.array(side)*sg*reach)
            if hit: best[k] = min(best[k], hit['t']*reach)
    return sum(best)


# ---- characters --------------------------------------------------------------
assets = {x['id']: x for x in m.get('objectAssets', [])}
def asset_manifest(aid):
    x = assets[aid]
    if 'dir' in x: return json.loads((a.package/x['dir']/'object.json').read_text())
    return {'traits': x.get('traits', {})}
chars = {}
for o in m.get('objects', []):
    om = asset_manifest(o['asset']); ch = om.get('traits', {}).get('character')
    if not ch: continue
    body = {'radius': ch.get('radius', .35), 'height': ch.get('height', 1.8)}
    fit = None
    if a.npc_check and 'dir' in assets[o['asset']]:
        r = json.loads(subprocess.run([str(a.npc_check), str(a.package/assets[o['asset']]['dir']/om['scene']), '--json'], capture_output=True, text=True, check=True).stdout)
        sit = next((x for x in r.get('clips', []) if x['name'] == 'sit'), None)
        fit = {'seatHeight': r.get('seatHeight'), 'sink': r.get('sitSink'),
               'travel': min(.8, max(0., sit['speed']*sit['seconds'])) if sit else None}
        if 'sit' in om['traits']['character']['clips'] and om['traits']['character']['clips']['sit'].get('seatHeight') is not None:
            fit['seatHeight'] = om['traits']['character']['clips']['sit']['seatHeight']
    chars[o['id']] = {'instance': o, 'body': body, 'fit': fit, 'walk': om['traits']['character']['clips'].get('walk', {}).get('speed')}

paths = {x['id']: x for x in m.get('paths', [])}
seats = {x['id']: x for x in m.get('seats', [])}
keep = [(np.array(k['min'], float), np.array(k['max'], float)) for k in m.get('keepClear', [])]
default = m.get('defaultSpawn', m['spawns'][0]['id']); spawn = next(s['pose']['position'] for s in m['spawns'] if s['id'] == default)
failures = []; report = {'package': f"{m['id']} {m['version']}", 'formatVersion': m['formatVersion'], 'characters': len(chars), 'routes': [], 'seats': [], 'benches': [], 'guides': []}
benches_checked = set()
def fail(kind, ident, **kw): failures.append({'kind': kind, 'id': ident, **kw})

if len(chars) > 16: fail('limit', 'characters', count=len(chars))
for pid, path in paths.items():
    bound = [c for c in chars.values() if c['instance'].get('path') == pid]
    if len(bound) > 8: fail('limit', pid, characters=len(bound))
for cid, c in chars.items():
    for it in c['instance'].get('interactions', []):
        if it['action']['type'] == 'say':
            lines = it['action']['lines']
            if not 1 <= len(lines) <= 8 or any(not 1 <= len(x) <= 160 for x in lines): fail('say', f'{cid}/{it["id"]}', lines=len(lines))
            long = [x for x in lines if len(x) > CAPTION]
            if long: fail('say-caption', f'{cid}/{it["id"]}', limit=CAPTION, lines=long)

# Route samples for the navmesh island and widths, collected first (one navmesh build).
routes = {}
for pid, path in paths.items():
    if path.get('use', 'generic') != 'route': continue
    samples, dist, marks = route(path['points'], path.get('closed', False)); routes[pid] = (samples, dist, marks)
nav_points, width_rows = [], []
for pid, (samples, dist, marks) in routes.items():
    for s in np.arange(0, dist[-1]+1e-6, NAV_SAMPLE):
        q = at(samples, dist, s); nav_points.append({'id': f'{pid}@{s:.2f}', 'p': q.tolist(), 'h': list(TOL)})
        t = tangent(samples, dist, s); width_rows.append((pid, round(float(s), 2), q, np.array([-t[2], 0, t[0]])))
nav_points.append({'id': 'spawn', 'p': list(spawn), 'h': list(TOL)})
navmesh_io.require_helper(); nav = navmesh_io.build(tri, DESIGN_SLOPE, nav_points)
hits = {x['id']: x['hit'] for x in nav['points']}; main = hits['spawn']['island'] if hits.get('spawn') else None

for pid, (samples, dist, marks) in routes.items():
    path = paths[pid]; bound = [cid for cid, c in chars.items() if c['instance'].get('path') == pid]
    body = {'radius': max([chars[c]['body']['radius'] for c in bound] or [.35]), 'height': max([chars[c]['body']['height'] for c in bound] + [1.8])}
    problems = walk(samples, dist, body)
    off = [k for k, h in hits.items() if k.startswith(pid+'@') and (not h or h['island'] != main)]
    narrow, widest = [], []
    for rid, s, q, side in width_rows:
        if rid != pid: continue
        fl = floor_at(q); w = clear_width([q[0], q[1] if fl is None else fl, q[2]], side); widest.append(w)
        if w < DOOR: narrow.append({'at': rnd(q), 's': s, 'width': round(w, 2)})
    stops = []
    for st in path.get('stops', []):
        pt = at(samples, dist, marks[st['point']]); fl = floor_at(pt); feet = np.array([pt[0], pt[1] if fl is None else fl, pt[2]])
        row = {'point': st['point'], 'at': rnd(feet), 'seconds': st.get('seconds', 3), 'kind': 'seat' if 'seat' in st else 'face' if 'face' in st else st.get('clip', 'idle'),
               'approachGap': round(zone_gap(feet), 2)}
        if any(obb_overlap(feet+[0, .5, 0], EYE3, [1e-3]*3, (lo+hi)/2, EYE3, (hi-lo)/2) for lo, hi in keep): fail('stop-keep-clear', f'{pid}#{st["point"]}', at=row['at'])
        if row['approachGap'] < STOP_MARGIN: fail('stop-near-screen', f'{pid}#{st["point"]}', at=row['at'], gap=row['approachGap'])
        if 'seat' in st:
            seat = seats.get(st['seat'])
            if not seat: fail('seat', st['seat'], error='not a world seat'); stops.append(row); continue
            sp = np.array(seat['pose']['position'], float); fwd = qrot(seat['pose']['rotation'], [0, 0, 1]); ap = sp+fwd*seat.get('approach', .6)
            legs = leg(feet, ap, body) + leg(ap, sp, body, render=False)
            row.update(seat=st['seat'], legs=legs)
            if legs: fail('seat-legs', f'{pid}#{st["point"]}', seat=st['seat'], problems=legs)
            top = sp[1]+seat['height']; right = np.cross([0, 1., 0], fwd); right /= np.linalg.norm(right)
            for cid in bound:
                f = chars[cid]['fit']
                if not f or f.get('travel') is None: continue
                pelvis = sp - fwd*f['travel']
                ins = {'front': march(pelvis, fwd, top), 'back': march(pelvis, -fwd, top), 'left': march(pelvis, -right, top), 'right': march(pelvis, right, top)}
                row.setdefault('pelvis', {})[cid] = {'at': rnd(pelvis), 'inset': ins}
                if min(ins['front'], ins['left'], ins['right']) < SEAT_MARGIN or ins['back'] < .05:
                    fail('seat-pelvis', f'{cid}@{st["seat"]}', inset=ins, margin=SEAT_MARGIN)
                if ins['front'] > 0:
                    rect = (pelvis, fwd, right, (-ins['back'], ins['front']), (-ins['left'], ins['right']))
                    key = tuple(rnd(pelvis+fwd*(ins['front']-ins['back'])/2+right*(ins['right']-ins['left'])/2, 1))
                    if key not in benches_checked:
                        benches_checked.add(key); near = bench_obstacles(rect, top, sp[1])
                        report['benches'].append({'seat': st['seat'], 'depth': round(ins['front']+ins['back'], 2), 'length': round(ins['left']+ins['right'], 2), 'obstacles': len(near)})
                        if near: fail('bench-clearance', st['seat'], clearance=BENCH_CLEARANCE, near=near[:6], count=len(near))
            for cid in bound:
                f = chars[cid]['fit']
                if f and f['seatHeight'] is not None:
                    clearance = seat['height']-f['seatHeight']-(f['sink'] or 0); row.setdefault('feetClearance', {})[cid] = round(clearance, 3)
                    if not -.03 <= clearance <= .45: fail('seat-fit', f'{cid}@{st["seat"]}', clearance=round(clearance, 3))
            report['seats'].append({'seat': st['seat'], 'route': pid, 'legsWalkable': not legs})
        stops.append(row)
    row = {'id': pid, 'length': round(float(dist[-1]), 2), 'closed': path.get('closed', False), 'residents': bound, 'walkable': not problems, 'problems': problems,
           'navmeshSamples': len([k for k in hits if k.startswith(pid+'@')]), 'offMainIsland': len(off), 'minClearWidth': round(min(widest), 2) if widest else None, 'narrow': narrow[:8], 'stops': stops}
    report['routes'].append(row)
    if problems: fail('walkable', pid, problems=problems)
    if off: fail('navmesh-island', pid, samples=off[:6], count=len(off))
    if narrow: fail('door-width', pid, metric=DOOR, narrow=narrow[:6], count=len(narrow))

# Guides: the join leg from every route sample of the guiding resident.
for cid, c in chars.items():
    for it in c['instance'].get('interactions', []):
        if it['action']['type'] != 'guide': continue
        gid = it['action']['path']; gpath = paths.get(gid)
        if not gpath or gpath.get('use') != 'route': fail('guide', f'{cid}/{it["id"]}', error='guide path is not a route'); continue
        start = np.array(gpath['points'][0]['position'], float); own = routes.get(c['instance'].get('path'))
        blocked, total = [], 0
        if own:
            samples, dist, marks = own
            starts = [at(samples, dist, s) for s in np.arange(0, dist[-1], 1.0)]
            # A seated resident steps off to its seat's approach point first (core), then joins.
            for st in paths[c['instance']['path']].get('stops', []):
                seat = seats.get(st.get('seat', ''))
                if seat: starts.append(np.array(seat['pose']['position'])+qrot(seat['pose']['rotation'], [0, 0, 1])*seat.get('approach', .6))
            for q in starts:
                total += 1; fl = floor_at(q); q = np.array([q[0], q[1] if fl is None else fl, q[2]])
                if leg(q, start, c['body']): blocked.append(rnd(q))
        report['guides'].append({'resident': cid, 'path': gid, 'length': round(float(routes[gid][1][-1]), 2), 'joinSamples': total, 'joinBlocked': len(blocked), 'blockedAt': blocked})
        if blocked: fail('guide-join', f'{cid}/{it["id"]}', blocked=len(blocked), samples=total, at=blocked[:4])

report['status'] = 'FAIL' if failures else 'PASS'; report['failures'] = failures
out = json.dumps(report, indent=1)
if a.output: a.output.write_text(out+'\n')
print(out if not a.output else json.dumps({'status': report['status'], 'failures': [(f['kind'], f['id']) for f in failures]}, indent=1))
sys.exit(1 if failures else 0)
