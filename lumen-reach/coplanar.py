# SPDX-License-Identifier: MIT
"""Same-facing coplanar faces between visual objects (0.11.1).

Core draws with a 24-bit depth buffer and a 0.05 m near plane: faces that share a
plane depth-fight at any distance, and faces a few millimetres apart from about
20 m on (0.5 mm resolution at 20 m, 4 mm at 60 m). The kit builds by stacking
boxes, so slabs, piers, lintels, posts and screen bezels often meet flush and
the baked lighting of the two faces differs, so tiles, deck strips and beams
shimmer as the camera moves. resolve() runs on the separate objects before they are
joined (after spatial() has copied collision, which it never touches):

- Faces are grouped by plane: normals within 0.15 degrees and offsets chained
  within GAP. Pairs from different objects whose interiors overlap count.
- A face entirely covered by such faces of other objects that are level with it
  or in front of it is deleted: it can never be seen without fighting.
- Of a remaining pair, the face behind steps back STEP along its normal; when
  they are level, the face more hidden by the other (by its own area) steps back,
  so the surface that mostly shows stays where it was. An object thinner than
  three steps along the normal is not moved; the other face steps instead, and
  when both are that thin the smaller face comes forward THIN_STEP.

Every action goes to artifacts/lumen-reach/coplanar-report.json, and
tools/check-coplanar-planes.py re-checks the exported package.
"""
import json
from collections import defaultdict
import numpy as np
from mathutils import Vector

GAP = .008
STEP = .012
THIN_STEP = .006
MAX_SHIFT = .05
SKIP_GROUPS = {'foliage', 'atmosphere'}
NORMAL_QUANT = 400  # normal components rounded to 1/400 (about 0.15 degrees)
LAYER = 'coplanar_moved'  # face layer: a face moves at most once over all passes


def _basis(n):
    t = np.array([1., 0, 0]) if abs(n[0]) < .9 else np.array([0, 1., 0])
    u = np.cross(n, t); u /= np.linalg.norm(u)
    return u, np.cross(n, u)


def _inside(pts, tris, margin):
    """pts (k,2) strictly inside any of tris (m,3,2) by `margin` metres (negative: tolerance)."""
    hit = np.zeros(len(pts), bool)
    for a, b, c in tris:
        e = [(a, b), (b, c), (c, a)]
        area = (b[0]-a[0])*(c[1]-a[1])-(b[1]-a[1])*(c[0]-a[0])
        if abs(area) < 1e-12:
            continue
        s = 1 if area > 0 else -1; ok = np.ones(len(pts), bool)
        for p, q in e:
            d = q-p; L = np.hypot(*d)
            side = s*((d[0])*(pts[:, 1]-p[1])-(d[1])*(pts[:, 0]-p[0]))/L
            ok &= side > margin
        hit |= ok
    return hit


def _area(f):
    t = f['tris']
    return float(np.linalg.norm(np.cross(t[:, 1]-t[:, 0], t[:, 2]-t[:, 0]), axis=1).sum()/2)


def _once(bpy, bmesh, groups):
    bpy.context.view_layer.update()
    owners = {}; meshes = {}; faces = []
    for g, obs in groups.items():
        if g in SKIP_GROUPS:
            continue
        for o in obs:
            if o.type != 'MESH' or o.name in owners:
                continue
            owners[o.name] = g
            bm = bmesh.new(); bm.from_mesh(o.data); bm.faces.ensure_lookup_table(); bm.verts.ensure_lookup_table()
            moved = bm.faces.layers.int.get(LAYER) or bm.faces.layers.int.new(LAYER)
            M = np.array(o.matrix_world); R = M[:3, :3]
            V = np.array([v.co[:] for v in bm.verts]); W = V@R.T+M[:3, 3]
            tris = bm.calc_loop_triangles()
            per = defaultdict(list)
            for t in tris:
                per[t[0].face.index].append([l.vert.index for l in t])
            nm = np.linalg.inv(R).T
            meshes[o.name] = {'object': o, 'bm': bm, 'world': W, 'R': R, 'deleted': set(), 'stepped': set(), 'layer': moved}
            for f in bm.faces:
                n = nm@np.array(f.normal[:]); L = np.linalg.norm(n)
                if L < 1e-9 or f.index not in per:
                    continue
                n /= L; w = W[[v.index for v in f.verts]]
                faces.append({'obj': o.name, 'face': f.index, 'n': n, 'd': float(n@w[0]), 'tris': W[np.array(per[f.index])],
                              'verts': [v.index for v in f.verts], 'moved': bool(f[moved])})
    buckets = defaultdict(list)
    for i, f in enumerate(faces):
        buckets[tuple(np.round(f['n']*NORMAL_QUANT).astype(int))].append(i)
    for key, ids in buckets.items():
        u, v = _basis(faces[ids[0]]['n'])
        for i in ids:
            t = faces[i]['tris']; faces[i]['t2'] = np.stack([t@u, t@v], -1); faces[i]['bucket'] = key
            faces[i]['lo'] = faces[i]['t2'].reshape(-1, 2).min(0); faces[i]['hi'] = faces[i]['t2'].reshape(-1, 2).max(0)
    clusters = []
    for ids in buckets.values():
        if len(ids) < 2:
            continue
        ids.sort(key=lambda i: faces[i]['d'])
        cur = [ids[0]]
        for i in ids[1:]:
            if faces[i]['d']-faces[cur[-1]]['d'] <= GAP:
                cur.append(i)
            else:
                clusters.append(cur); cur = [i]
        clusters.append(cur)
    clusters = [c for c in clusters if len({faces[i]['obj'] for i in c}) > 1]
    actions = []

    def overlaps(i, j):
        return (faces[j]['lo'] < faces[i]['hi']-.001).all() and (faces[i]['lo'] < faces[j]['hi']-.001).all()

    def plan(b, direction, shift):
        """A shift (metres) that leaves face b at least STEP (back) or THIN_STEP (forward) clear of
        every other object's overlapping face in its plane bucket, or None past MAX_SHIFT."""
        for _ in range(6):
            nd = faces[b]['d']+direction*shift
            hits = [k for k in buckets[faces[b]['bucket']] if faces[k]['obj'] != faces[b]['obj'] and faces[k]['face'] not in meshes[faces[k]['obj']]['deleted']
                    and abs(faces[k]['d']-nd) < GAP and overlaps(b, k)]
            if not hits:
                return shift
            shift = faces[b]['d']-(min(faces[k]['d'] for k in hits)-STEP) if direction < 0 else max(faces[k]['d'] for k in hits)+THIN_STEP-faces[b]['d']
            if shift > MAX_SHIFT:
                return None
        return None

    def move(b, shift, direction):
        mb = meshes[faces[b]['obj']]; n = faces[b]['n']
        local = np.linalg.solve(mb['R'], direction*shift*n)
        for vi in faces[b]['verts']:
            mb['bm'].verts[vi].co += Vector(tuple(float(x) for x in local))
        mb['stepped'].add(faces[b]['face']); mb['bm'].faces[faces[b]['face']][mb['layer']] = 1
        faces[b]['d'] += direction*shift

    def samples(i):
        lo, hi = faces[i]['lo'], faces[i]['hi']; span = hi-lo
        step = float(np.clip(span.min()/8, .004, .05))
        xs = np.arange(lo[0]+step/2, hi[0], step); ys = np.arange(lo[1]+step/2, hi[1], step)
        if len(xs)*len(ys) > 250000:
            xs = np.linspace(lo[0], hi[0], 502)[1:-1]; ys = np.linspace(lo[1], hi[1], 502)[1:-1]
        g = np.stack(np.meshgrid(xs, ys), -1).reshape(-1, 2)
        return g[_inside(g, faces[i]['t2'], .001)], step

    def neighbours(c, i):
        # Only faces within GAP of this one: a cluster chains planes, so its ends can lie further apart.
        return [j for j in c if faces[j]['obj'] != faces[i]['obj'] and faces[j]['face'] not in meshes[faces[j]['obj']]['deleted']
                and abs(faces[j]['d']-faces[i]['d']) < GAP and overlaps(i, j)]

    for c in clusters:
        # 1. Faces wholly covered by level-or-front faces of other objects.
        for i in c:
            near = [j for j in neighbours(c, i) if faces[j]['d'] >= faces[i]['d']-1e-4]
            if not near:
                continue
            pts, step = samples(i)
            if not len(pts):
                continue
            cov = np.zeros(len(pts), bool)
            for j in near:
                cov |= _inside(pts, faces[j]['t2'], -.001)
            if cov.all():
                meshes[faces[i]['obj']]['deleted'].add(faces[i]['face'])
                actions.append({'action': 'delete', 'object': faces[i]['obj'], 'by': sorted({faces[j]['obj'] for j in near}),
                                'normal': [round(float(x), 3) for x in faces[i]['n']], 'offset': round(faces[i]['d'], 4)})
        # 2. Remaining overlaps: one face of each pair steps back.
        for i in c:
            mi = meshes[faces[i]['obj']]
            if faces[i]['face'] in mi['deleted']:
                continue
            for j in neighbours(c, i):
                if j < i or abs(faces[i]['d']-faces[j]['d']) >= GAP:
                    continue
                pi, si = samples(i); pj, sj = samples(j)
                oi = _inside(pi, faces[j]['t2'], .001).mean() if len(pi) else 0
                oj = _inside(pj, faces[i]['t2'], .001).mean() if len(pj) else 0
                area = oi*len(pi)*si*si if len(pi) else 0
                if oi == 0 and oj == 0 or area < 1e-4:
                    continue
                dd = faces[i]['d']-faces[j]['d']
                back, front = (j, i) if dd > 1e-4 else (i, j) if dd < -1e-4 else ((i, j) if oi >= oj else (j, i))
                done = False
                for b, f in [(back, front), (front, back)]:
                    if faces[b]['moved'] or faces[b]['face'] in meshes[faces[b]['obj']]['stepped']:
                        continue
                    # The stepped face moves STEP behind the other face's plane (its offset can lie up to GAP ahead).
                    shift = plan(b, -1, STEP+max(0., faces[b]['d']-faces[f]['d']))
                    if shift is None or np.ptp(meshes[faces[b]['obj']]['world']@faces[b]['n']) < 2.5*shift:
                        continue
                    actions.append({'action': 'step', 'object': faces[b]['obj'], 'behind': faces[f]['obj'], 'metres': round(shift, 4),
                                    'overlapM2': round(float(area), 4), 'normal': [round(float(x), 3) for x in faces[b]['n']], 'offset': round(faces[b]['d'], 4)})
                    move(b, shift, -1); done = True
                    break
                if done:
                    continue
                # Both too thin to step back (sigil strokes, bolt heads): the smaller face comes forward instead.
                for f in sorted([i, j], key=lambda k: _area(faces[k])):
                    b = j if f == i else i
                    if faces[f]['moved'] or faces[f]['face'] in meshes[faces[f]['obj']]['stepped']:
                        continue
                    shift = plan(f, 1, THIN_STEP+max(0., faces[b]['d']-faces[f]['d']))
                    if shift is None:
                        continue
                    actions.append({'action': 'forward', 'object': faces[f]['obj'], 'ahead': faces[b]['obj'], 'metres': round(shift, 4),
                                    'overlapM2': round(float(area), 4), 'normal': [round(float(x), 3) for x in faces[f]['n']], 'offset': round(faces[f]['d'], 4)})
                    move(f, shift, 1); done = True
                    break
                if not done:
                    actions.append({'action': 'unresolved', 'objects': [faces[i]['obj'], faces[j]['obj']], 'overlapM2': round(float(area), 4)})
    for name, m in meshes.items():
        if m['deleted'] or m['stepped']:
            bm = m['bm']
            if m['deleted']:
                bmesh.ops.delete(bm, geom=[bm.faces[k] for k in sorted(m['deleted'])], context='FACES_ONLY')
            bm.to_mesh(m['object'].data); m['object'].data.update()
        m['bm'].free()
    return actions


def resolve(bpy, bmesh, groups, report_path, passes=8):
    """Repeat until a pass changes nothing: a stepped face can land in a third face's plane."""
    actions = []
    for k in range(passes):
        done = _once(bpy, bmesh, groups)
        actions += [{**a, 'pass': k+1} for a in done]
        if not any(a['action'] != 'unresolved' for a in done):
            break
    for obs in groups.values():
        for o in obs:
            if o.type == 'MESH' and LAYER in o.data.attributes:
                o.data.attributes.remove(o.data.attributes[LAYER])
    counts = defaultdict(int)
    for a in actions:
        counts[a['action']] += 1
    report = {'gapMetres': GAP, 'stepMetres': STEP, 'thinStepMetres': THIN_STEP, 'passes': k+1, 'counts': dict(counts), 'actions': actions}
    report_path.write_text(json.dumps(report, indent=1)+'\n')
    return report
