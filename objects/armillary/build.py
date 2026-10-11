# SPDX-License-Identifier: MIT
"""Armillary: a reusable world object (world format 0.8 objectAssets).

A dark instrument globe wrapped in a cyan network, inside three nested ivory
rings. Each ring turns on its own axis, which lies in the ring's own plane, so it
sweeps its own path around the sphere. The globe turns slowly about the vertical.
Original procedural geometry (the Lumen Reach Sun Court globe, made reusable).

    make objects            (Blender on the bake host, like the worlds)

Writes dist/objects/armillary/: armillary.gltf + .bin and object.json, the
objectAssets entry a world copies (with "scene" made package-relative).
Asset space: glTF (+Y up), origin at the globe centre, metres.
"""
import json, math, os, shutil, sys
from pathlib import Path
if os.environ.get('HYPRUNE_REMOTE_BLENDER') != '1':
    raise SystemExit('Use make objects (tools/remote-blender.sh); never local Blender on the laptop')
import bpy
from mathutils import Euler, Vector

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / 'dist/objects/armillary'
R = 1.8  # the Sun Court globe's design radius
RINGS = [  # (Blender XYZ Euler of the torus, period s, phase, direction) - the Lumen rotations
    ((0, .45, 0), 23, 0.0, 1),
    ((.8, 0, .5), 31, 0.35, -1),
    ((1.2, .35, 0), 41, 0.7, 1),
]


UNLIT = set()


def unlit(name, color):
    """Emission-only in Blender; written as KHR_materials_unlit after export (like the 0.9 rings)."""
    UNLIT.add(name)
    m = bpy.data.materials.new(name); m.use_nodes = True; nt = m.node_tree
    e = nt.nodes.new('ShaderNodeEmission'); e.inputs['Color'].default_value = (*color, 1); e.inputs['Strength'].default_value = 1
    nt.links.new(e.outputs[0], nt.nodes.get('Material Output').inputs['Surface'])
    return m


def material(name, color, rough, metal=0.0, emit=0.0):
    m = bpy.data.materials.new(name); m.use_nodes = True; p = m.node_tree.nodes.get('Principled BSDF')
    p.inputs['Base Color'].default_value = (*color, 1); p.inputs['Roughness'].default_value = rough; p.inputs['Metallic'].default_value = metal
    if emit:
        p.inputs['Emission Color'].default_value = (*color, 1); p.inputs['Emission Strength'].default_value = emit
    return m


def link(o, mat, parent=None):
    o.data.materials.clear(); o.data.materials.append(mat)
    if parent:
        o.parent = parent
    for poly in o.data.polygons:
        poly.use_smooth = True
    return o


def rod(name, a, b, r, mat, parent):
    a, b = Vector(a), Vector(b)
    bpy.ops.mesh.primitive_cylinder_add(vertices=6, radius=r, depth=(b - a).length, location=(a + b) / 2)
    o = bpy.context.object; o.name = name; o.rotation_euler = (b - a).to_track_quat('Z', 'Y').to_euler()
    return link(o, mat, parent)


def blender_to_gltf(v):
    return [round(v[0], 6), round(v[2], 6), round(-v[1], 6)]


def main():
    bpy.ops.wm.read_factory_settings(use_empty=True)
    if OUT.exists():
        shutil.rmtree(OUT)
    OUT.mkdir(parents=True)
    # Matched to the baked 0.9.2 Sun Court globe at two poses (per-region CIEDE2000
    # < 1 with the Lumen placement's ambient 0.11): a near-black matte shell lit at
    # runtime; the cyan network and the champagne rings unlit, as the 0.9 rings were.
    dark = material('armillary-globe', (.004, .005, .007), .95, 0)
    cyan = unlit('armillary-network', (.114, .496, .685))
    ivory = unlit('armillary-ring', (.421, .337, .222))

    bpy.ops.mesh.primitive_ico_sphere_add(subdivisions=2, radius=R * .9, location=(0, 0, 0))
    globe = link(bpy.context.object, dark); globe.name = 'globe'
    edges = set()
    for face in globe.data.polygons:
        ids = list(face.vertices)
        for a, b in zip(ids, ids[1:] + ids[:1]):
            edges.add(tuple(sorted((a, b))))
    rods = [rod('network', globe.data.vertices[a].co, globe.data.vertices[b].co, .012, cyan, None) for a, b in sorted(edges)]
    bpy.ops.object.select_all(action='DESELECT')
    for o in rods:
        o.select_set(True)
    bpy.context.view_layer.objects.active = rods[0]; bpy.ops.object.join()
    network = bpy.context.object; network.name = 'globe-network'; network.parent = globe

    animations = [{'node': 'globe', 'type': 'spin', 'axis': [0, 1, 0], 'pivot': [0, 0, 0], 'period': 90}]
    for i, (rot, period, phase, sign) in enumerate(RINGS):
        bpy.ops.mesh.primitive_torus_add(major_segments=64, minor_segments=8, location=(0, 0, 0), major_radius=R * (1.05 + i * .07),
                                         minor_radius=.035, rotation=rot)
        ring = link(bpy.context.object, ivory); ring.name = f'ring-{i + 1}'
        # The torus lies in its local XY plane: local X is a diameter, so spinning
        # about it tumbles the ring through its own path around the globe.
        axis = Euler(rot, 'XYZ').to_matrix() @ Vector((1, 0, 0))
        animations.append({'node': ring.name, 'type': 'spin', 'axis': blender_to_gltf(axis * sign), 'pivot': [0, 0, 0],
                           'period': period, 'phase': phase})

    bpy.ops.object.select_all(action='SELECT')
    bpy.ops.export_scene.gltf(filepath=str(OUT / 'armillary.gltf'), export_format='GLTF_SEPARATE', use_selection=True, export_yup=True,
                              export_apply=True, export_animations=False, export_cameras=False, export_lights=False, export_extras=False,
                              export_materials='EXPORT')
    # The exporter writes an emission-only material as black base + emissive; make it
    # KHR_materials_unlit with that colour as base (what core draws unlit, as measured).
    g = json.loads((OUT / 'armillary.gltf').read_text())
    for m in g['materials']:
        if m['name'] in UNLIT:
            m['pbrMetallicRoughness'] = {'baseColorFactor': [*m.pop('emissiveFactor'), 1], 'metallicFactor': 0, 'roughnessFactor': 1}
            m['extensions'] = {'KHR_materials_unlit': {}}
    g['extensionsUsed'] = sorted(set(g.get('extensionsUsed', [])) | {'KHR_materials_unlit'})
    (OUT / 'armillary.gltf').write_text(json.dumps(g, indent=1) + '\n')
    outer = R * (1.05 + 2 * .07) + .035
    descriptor = {
        'id': 'armillary', 'version': '1.0.0', 'scene': 'armillary.gltf',
        'description': 'Instrument globe with a cyan network inside three nested rings; each ring spins about its own in-plane axis, the globe turns slowly.',
        'animations': animations, 'lighting': {'mode': 'probe'},
        'boundsRadius': round(outer, 4), 'license': 'CC-BY-4.0',
        'attribution': [{'path': '.', 'author': 'Hyprune contributors', 'license': 'CC-BY-4.0', 'source': 'https://github.com/hyprune/worlds'}],
    }
    (OUT / 'object.json').write_text(json.dumps(descriptor, indent=1) + '\n')
    print('ARMILLARY', json.dumps({'nodes': ['globe', 'globe-network'] + [f'ring-{i + 1}' for i in range(3)], 'boundsRadius': descriptor['boundsRadius']}))


main()
