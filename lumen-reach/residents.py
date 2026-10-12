#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Lumen Reach residents: the world format 0.9 side of residents.json.

The four starter-kit residents ship inside the package as RFC-0011 object
directories (`characters/<id>/`, byte-identical to `characters/` in this
repository and to `com.hyprune.starter@0.1.0`), referenced as directory assets.
Official worlds stay self-contained: core resolves a library asset only against
an installed `id@version` and fails activation otherwise (RFC-0011 Libraries),
and installers do not install world library dependencies yet.

Seat anchors come from the benches build.py makes from the same table, so the
anchors and the geometry cannot drift apart. A seat anchor stands `frontGap`
in front of the seat's front edge, at the middle of its half of the bench, and
faces away from it. Core sits a resident down by moving its root back from the
anchor by the sit clip's travel (0.36-0.42 m for these residents) with the
hips over the root, so the pelvis lands 0.20-0.26 m inside the front edge.
The bench's collision stops `collisionSetback` short of the seat front, so the
walker's body (0.30 m across its centre) is clear of collision at the anchor,
which core requires of the seat approach.

  residents.py PACKAGE --in-place   apply to an exported package (iteration)
build.py calls apply() while it writes world.json.
"""
import json, math, shutil, sys
from pathlib import Path
HERE = Path(__file__).resolve().parent; ROOT = HERE.parent
DATA = json.loads((HERE/'residents.json').read_text())
FACING = {'+z': 0, '+x': 90, '-z': 180, '-x': 270}
CHARACTER_FILES = ['object.json', 'object.glb', 'thumbnail.png']


def yaw_quat(degrees):
    h = math.radians(degrees)/2
    return [0, round(math.sin(h), 7), 0, round(math.cos(h), 7)]


def seats():
    """World seats[] from the bench table: one per anchor, id `<bench>-<anchor>`."""
    gap, approach = DATA['seatAnchor']['frontGap'], DATA['seatAnchor']['approach']
    out = []
    for b in DATA['benches']:
        cx, cy, cz = b['centre']
        for an in b['anchors']:
            yaw = FACING[an['facing']]; fx, fz = round(math.sin(math.radians(yaw)), 6), round(math.cos(math.radians(yaw)), 6)
            assert (b['along'] == 'x') == (fx == 0), (b['id'], an['id'], 'anchors face across the bench')
            ax, az = (cx + an['offset'], cz) if b['along'] == 'x' else (cx, cz + an['offset'])
            reach = b['depth']/2 + gap
            out.append({'id': f"{b['id']}-{an['id']}", 'height': b['height'], 'approach': approach,
                        'pose': {'position': [round(ax + fx*reach, 4), cy, round(az + fz*reach, 4)], 'rotation': yaw_quat(yaw)}})
    return out


def apply(m, package, source=ROOT):
    """Add the residents to manifest `m` and copy their directories into `package`."""
    package = Path(package)
    for cid in DATA['characters']:
        dst = package/'characters'/cid; dst.mkdir(parents=True, exist_ok=True)
        for f in CHARACTER_FILES: shutil.copyfile(source/'characters'/cid/f, dst/f)
    assets = [a for a in m.get('objectAssets', []) if a['id'] not in DATA['characters']]
    m['objectAssets'] = assets + [{'id': cid, 'dir': f'characters/{cid}'} for cid in DATA['characters']]
    ids = {r['id'] for r in DATA['residents']}
    m['objects'] = [o for o in m.get('objects', []) if o['id'] not in ids] + DATA['residents']
    anchors = {an['id'] for an in m['anchors']}
    m['paths'] = json.loads(json.dumps(DATA['paths']))
    for path in m['paths']:
        for st in path.get('stops', []):
            assert st.get('face', {}).get('anchor', next(iter(anchors))) in anchors, (path['id'], st)
    m['seats'] = seats(); m['keepClear'] = DATA['keepClear']
    m['formatVersion'] = '0.9'
    return m


if __name__ == '__main__':
    if len(sys.argv) != 3 or sys.argv[2] != '--in-place': sys.exit(__doc__)
    pkg = Path(sys.argv[1]); m = json.loads((pkg/'world.json').read_text())
    (pkg/'world.json').write_text(json.dumps(apply(m, pkg), indent=2)+'\n')
    print(json.dumps({'package': str(pkg.name), 'version': m['version'], 'residents': len(DATA['residents']), 'paths': len(m['paths']), 'seats': len(m['seats']), 'keepClear': len(m['keepClear'])}))
