# SPDX-License-Identifier: MIT
"""Lumen Reach world.json in the canonical format 0.6 contract (from 0.9.0).

The build used the legacy com.hyprune.lumen-reach.mounts/.placement extensions
(core's compatibility adapter). Core reads per-area `playable` volumes only
from canonical `areas[]` and refuses to mix them with the legacy extension, so
`canonical()` writes what that adapter produced (core src/world/Mounts.cpp):
- areas[]: id, workspaceSlot, primaryAnchor, toolAnchors, dataAnchors, theme,
  spawnId, freePlacementZones, plus playable volumes;
- anchors[].mount: type, role (tool -> tool-mount), interaction;
- dataObjects[]: the legacy objects with a data-object mount;
- placementZones[]: the legacy placement zones.
Playable volumes are the footprint rects of lumen-reach/playable-volumes.json
(Blender X/Y, so world box min [x0, bottom, -y1], max [x1, top, -y0]),
grouped into the four workspace areas (connectors join a neighbour), plus a
world-level maxFlyHeight. Core bounds ordinary fly only; walking stays
collision-driven (the low walking backstops remain).
"""
import json
from pathlib import Path

HERE = Path(__file__).parent
MAX_FLY_HEIGHT = 60.0
# Footprint area -> workspace area that declares its volume.
VOLUME_OWNER = {'sun-court': 'sun-court', 'entry-vestibule': 'sun-court', 'array-hall': 'array-hall',
                'connector-descent': 'rime-vault', 'rime-vault': 'rime-vault',
                'connector-ascent': 'signal-rise', 'signal-rise': 'signal-rise'}
ROLE = {'mounted-workspace': 'mounted-workspace', 'tool': 'tool-mount', 'data': 'data-object'}
INTERACTION = {'mounted-workspace': 'focus-in', 'tool-mount': 'in-place', 'data-object': 'none'}


def volumes(spec=None):
    spec = spec or json.loads((HERE / 'playable-volumes.json').read_text())
    out = {}
    for area in spec['areas']:
        for x0, x1, y0, y1 in area['rects']:
            out.setdefault(VOLUME_OWNER[area['id']], []).append(
                {'type': 'box', 'min': [x0, spec['backstopBottom'], -y1], 'max': [x1, MAX_FLY_HEIGHT, -y0]})
    return out


def canonical(m, spec=None):
    ext = m['extensions']
    mounts = ext.pop('com.hyprune.lumen-reach.mounts')
    placement = ext.pop('com.hyprune.lumen-reach.placement')
    vols = volumes(spec)
    anchors = {a['id']: a for a in m['anchors']}
    for r in mounts['mounts']:
        role = ROLE[r['role']]
        mount = {'type': r['mountType'], 'role': role, 'interaction': INTERACTION[role]}
        for k in ('frameNode', 'limits'):
            if k in r:
                mount[k] = r[k]
        anchors[r['anchorId']]['mount'] = mount
    m['areas'] = [{k: a[k] for k in ('id', 'workspaceSlot', 'primaryAnchor', 'toolAnchors', 'dataAnchors', 'theme', 'spawnId', 'freePlacementZones')}
                  | {'playable': {'volumes': vols[a['id']]}} for a in mounts['areas']]
    assert set(vols) <= {a['id'] for a in m['areas']} and all(len(v) <= 8 for v in vols.values())
    m['dataObjects'] = [{'id': o['id'], 'areaId': o['areaId'], 'pose': o['pose'],
                         'mount': {'type': o['mountType'], 'role': 'data-object', 'interaction': 'none'}, **({'node': o['node']} if 'node' in o else {})}
                        for o in mounts['objects']]
    m['placementZones'] = placement['zones']
    m['playable'] = {'maxFlyHeight': MAX_FLY_HEIGHT}
    m['formatVersion'] = '0.6'
    return m


JUMP_UP = 5 ** 2 / (2 * 9.81) + .35   # core jump apex (5 m/s) plus step height
JUMP_REACH = 1.5                       # horizontal gap a jump or a drop clears


def walk_reachable(tops, seeds):
    """Which walkable tops a walker can reach. tops: (x0, x1, y0, y1, zmin,
    zmax) in Blender coordinates; seeds: route/stair feet points (x, y, z).
    Seeded tops are under a seed point; then any top within JUMP_REACH of a
    reachable one is reachable if at most JUMP_UP above it (jump/step) or
    below it (drop). Fly-only roofs stay unreachable."""
    import numpy as np
    t = np.asarray(tops, float).reshape(-1, 6)
    ok = np.zeros(len(t), bool)
    for x, y, z in seeds:
        ok |= (t[:, 0] - .05 <= x) & (x <= t[:, 1] + .05) & (t[:, 2] - .05 <= y) & (y <= t[:, 3] + .05) & (t[:, 4] - .4 <= z) & (z <= t[:, 5] + .4)
    while True:
        r = t[ok]
        gx = np.maximum(0, np.maximum(r[None, :, 0] - t[:, None, 1], t[:, None, 0] - r[None, :, 1]))
        gy = np.maximum(0, np.maximum(r[None, :, 2] - t[:, None, 3], t[:, None, 2] - r[None, :, 3]))
        near = np.hypot(gx, gy) <= JUMP_REACH
        new = ~ok & (near & (t[:, None, 5] <= r[None, :, 5] + JUMP_UP)).any(axis=1)
        if not new.any():
            return ok
        ok |= new


if __name__ == '__main__':
    # Convert an existing (legacy) package's world.json in place, for tests.
    import sys
    p = Path(sys.argv[1]) / 'world.json'
    p.write_text(json.dumps(canonical(json.loads(p.read_text())), indent=2) + '\n')
