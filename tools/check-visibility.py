#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Check subtree ownership, directed links, build reproducibility and unchanged assets."""
import argparse
import copy
import hashlib
import json
from pathlib import Path
from world_visibility import annotate

ROOT = Path(__file__).resolve().parents[1]


def validate(manifest, scene):
    areas = manifest['visibility']['areas']
    ids = [a['id'] for a in areas]
    assert len(ids) == len(set(ids)), 'duplicate region'
    owners = {}
    def walk(node, owner):
        assert 0 <= node < len(scene['nodes']), 'invalid node'
        assert node not in owners, 'overlapping subtree ownership'
        owners[node] = owner
        for child in scene['nodes'][node].get('children', []):
            walk(child, owner)
    for area in areas:
        assert all(lo < hi for lo, hi in zip(area['bounds']['min'], area['bounds']['max'])), 'invalid bounds'
        assert set(area['visibleFrom']) <= set(ids), 'unknown directed source'
        for node in area['nodes']:
            walk(node, area['id'])
    return owners


def active_areas(areas, point):
    return {a['id'] for a in areas if all(lo <= p <= hi for lo, p, hi in zip(a['bounds']['min'], point, a['bounds']['max']))}


def visible_areas(areas, point):
    active = active_areas(areas, point)
    return {a['id'] for a in areas if not active or a['id'] in active or active.intersection(a['visibleFrom'])}


def audit(package, baseline=None):
    manifest = json.loads((package / 'world.json').read_text())
    scene = json.loads((package / manifest['scene']).read_text())
    owners = validate(manifest, scene)
    assert annotate(copy.deepcopy(manifest), scene) == manifest, 'not reproducible from authored spec'
    name = manifest['id'].removeprefix('com.hyprune.')
    spec = json.loads((ROOT / name / 'visibility.json').read_text())
    reachable = set()
    def visit(i):
        reachable.add(i)
        for child in scene['nodes'][i].get('children', []): visit(child)
    for i in scene['scenes'][scene.get('scene', 0)]['nodes']: visit(i)
    helpers = {manifest['navigation']['node']} | {c['node'] for c in manifest['collision']}
    assert not helpers.intersection(owners), 'helper assigned to visual region'
    assert set(owners) <= reachable, 'ownership points outside visual scene'
    shared = [n['name'] for i, n in enumerate(scene['nodes']) if i in reachable and 'mesh' in n and i not in owners]
    assert sorted(shared) == sorted(spec['unassignedAlwaysVisible']), ('unexpected shared chunk', shared)
    draws = {a['id']: 0 for a in manifest['visibility']['areas']}
    for i, owner in owners.items():
        if 'mesh' in scene['nodes'][i]: draws[owner] += len(scene['meshes'][scene['nodes'][i]['mesh']]['primitives'])
    graph = manifest['extensions']['com.hyprune.' + name + '.routes']
    points = [{'id': p['id'], 'sourceAreas': sorted(active_areas(manifest['visibility']['areas'], [p['position'][0], p['position'][1]+1.7, p['position'][2]]))} for p in graph['nodes']]
    result = {'status': 'PASS', 'version': manifest['version'], 'regions': len(draws), 'ownedDraws': draws, 'alwaysVisible': shared, 'routeSources': points}
    if baseline:
        old = json.loads((baseline / 'world.json').read_text())
        now = copy.deepcopy(manifest)
        for key in ['version', 'formatVersion', 'visibility']:
            old.pop(key, None); now.pop(key, None)
        assert old == now, 'non-visibility manifest contract changed'
        files = sorted(p.relative_to(package) for p in package.rglob('*') if p.is_file() and p.name != 'world.json')
        assert files == sorted(p.relative_to(baseline) for p in baseline.rglob('*') if p.is_file() and p.name != 'world.json')
        for path in files:
            assert hashlib.sha256((package/path).read_bytes()).digest() == hashlib.sha256((baseline/path).read_bytes()).digest(), ('asset changed', path)
        result['unchangedAssetFiles'] = len(files)
        result['unchangedContracts'] = ['anchors', 'collision', 'navigation', 'lightmaps', 'spawns', 'zones', 'extensions']
    return result


if __name__ == '__main__':
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('package', type=Path)
    p.add_argument('--baseline', type=Path)
    p.add_argument('--output', type=Path)
    args = p.parse_args()
    result = audit(args.package, args.baseline)
    text = json.dumps(result, indent=2) + '\n'
    if args.output: args.output.write_text(text)
    else: print(text, end='')
