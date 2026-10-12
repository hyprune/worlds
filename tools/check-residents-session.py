#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Nested check of a world's residents (world format 0.9, IPC 0.23), through core's
harness (it isolates and locks the session):

  CORE/dev/nested/run.sh tools/check-residents-session.py --core CORE --package PKG --output DIR

Reads the residents from the package's world.json. Checks, with stills in DIR:
- every authored character is bound to its route and walks at about its clip speed;
- every seat stop is taken: the resident sits on the named seat (sit_idle, root
  lifted by the seat fit), then stands and walks on;
- every resident reaches each of its stops;
- aimed, each resident offers its interactions; say shows the lines in order and E
  advances and ends them; waypoint sets the waypoint; guide walks its path ahead of
  the player (who follows), reaches the end and returns to its route;
- frames: at poses where no resident is in view, npc_motion always renders no more
  frames than npc_motion off (render on demand); in view, animating residents do.
Writes DIR/residents-session.json.
"""
import argparse, json, math, os, shutil, subprocess, sys, time
from pathlib import Path
from types import SimpleNamespace
p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
p.add_argument('--core', type=Path, required=True); p.add_argument('--package', type=Path, required=True)
p.add_argument('--output', type=Path, required=True); p.add_argument('--window', type=float, default=420, help='seconds to watch the routes')
a = p.parse_args(); a.output = a.output.resolve(); a.output.mkdir(parents=True, exist_ok=True); a.package = a.package.resolve()
sys.path.insert(0, str(a.core.resolve()/'dev/nested'))
import session as s, npcs
from m2 import wait, keys
M = json.loads((a.package/'world.json').read_text())
PATHS = {x['id']: x for x in M.get('paths', [])}; SEATS = {x['id']: x for x in M.get('seats', [])}
ASSETS = {x['id']: x for x in M.get('objectAssets', [])}
RESIDENTS = [o for o in M['objects'] if 'dir' in ASSETS.get(o['asset'], {}) and 'path' in o]
WALK = {o['id']: json.loads((a.package/ASSETS[o['asset']]['dir']/'object.json').read_text())['traits']['character']['clips']['walk']['speed'] for o in RESIDENTS}
AREA = {o['id']: next((z['id'] for z in M['zones'] if all(z['bounds']['min'][i] - 1 <= PATHS[o['path']]['points'][0]['position'][i] <= z['bounds']['max'][i] + 1 for i in range(3))), '?') for o in RESIDENTS}
FREE = (0, 1, 2)  # core's NpcAgent modes Idle, Walk, Stop: free to start an interaction
report = {'package': f"{M['id']} {M['version']}", 'formatVersion': M['formatVersion'], 'checks': [], 'stills': {}}


def save(): (a.output/'residents-session.json').write_text(json.dumps(report, indent=1)+'\n')


def check(name, ok, data=None):
    report['checks'].append({'name': name, 'ok': bool(ok), 'evidence': data}); save()
    print(('PASS' if ok else 'FAIL'), 'residents:', name, json.dumps(data)[:240] if data is not None else '', flush=True)
    return ok


def prepare(installed):
    target = installed/M['id']; shutil.rmtree(target, ignore_errors=True); shutil.copytree(a.package, target)
    for name in ['editor.json', 'editor.json.v1', 'layout.json', 'input.json', 'graphics.json']: (s.STATE/name).unlink(missing_ok=True)


def acceptance(client, children, args, shell_token, socketpath):
    children.append(s.envrun('wtype', '-s', '300000')); time.sleep(.2)
    device = s.envrun(str(s.ROOT/'build/nested-pointer'), 'serve', stdin=subprocess.PIPE, stdout=subprocess.PIPE, text=True); children.append(device)
    def pointer(*x):
        device.stdin.write(' '.join(map(str, x))+'\n'); device.stdin.flush(); assert device.stdout.readline().strip() == 'ok'; time.sleep(.08)
    def center():
        for _ in range(4):
            xy = list(map(float, s.ctl('cursorpos').split(','))); pointer(2560-xy[0], 540-xy[1]); time.sleep(.04)
    sub = client.call('state.subscribe', {'topics': ['state']})['subscriptionId']
    state = lambda: client.call('state.snapshot', {'subscriptionId': sub})['snapshot']['state']
    diag = lambda: s.camera()['npcs']
    agent = lambda id_: next((x for x in diag()['agents'] if x['id'] == id_), None)
    instance = lambda id_: next((i for i in state()['objects']['instances'] if i['id'] == id_), None)
    def camera(pos, yaw, pitch=0.): s.ctl('eval', f'hl.plugin.hyprune.camera({pos[0]},{pos[1]},{pos[2]},{yaw},{pitch})')
    def look(eye, target):
        d = [target[i]-eye[i] for i in range(3)]; camera(eye, math.atan2(d[0], -d[2]), math.atan2(d[1], math.hypot(d[0], d[2]))); time.sleep(.25)
    def facing(id_, distance, side=0., height=1.7):
        x = agent(id_); q = x['position']; h = x['heading']; f = [math.sin(h), math.cos(h)]; left = [f[1], -f[0]]
        eye = [q[0]+f[0]*distance+left[0]*side, q[1]+height, q[2]+f[1]*distance+left[1]*side]; look(eye, [q[0], q[1]+1.1, q[2]]); return eye
    def shot(name):
        path = a.output/name; subprocess.run([str(s.HERE/'ctl.py'), 'shot', str(path)], check=True, stdout=subprocess.DEVNULL); report['stills'][name] = name; return path
    def fps(seconds=3.):
        f0 = s.camera()['frames']; time.sleep(seconds); return (s.camera()['frames']-f0)/seconds
    def motion(value): client.call('graphics.set', {'patch': {'npc_motion': value}}); time.sleep(.4)

    s.ctl('eval', 'hl.config({misc={disable_watchdog_warning=true},cursor={inactive_timeout=1}})')
    s.ctl('eval', 'hl.dispatch(hl.dsp.focus({ monitor = "HEADLESS-1" }))')
    client.call('world.load', {'worldId': M['id']})
    s.ctl('eval', 'hl.plugin.hyprune.toggle("HEADLESS-1")'); wait(lambda: s.camera()['active'], timeout=90); time.sleep(2)
    client.call('movement.set', {'modeId': 'com.hyprune.fly'})
    client.call('graphics.set', {'patch': {'offload': 'off', 'npc_motion': 'always'}}); center()
    wait(lambda: len(diag()['agents']) == len(RESIDENTS), timeout=30)
    st = state(); chars = {i['id']: i for i in st['objects']['instances'] if i['character']}
    check('authored residents bound to their routes', all(chars.get(o['id'], {}).get('path') == 'package/'+o['path'] for o in RESIDENTS) and
          st['npcs']['usage']['authored'] == len(RESIDENTS) and st['npcs']['state'] == 'animating',
          {k: {'path': v['path'], 'activity': v['activity']} for k, v in chars.items()})
    paths = {x['id']: x for x in client.call('paths.list', {})['paths']}
    check('paths.list: every route walkable', all(paths['package/'+k]['walkable'] if 'package/'+k in paths else paths[k]['walkable'] for k, v in PATHS.items() if v.get('use') == 'route'),
          {k: (v['walkable'], v['problems'][:1]) for k, v in paths.items()})

    # Watch the routes: walking speed, stops reached, each seat taken (with a still).
    stops = {o['id']: [{'point': x['point'], 'at': PATHS[o['path']]['points'][x['point']]['position'], 'seat': x.get('seat'), 'best': 99.} for x in PATHS[o['path']].get('stops', [])] for o in RESIDENTS}
    speeds = {o['id']: [] for o in RESIDENTS}; seated = {}; stood = {}; last = {}
    t0 = time.monotonic(); look([20, 40, -70], [40, 0, -100])
    while time.monotonic()-t0 < a.window and not (len(stood) == len(RESIDENTS) and all(x['best'] < .6 for v in stops.values() for x in v)):
        now = time.monotonic(); d = diag()
        for x in d['agents']:
            id_ = x['id']
            if id_ not in stops: continue
            prev = last.get(id_)
            if x['activity'] != 'walking' or not prev: last[id_] = (now, x)
            elif now-prev[0] >= 1.0:
                speeds[id_].append(math.hypot(x['position'][0]-prev[1]['position'][0], x['position'][2]-prev[1]['position'][2])/(now-prev[0])); last[id_] = (now, x)
            for stp in stops[id_]: stp['best'] = min(stp['best'], math.hypot(x['position'][0]-stp['at'][0], x['position'][2]-stp['at'][2]))
            if x['activity'] == 'sitting' and x['clip'] == 'sit_idle' and x['seat'] and id_ not in seated:
                seated[id_] = {'seat': x['seat'], 'seatOffset': x['seatOffset'], 'position': x['position'], 'heading': x['heading'], 't': round(now-t0, 1)}
                seat = SEATS.get(x['seat'].split('/')[-1]); sp = seat['pose']['position'] if seat else x['position']; h = x['heading']; f = [math.sin(h), math.cos(h)]; side = [f[1], -f[0]]
                look([sp[0]+f[0]*2.4+side[0]*1.3, sp[1]+1.25, sp[2]+f[1]*2.4+side[1]*1.3], [x['position'][0], sp[1]+.55, x['position'][2]]); time.sleep(.6)
                shot(f'seated-{AREA[id_]}.png'); look([20, 40, -70], [40, 0, -100])
            if id_ in seated and id_ not in stood and x['activity'] == 'walking' and seated[id_]['seat'] not in d.get('seatsTaken', []):
                stood[id_] = round(now-t0, 1)
        time.sleep(.25)
    for o in RESIDENTS:
        v = sorted(speeds[o['id']]); med = v[len(v)//2] if v else 0
        check(f"{o['id']} walks at about its walk clip speed ({WALK[o['id']]:.2f} m/s)", len(v) >= 3 and .75*WALK[o['id']] < med < 1.25*WALK[o['id']], {'median': round(med, 3), 'samples': len(v)})
        want = next((x['seat'] for x in PATHS[o['path']].get('stops', []) if 'seat' in x), None)
        got = seated.get(o['id'])
        check(f"{o['id']} sits on {want}, then stands and walks on", got and got['seat'].split('/')[-1] == want and got['seatOffset'] > .1 and o['id'] in stood,
              {'seated': got, 'stoodAt': stood.get(o['id'])})
        check(f"{o['id']} reaches each of its stops", all(x['best'] < .6 for x in stops[o['id']]), [{'point': x['point'], 'closest': round(x['best'], 2)} for x in stops[o['id']]])

    # Frames: no resident in view -> no frames beyond npc_motion off; in view -> frames.
    # Poses with no resident in sight; the first two have residents of later areas inside
    # the view frustum behind walls (they must still cost nothing).
    away = {'sun-court-wall': ([8, 1.7, -12], [8, 6, -23]), 'rime-vault-console': ([38, -4.3, -90], [38, -4.3, -110]),
            'sun-court-east': ([22, 1.7, 10], [40, 1.7, 10]), 'array-hall-east': ([20, 1.7, -45], [24, 1.7, -45]),
            'signal-rise-east': ([60, 1.7, -128], [90, 1.7, -128])}
    rows = {}
    for area, (eye, target) in away.items():
        look(eye, target); motion('always'); time.sleep(1); on = fps(); drawn = diag()['drawn']; motion('off'); time.sleep(1); off = fps()
        rows[area] = {'alwaysFps': round(on, 2), 'offFps': round(off, 2), 'drawn': drawn}; shot(f'away-{area}.png')
    motion('always')
    check('out of view: residents cost no frames (npc_motion always vs off)', all(r['alwaysFps'] <= r['offFps']+.34 and r['alwaysFps'] < 1 for r in rows.values()), rows)
    first = RESIDENTS[0]['id']; wait(lambda: agent(first)['activity'] == 'walking', timeout=90); facing(first, 4.5, 1.5, 1.2); inview = fps(2.)
    check('in view: an animating resident renders frames', inview > 20, {'fps': round(inview, 1), 'resident': first})

    # Walking stills, one per area.
    for o in RESIDENTS:
        wait(lambda: agent(o['id'])['activity'] == 'walking', timeout=120)
        x = agent(o['id']); h = x['heading']; f = [math.sin(h), math.cos(h)]; left = [f[1], -f[0]]; q = x['position']
        look([q[0]+f[0]*3.2+left[0]*1.6, q[1]+1.55, q[2]+f[1]*3.2+left[1]*1.6], [q[0], q[1]+.95, q[2]]); time.sleep(.3); shot(f'walking-{AREA[o["id"]]}.png')

    # Interactions: aim, choose, say lines in order, waypoint.
    for o in RESIDENTS:
        motion('always'); wait(lambda: agent(o['id'])['mode'] in FREE, timeout=180); motion('still')
        facing(o['id'], 1.8); center(); time.sleep(.6); st = state(); aimed = st['npcs']['aimed']
        ids = [i['id'] for i in o['interactions']]
        check(f"{o['id']}: aimed, offers its interactions", aimed and aimed['objectId'] == o['id'] and [i['id'] for i in aimed['interactions']] == ids and
              st['interaction']['reticle']['action'] == 'interact', {'aimed': aimed})
        for it in o['interactions']:
            act = it['action']
            if act['type'] == 'say':
                client.call('interaction.choose', {'objectId': o['id'], 'interactionId': it['id']}); time.sleep(.4)
                seen = []
                for k in range(len(act['lines'])):
                    cur = state()['npcs']['interaction']; seen.append(cur and cur['line'])
                    if k == 0: shot(f'say-{AREA[o["id"]]}.png')
                    keys('-k', 'e'); time.sleep(.35)
                check(f"{o['id']}: say shows its {len(act['lines'])} lines in order, E ends it", seen == act['lines'] and state()['npcs']['interaction'] is None, seen)
            elif act['type'] == 'waypoint':
                client.call('interaction.choose', {'objectId': o['id'], 'interactionId': it['id']}); time.sleep(.6)
                wp = state()['location']['waypoint']
                check(f"{o['id']}: waypoint sets the waypoint", wp is not None and all(str(v) in json.dumps(wp) for v in act['target'].values()), wp)
                client.call('interaction.choose', {'objectId': o['id'], 'interactionId': None}); time.sleep(.3)
        motion('always')

    # Guide: the resident walks the guide path ahead of a following player and returns.
    for o in RESIDENTS:
        for it in [i for i in o['interactions'] if i['action']['type'] == 'guide']:
            gp = PATHS[it['action']['path']]; end = gp['points'][-1]['position']
            wait(lambda: agent(o['id'])['mode'] in FREE, timeout=180)
            facing(o['id'], 1.8); center(); time.sleep(.5)
            client.call('interaction.choose', {'objectId': o['id'], 'interactionId': it['id']}); time.sleep(.5)
            check(f"{o['id']}: guide starts", agent(o['id'])['activity'] == 'guiding', agent(o['id']))
            t1 = time.monotonic(); closest = 99; snapped = False; trail = []
            while time.monotonic()-t1 < 240:
                x = agent(o['id']); q = x['position']; h = x['heading']; f = [math.sin(h), math.cos(h)]
                closest = min(closest, math.dist(q, end))
                look([q[0]-f[0]*3.0+f[1]*.8, q[1]+1.7, q[2]-f[1]*3.0-f[0]*.8], [q[0]+f[0]*2, q[1]+1.0, q[2]+f[1]*2])
                if not snapped and time.monotonic()-t1 > 8: shot(f'guide-{AREA[o["id"]]}.png'); snapped = True
                if len(trail) < 400: trail.append([round(v, 2) for v in q])
                if closest < .6 and x['activity'] != 'guiding': break
                time.sleep(.2)
            check(f"{o['id']}: guide reaches the end of {gp['id']} with the player following", closest < .8, {'closest': round(closest, 2), 'seconds': round(time.monotonic()-t1, 1)})
            back = wait(lambda: (lambda x: x if x['activity'] in ('walking', 'stopped', 'sitting') else None)(agent(o['id'])), timeout=240)
            check(f"{o['id']}: returns to its route after guiding", back is not None, back)
    # A seated resident asked to guide (recorded, not gated: core's join leg starts on the seat).
    for o in RESIDENTS:
        for it in [i for i in o['interactions'] if i['action']['type'] == 'guide']:
            x = wait(lambda: (lambda y: y if y['mode'] == 6 else None)(agent(o['id'])), timeout=240)
            facing(o['id'], 1.8); center(); time.sleep(.4)
            try:
                client.call('interaction.choose', {'objectId': o['id'], 'interactionId': it['id']}); result = 'accepted'
            except Exception as e: result = str(e)
            time.sleep(1.5); after = agent(o['id'])
            report['seatedGuide'] = {'resident': o['id'], 'result': result, 'after': {k: after[k] for k in ('mode', 'activity', 'clip', 'position')}}; save()
            print('seated guide:', json.dumps(report['seatedGuide']), flush=True)
            client.call('interaction.choose', {'objectId': o['id'], 'interactionId': None}) if result == 'accepted' else None
    shot('final.png'); client.call('runtime.exit', {})
    report['status'] = 'PASS' if all(c['ok'] for c in report['checks']) else 'FAIL'; save()
    print(report['status'], 'residents session', len(report['checks']), 'checks', flush=True)


npcs.prepare = prepare; npcs.acceptance = acceptance
s.run(SimpleNamespace(npcs=True, m3b=False, m3a=False, m2=False, m1=False, integration=False, live=False, serve=False, record=False, visible=False, authoring=False, climbing=False))
