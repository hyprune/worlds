#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Check the installed machine objects against today's world contract.

Builds a throwaway world format 0.8 package (a floor and one instance of every
machine in objects/machines/, as inline objectAssets with the decorative
animations and the collision proxy), then runs the shared schema validator
and core's hyprune-world-check on it. Also checks each object.json against the
RFC-0011/0013 draft rules this repository can check without a schema yet:
names that slots and drives reference exist in the glTF, slot counts, bounds.

    python3 objects/machines/check.py [--schema ../schema] [--core ../core] [--output report.json]
"""
import argparse, json, shutil, struct, subprocess, sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
IDS = ['job-token', 'ci-conveyor', 'queue-stack', 'server-rack', 'deploy-lift', 'build-monitor']


def floor_gltf(out, size=40.0):
    s = size / 2
    pos = [-s, 0, -s, s, 0, -s, s, 0, s, -s, 0, s]
    idx = [0, 2, 1, 0, 3, 2]
    blob = struct.pack('<12f', *pos) + struct.pack('<6H', *idx)
    (out / 'scene.bin').write_bytes(blob)
    g = {'asset': {'version': '2.0'}, 'scene': 0, 'scenes': [{'nodes': [0]}], 'nodes': [{'name': 'floor', 'mesh': 0}],
         'meshes': [{'name': 'floor', 'primitives': [{'attributes': {'POSITION': 0}, 'indices': 1, 'material': 0}]}],
         'materials': [{'name': 'floor', 'pbrMetallicRoughness': {'baseColorFactor': [.6, .58, .55, 1], 'metallicFactor': 0, 'roughnessFactor': .8}}],
         'buffers': [{'uri': 'scene.bin', 'byteLength': len(blob)}],
         'bufferViews': [{'buffer': 0, 'byteOffset': 0, 'byteLength': 48}, {'buffer': 0, 'byteOffset': 48, 'byteLength': 12}],
         'accessors': [{'bufferView': 0, 'componentType': 5126, 'count': 4, 'type': 'VEC3', 'min': [-s, 0, -s], 'max': [s, 0, s]},
                       {'bufferView': 1, 'componentType': 5123, 'count': 6, 'type': 'SCALAR'}]}
    (out / 'scene.gltf').write_text(json.dumps(g, indent=1))


def draft_checks(mid):
    """RFC-0011/0013 draft rules checked against the installed glTF."""
    d = HERE / mid
    m = json.loads((d / 'object.json').read_text()); g = json.loads((d / m['scene']).read_text())
    nodes = [n.get('name') for n in g['nodes']]; mats = [x['name'] for x in g['materials']]
    errs = []
    def node(n, why):
        if nodes.count(n) != 1:
            errs.append(f'{why}: node {n} found {nodes.count(n)} times')
    slots = m.get('slots', {})
    for kind, items in slots.items():
        if len(items) > 8:
            errs.append(f'slots.{kind}: {len(items)} > 8')
        ids = [s['id'] for s in items]
        if len(set(ids)) != len(ids):
            errs.append(f'slots.{kind}: duplicate ids')
    for s in slots.get('states', []):
        for mn in s.get('materials', []):
            if mats.count(mn) != 1:
                errs.append(f'states {s["id"]}: material {mn} found {mats.count(mn)} times')
        if not 1 <= len(s['palette']) <= 16:
            errs.append(f'states {s["id"]}: palette size')
    for s in slots.get('stacks', []):
        node(s['node'], f'stacks {s["id"]}')
        nx, ny, nz = s['layout']['grid']
        if s['cap'] > 64 or s['cap'] > nx * ny * nz:
            errs.append(f'stacks {s["id"]}: cap {s["cap"]} over 64 or the grid')
    for s in slots.get('toggles', []):
        for n in s['nodes']:
            node(n, f'toggles {s["id"]}')
    for s in slots.get('tracks', []):
        if not 2 <= len(s['points']) <= 32:
            errs.append(f'tracks {s["id"]}: {len(s["points"])} points')
    traits = m.get('traits', {})
    anims = {a['node'] for a in traits.get('decorative', {}).get('animations', [])}
    for n in anims:
        node(n, 'animation')
    if 'collidable' in traits:
        node(traits['collidable']['node'], 'collidable')
    mach = traits.get('machine', {})
    inputs = {}
    for i in mach.get('inputs', []):
        for k in range(1, i.get('repeat', 1) + 1):
            inputs[f'{i["id"]}.{k}' if 'repeat' in i else i['id']] = i
    if len(inputs) > 16:
        errs.append(f'machine: {len(inputs)} inputs > 16')
    if len(mach.get('drives', [])) > 32:
        errs.append('machine: drives > 32')
    by_kind = {k: {s['id'] for s in v} for k, v in slots.items()}
    kinds = {'state': 'states', 'emission': 'states', 'label': 'labels', 'visible': 'toggles', 'count': 'stacks', 'spawn': 'spawns', 'effect': 'effects'}
    for dr in mach.get('drives', []):
        if dr['input'] not in inputs:
            errs.append(f'drive input {dr["input"]} undeclared')
        kind, _, name = dr['target'].partition(':')
        if kind in ('animation', 'position'):
            if name not in anims:
                errs.append(f'drive target {dr["target"]}: no such animation')
        elif name not in by_kind.get(kinds.get(kind, '?'), set()):
            errs.append(f'drive target {dr["target"]}: no such slot')
        if kind == 'state':
            pal = {e['id'] for s in slots['states'] if s['id'] == name for e in s['palette']}
            mp = dr.get('map', {})
            outs = [c['to'] for c in mp.get('cases', [])] + ([mp['else']] if 'else' in mp else [])
            if not mp:
                outs = inputs[dr['input']].get('values', [])
            for o in outs:
                if o not in pal:
                    errs.append(f'drive {dr["input"]} -> {dr["target"]}: state {o} not in the palette')
    b = m['bounds']
    if abs(b['min'][1]) > .01:
        errs.append(f'bounds min Y {b["min"][1]} (floor objects start at 0)')
    tris = sum(g['accessors'][p['indices']]['count'] // 3 for i in g['scenes'][0]['nodes'] for p in
               (g['meshes'][g['nodes'][i]['mesh']]['primitives'] if 'mesh' in g['nodes'][i] else []))
    return {'id': mid, 'errors': errs, 'inputs': len(inputs), 'drives': len(mach.get('drives', [])),
            'slots': {k: len(v) for k, v in slots.items()}, 'rootTriangles': tris}


def main():
    ap = argparse.ArgumentParser(); ap.add_argument('--schema', default=str(ROOT.parent / 'schema')); ap.add_argument('--core', default=str(ROOT.parent / 'core'))
    ap.add_argument('--output')
    a = ap.parse_args()
    pkg = ROOT / 'build/machines-check/com.hyprune.machines-check'
    shutil.rmtree(pkg, ignore_errors=True); (pkg / 'objects').mkdir(parents=True)
    floor_gltf(pkg)
    assets, objects, x = [], [], -12.0
    for mid in IDS:
        d = HERE / mid; m = json.loads((d / 'object.json').read_text())
        shutil.copytree(d, pkg / 'objects' / mid, ignore=shutil.ignore_patterns('build.py', 'object.json', 'thumbnail.png'))
        e = {'id': mid, 'scene': f'objects/{mid}/{m["scene"]}'}
        if m['traits'].get('decorative'):
            e['animations'] = m['traits']['decorative']['animations']
        if m['traits'].get('collidable'):
            e['collision'] = m['traits']['collidable']
        assets.append(e)
        w = m['bounds']['max'][0] - m['bounds']['min'][0]
        objects.append({'id': f'{mid}-1', 'asset': mid, 'pose': {'position': [round(x + w / 2, 3), 0, -6], 'rotation': [0, 0, 0, 1]}})
        x += w + 1.5
    world = {'formatVersion': '0.8', 'id': 'com.hyprune.machines-check', 'version': '0.1.0', 'name': 'Machines check', 'license': 'CC-BY-4.0',
             'scene': 'scene.gltf', 'defaultSpawn': 'arrival',
             'spawns': [{'id': 'arrival', 'pose': {'position': [0, 0, 4], 'rotation': [0, 0, 0, 1]}}],
             'attribution': [{'path': '.', 'author': 'Hyprune contributors', 'license': 'CC-BY-4.0'}],
             'zones': [{'id': 'yard', 'name': 'Yard', 'bounds': {'min': [-20, 0, -20], 'max': [20, 6, 20]}}],
             'anchors': [], 'collision': [{'node': 0, 'shape': 'mesh', 'layer': 'static'}], 'objectAssets': assets, 'objects': objects}
    (pkg / 'world.json').write_text(json.dumps(world, indent=1))
    report = {'package': str(pkg.relative_to(ROOT)), 'draft': [draft_checks(mid) for mid in IDS]}
    r = subprocess.run(['node', str(Path(a.schema) / 'bin/validate.mjs'), 'world', str(pkg / 'world.json'), '-', '0.8'], capture_output=True, text=True)
    report['schema'] = {'exit': r.returncode, 'out': (r.stdout + r.stderr).strip()[-2000:]}
    wc = Path(a.core) / 'build/hyprune-world-check'
    if wc.exists():
        r = subprocess.run([str(wc), str(pkg)], capture_output=True, text=True)
        out = r.stdout.strip()
        try:
            out = json.loads(out)
        except ValueError:
            out = out[-3000:]
        report['coreWorldCheck'] = {'exit': r.returncode, 'out': out, 'stderr': r.stderr.strip()[-2000:]}
    text = json.dumps(report, indent=1)
    if a.output:
        Path(a.output).write_text(text + '\n')
    print(text)
    ok = report['schema']['exit'] == 0 and all(not d['errors'] for d in report['draft']) and report.get('coreWorldCheck', {}).get('exit', 0) == 0
    sys.exit(0 if ok else 1)


main()
