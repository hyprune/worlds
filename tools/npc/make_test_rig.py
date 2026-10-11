# SPDX-License-Identifier: MIT
"""Blender (bake host only): Mixamo-named test rigs for tools/npc-import.

    blender --background --factory-startup --python tools/npc/make_test_rig.py -- OUTDIR

Writes the faults a raw auto-rigged export can have, so the import step is tested on
them: resident-a.fbx and resident-a.glb (animated: centimetres, facing +Y, root motion on
the Hips, clips named like auto-rig exports at 24 fps, finger bones, no `root`) and
resident-b.glb (same skeleton template, 8% shorter, no animations). Original test content.
"""
import bpy, math, os, sys
from mathutils import Vector, Matrix

out = sys.argv[sys.argv.index('--') + 1]
os.makedirs(out, exist_ok=True)


def reset(fps):
    bpy.ops.wm.read_factory_settings(use_empty=True)
    bpy.context.scene.render.fps = fps


# Mixamo template: bone, parent, head (metres, Blender Z up, character facing -Y as Mixamo).
def template(h):
    s = h / 1.8
    B = [('mixamorig:Hips', None, (0, 0, .95)), ('mixamorig:Spine', 'mixamorig:Hips', (0, 0, 1.07)),
         ('mixamorig:Spine1', 'mixamorig:Spine', (0, 0, 1.2)), ('mixamorig:Spine2', 'mixamorig:Spine1', (0, 0, 1.33)),
         ('mixamorig:Neck', 'mixamorig:Spine2', (0, 0, 1.5)), ('mixamorig:Head', 'mixamorig:Neck', (0, 0, 1.58)),
         ('mixamorig:HeadTop_End', 'mixamorig:Head', (0, 0, 1.8))]
    for side, x in (('Left', 1), ('Right', -1)):
        B += [(f'mixamorig:{side}Shoulder', 'mixamorig:Spine2', (.06 * x, 0, 1.45)), (f'mixamorig:{side}Arm', f'mixamorig:{side}Shoulder', (.18 * x, 0, 1.45)),
              (f'mixamorig:{side}ForeArm', f'mixamorig:{side}Arm', (.18 * x, 0, 1.17)), (f'mixamorig:{side}Hand', f'mixamorig:{side}ForeArm', (.18 * x, 0, .91)),
              (f'mixamorig:{side}UpLeg', 'mixamorig:Hips', (.1 * x, 0, .9)), (f'mixamorig:{side}Leg', f'mixamorig:{side}UpLeg', (.1 * x, 0, .48)),
              (f'mixamorig:{side}Foot', f'mixamorig:{side}Leg', (.1 * x, 0, .07)), (f'mixamorig:{side}ToeBase', f'mixamorig:{side}Foot', (.1 * x, -.12, .02)),
              (f'mixamorig:{side}Toe_End', f'mixamorig:{side}ToeBase', (.1 * x, -.18, .02))]
        for f, finger in enumerate(('Thumb', 'Index', 'Middle', 'Ring', 'Pinky')):
            parent = f'mixamorig:{side}Hand'
            for k in range(1, 4):
                name = f'mixamorig:{side}Hand{finger}{k}'
                B.append((name, parent, ((.15 + .015 * f) * x, 0, .87 - .03 * k)))
                parent = name
    return [(n, p, Vector(v) * s) for n, p, v in B]


def build(name, height, animate):
    bones = template(height)
    arm = bpy.data.objects.new(name, bpy.data.armatures.new(name))
    bpy.context.scene.collection.objects.link(arm)
    bpy.context.view_layer.objects.active = arm
    bpy.ops.object.mode_set(mode='EDIT')
    heads = {n: v for n, p, v in bones}
    for n, p, v in bones:
        b = arm.data.edit_bones.new(n)
        b.head = v
        kids = [c for c, pp, _ in bones if pp == n]
        b.tail = heads[kids[0]] if kids and (heads[kids[0]] - v).length > .01 else v + Vector((0, 0, .05))
        if p:
            b.parent = arm.data.edit_bones[p]
    bpy.ops.object.mode_set(mode='OBJECT')
    # Mesh: a box per bone segment, rigidly weighted (body + accent + visor materials).
    mesh_objs = []
    mats = {}
    for mname, colour, emit in (('base', (.6, .62, .66, 1), None), ('accent', (.9, .5, .1, 1), None), ('visor', (.05, .05, .05, 1), (.3, .9, 1))):
        m = bpy.data.materials.new(mname)
        m.use_nodes = True
        bsdf = m.node_tree.nodes['Principled BSDF']
        bsdf.inputs['Base Color'].default_value = colour
        if emit:
            bsdf.inputs['Emission Color'].default_value = (*emit, 1)
            bsdf.inputs['Emission Strength'].default_value = 2.0
        mats[mname] = m
    for part, members in (('body', None), ('head', ('mixamorig:Head', 'mixamorig:Neck')), ('visor', ('visor',))):
        me = bpy.data.meshes.new(part)
        verts, faces, groups = [], [], []
        for n, p, v in bones:
            if 'Hand' in n and n.count('Hand') and any(f in n for f in ('Thumb', 'Index', 'Middle', 'Ring', 'Pinky')):
                continue
            seg = [c for c, pp, _ in bones if pp == n]
            if part == 'visor':
                if n != 'mixamorig:Head':
                    continue
                c, size = v + Vector((0, -.11, .11)), Vector((.16, .02, .05))
            else:
                if (members and n not in members) or (not members and n in ('mixamorig:Head', 'mixamorig:Neck')) or not seg or 'End' in n:
                    continue
                a, b = v, heads[seg[0]]
                c, size = (a + b) / 2, Vector((.11, .11, max(.05, (b - a).length)))
                if n == 'mixamorig:Head':
                    c, size = v + Vector((0, 0, .11)), Vector((.2, .22, .22))
                if 'Spine' in n:
                    size = Vector((.32, .18, (b - a).length))
                if 'Foot' in n:
                    c, size = v + Vector((0, -.05, -.03)), Vector((.1, .22, .06))
            base = len(verts)
            for i in range(8):
                verts.append(c + Vector(((i & 1) - .5, ((i >> 1) & 1) - .5, ((i >> 2) & 1) - .5)) * 1 * Vector((1, 1, 1)) * 1 if False else
                             c + Vector((((i & 1) - .5) * size.x, (((i >> 1) & 1) - .5) * size.y, (((i >> 2) & 1) - .5) * size.z)))
                groups.append(n)
            faces += [[base + i for i in f] for f in ((0, 1, 3, 2), (4, 6, 7, 5), (0, 4, 5, 1), (2, 3, 7, 6), (0, 2, 6, 4), (1, 5, 7, 3))]
        me.from_pydata([tuple(v) for v in verts], [], faces)
        ob = bpy.data.objects.new(part, me)
        bpy.context.scene.collection.objects.link(ob)
        for i, g in enumerate(groups):
            vg = ob.vertex_groups.get(g) or ob.vertex_groups.new(name=g)
            vg.add([i], 1.0, 'REPLACE')
        ob.data.materials.append(mats['visor' if part == 'visor' else 'base'])
        if part == 'body':
            ob.data.materials.append(mats['accent'])
            for poly in me.polygons:  # the chest in the accent colour
                if all(ob.vertex_groups[ob.data.vertices[i].groups[0].group].name == 'mixamorig:Spine2' for i in poly.vertices):
                    poly.material_index = 1
        # subdivide to a realistic triangle count
        mod = ob.modifiers.new('subdiv', 'SUBSURF'); mod.levels = 2; mod.subdivision_type = 'SIMPLE'
        bpy.context.view_layer.objects.active = ob; bpy.ops.object.modifier_apply(modifier='subdiv')
        ob.parent = arm
        ob.modifiers.new('Armature', 'ARMATURE').object = arm
        mesh_objs.append(ob)
    if animate:
        def clip(cname, seconds, fn, travel=0.0):
            act = bpy.data.actions.new(cname)
            arm.animation_data_create()
            arm.animation_data.action = act
            fps = bpy.context.scene.render.fps
            frames = int(seconds * fps)
            for f in range(frames + 1):
                u = f / frames
                for bname, rot in fn(u).items():
                    pb = arm.pose.bones[bname]
                    pb.rotation_mode = 'QUATERNION'
                    pb.rotation_quaternion = rot
                    pb.keyframe_insert('rotation_quaternion', frame=f + 1)
                hips = arm.pose.bones['mixamorig:Hips']
                # Root motion: forward (-Y, Mixamo facing) in armature space, written in bone space.
                hips.location = hips.bone.matrix_local.to_3x3().inverted() @ Vector((0, -travel * u * seconds, 0))
                hips.keyframe_insert('location', frame=f + 1)
            track = arm.animation_data.nla_tracks.new(); track.name = cname
            track.strips.new(cname, 1, act)
            arm.animation_data.action = None
        from mathutils import Quaternion as Q
        def gait(swing):
            return lambda u: {'mixamorig:LeftUpLeg': Q((1, 0, 0), math.radians(swing * math.sin(2 * math.pi * u))),
                              'mixamorig:RightUpLeg': Q((1, 0, 0), math.radians(-swing * math.sin(2 * math.pi * u))),
                              'mixamorig:LeftArm': Q((1, 0, 0), math.radians(-15 * math.sin(2 * math.pi * u))),
                              'mixamorig:RightArm': Q((1, 0, 0), math.radians(15 * math.sin(2 * math.pi * u)))}
        clip('Armature|Walking|baselayer', 1.0, gait(25), travel=1.3)
        clip('Running', .7, gait(40), travel=3.0)
        clip('Idle', 2.0, lambda u: {'mixamorig:Spine1': Q((1, 0, 0), math.radians(2 * math.sin(2 * math.pi * u)))})
        clip('Left Turn', 1.0, lambda u: {'mixamorig:Hips': Q((0, 1, 0), math.radians(90 * u))})
        clip('Waving', 2.0, lambda u: {'mixamorig:RightArm': Q((0, 1, 0), math.radians(120 * math.sin(math.pi * u)))})
        clip('Dance Hip Hop', 1.0, lambda u: {})  # not in the spec: passes through
    return arm, mesh_objs


reset(24)
arm, meshes = build('Armature', 1.8, True)
# The usual FBX-export faults: centimetres and facing +Y instead of -Y.
arm.rotation_euler = (0, 0, math.pi)
for ob in [arm] + meshes:
    ob.select_set(True)
bpy.ops.export_scene.fbx(filepath=os.path.join(out, 'resident-a.fbx'), global_scale=100, apply_unit_scale=False, bake_anim=True,
                         bake_anim_use_nla_strips=True, bake_anim_use_all_actions=False, add_leaf_bones=False)
bpy.ops.export_scene.gltf(filepath=os.path.join(out, 'resident-a.glb'), export_format='GLB', export_animation_mode='NLA_TRACKS')
reset(30)
arm, meshes = build('Armature', 1.66, False)
bpy.ops.export_scene.gltf(filepath=os.path.join(out, 'resident-b.glb'), export_format='GLB')
for n in ('resident-a', 'resident-b'):
    with open(os.path.join(out, n + '.PROVENANCE.md'), 'w') as f:
        f.write(f'''# PROVENANCE: {n}
Source: test rig generated by worlds tools/npc/make_test_rig.py (not a tool export)
Author: Hyprune contributors
Licence: CC-BY-4.0
Animations: generated by the script ({'animated' if n == 'resident-a' else 'none'})
Resemblance check: abstract box figure; resembles no third-party character
''')
print('TEST RIGS', out)
