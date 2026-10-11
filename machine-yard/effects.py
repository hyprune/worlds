# SPDX-License-Identifier: MIT
"""Machine Yard effect particle: `fx-spark`, the stand-in piece the machines prototype draws
for `burst`, `pulse`, `flash` and `ring` effects (bindings `effectAsset`), painted with the
effect slot's colour at runtime. The machines themselves are the object assets in
objects/machines/ (copied into the package by build.py).

Writes objects/fx-spark/ (fx-spark.gltf + .bin, object.json: an RFC-0011 format 0.10 item).
"""
import json
import bpy
import kit
from kit import Part, MATS, CYAN, MINT, AMBER

ATTRIBUTION = [{'path': '.', 'author': 'Hyprune contributors', 'license': 'CC-BY-4.0',
                'source': 'https://github.com/hyprune/worlds/tree/main/machine-yard'}]
SPARK = [('mint', MINT, 3), ('amber', AMBER, 3), ('cyan', CYAN, 3)]


def states(slot, palette):
    return {'id': slot, 'materials': [slot], 'palette': [
        {'id': s, 'colour': [round(c, 4) for c in col], 'emission': em} for s, col, em in palette]}


def fx_spark():
    MATS['fx-spark'] = dict(color=(.95, .95, .95), unlit=True)
    p = Part('spark')
    r = .03
    p.hull('fx-spark', [(r, 0, 0), (-r, 0, 0), (0, r * 1.4, 0), (0, -r * 1.4, 0), (0, 0, r * .6), (0, 0, -r * .6)])
    p.finish(smooth_angle=0)
    return dict(id='fx-spark', name='Spark', tags=['effect', 'particle'],
                description='A tiny unlit diamond: the stand-in effect piece, painted with the effect colour at runtime.',
                animations=[], lighting='unlit', traits={'mover': {'speed': 1, 'item': True}},
                slots={'states': [{**states('spark', SPARK), 'materials': ['fx-spark']}]})


def export_asset(data, out):
    """Export the current Blender scene as one object asset into out/<id>/."""
    aid = data['id']; d = out / aid
    if d.exists():
        import shutil; shutil.rmtree(d)
    d.mkdir(parents=True)
    proxy = data.get('proxy')
    objs = list(bpy.context.scene.objects)
    names = [o.name for o in objs]
    assert len(names) == len(set(names)) and not any('.' in n for n in names), ('node names must be unique and unsuffixed', names)
    g = kit.export_gltf(d / f'{aid}.gltf', objs)
    nodes = {n['name']: i for i, n in enumerate(g['nodes'])}
    if proxy is not None:  # the collision proxy stays in nodes[] but leaves the drawn scene
        g['scenes'][0]['nodes'] = [i for i in g['scenes'][0]['nodes'] if i != nodes['proxy']]
        (d / f'{aid}.gltf').write_text(json.dumps(g, indent=1) + '\n')
    visible = [o for o in objs if o.type == 'MESH' and o is not proxy]
    bounds = kit.mesh_bounds(visible)
    # Every slot node / material the manifest names must exist exactly once.
    mats = [m['name'] for m in g.get('materials', [])]
    slots = data.get('slots', {})
    for s in slots.get('states', []):
        for m in s['materials']:
            assert mats.count(m) == 1, (aid, 'states material', m)
    for a in data['animations']:
        assert a['node'] in nodes, (aid, a['node'])
    for kind in ('labels', 'effects', 'spawns', 'stacks', 'toggles'):
        for s in slots.get(kind, []):
            for n in s.get('nodes', [s.get('node', s['id'])]) if kind in ('stacks', 'toggles') else [s['id']]:
                assert n in nodes, (aid, kind, n)
    traits = dict(data.get('traits', {}))
    if data['animations']:
        traits['decorative'] = {'animations': data['animations']}
    if proxy is not None:
        traits['collidable'] = {'node': 'proxy'}
    if data.get('machine'):
        traits['machine'] = data['machine']
    manifest = {'formatVersion': '0.10', 'id': aid, 'version': '0.1.0', 'name': data['name'], 'description': data['description'],
                'category': 'machines', 'tags': data['tags'], 'scene': f'{aid}.gltf', 'license': 'CC-BY-4.0', 'attribution': ATTRIBUTION,
                'bounds': bounds, 'lighting': {'mode': data.get('lighting', 'probe')}, 'traits': traits, 'slots': slots}
    (d / 'object.json').write_text(json.dumps(manifest, indent=1) + '\n')
    report = {'id': aid, 'triangles': kit.triangles(visible), 'proxyTriangles': kit.triangles([proxy]) if proxy else 0,
              'nodes': len(g['nodes']), 'materials': len(mats), 'bounds': bounds, **data.get('notes', {})}
    print('MACHINE', json.dumps(report), flush=True)
    return manifest, report


def build(out):
    kit.reset()
    return export_asset(fx_spark(), out)[1]
