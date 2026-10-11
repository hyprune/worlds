# SPDX-License-Identifier: MIT
"""Blender (bake host only): normalise a Meshy/Mixamo NPC export to the canonical NPC .glb.

    blender --background --factory-startup --python tools/npc/npc_import.py -- \
        --in SRC.glb|.fbx --out OUT.glb --report REPORT.json [--map clip-map.json]
        [--clips-from ANIMATED.glb] [--strip-fingers] [--max-tris 8000] [--keep-sway]

Steps (RFC-0010 draft, docs/npc-characters): metres (cm/mm exports scaled), Y up and +Z
forward in glTF (Blender: Z up, facing -Y), a `root` bone at the feet when missing,
optional finger strip, optional clips copied from another rig of the same skeleton template
(rotations by bone name, Hips translation scaled by the hip-height ratio), clips renamed by
clip-map.json (unknown names pass through), Hips held in place (no root motion; the walk
speed it had is kept as extras.speed), 30 fps, at most 4 weights per vertex, decimation
over the triangle budget. tools/npc/compress.mjs then applies meshopt + KTX2.
"""
import bpy, json, math, os, re, sys
from mathutils import Vector, Matrix

argv = sys.argv[sys.argv.index('--') + 1:]
def arg(name, default=None):
    return argv[argv.index(name) + 1] if name in argv else default
SRC, OUT, REPORT = arg('--in'), arg('--out'), arg('--report')
MAP = arg('--map', os.path.join(os.path.dirname(__file__), 'clip-map.json'))
CLIPS_FROM, MAX_TRIS = arg('--clips-from'), int(arg('--max-tris', '8000'))
STRIP, KEEP_SWAY = '--strip-fingers' in argv, '--keep-sway' in argv
FPS = 30
report = {'source': os.path.basename(SRC), 'steps': [], 'warnings': [], 'clips': {}}
def step(text):
    report['steps'].append(text); print('NPC-IMPORT', text, flush=True)
def warn(text):
    report['warnings'].append(text); print('NPC-IMPORT warning:', text, flush=True)


# Blender 4.4+ layered (slotted) actions and the legacy API.
def channelbags(action):
    bags = []
    for layer in getattr(action, 'layers', []):
        for strip in layer.strips:
            bags += list(strip.channelbags)
    return bags
def fcurves(action):
    if getattr(action, 'layers', None) and len(action.layers):
        return [fc for bag in channelbags(action) for fc in bag.fcurves]
    return list(action.fcurves)
def remove_fcurve(action, fc):
    for bag in channelbags(action):
        if fc in list(bag.fcurves):
            bag.fcurves.remove(fc); return
    action.fcurves.remove(fc)
def bone_of(fc):
    m = re.match(r'pose\.bones\["(.+)"\]\.(\w+)', fc.data_path)
    return (m.group(1), m.group(2)) if m else (None, None)
def assign(arm, action):
    arm.animation_data_create()
    arm.animation_data.action = action
    if getattr(action, 'slots', None) and len(action.slots) and hasattr(arm.animation_data, 'action_slot'):
        arm.animation_data.action_slot = action.slots[0]


def load(path):
    before = set(bpy.data.objects)
    if path.lower().endswith('.fbx'):
        bpy.ops.import_scene.fbx(filepath=path, automatic_bone_orientation=False, ignore_leaf_bones=True)
    else:
        bpy.ops.import_scene.gltf(filepath=path)
    new = [o for o in bpy.data.objects if o not in before]
    arms = [o for o in new if o.type == 'ARMATURE']
    if len(arms) != 1:
        raise SystemExit(f'{path}: expected one armature, found {len(arms)}')
    arm = arms[0]
    meshes = [o for o in new if o.type == 'MESH' and any(m.type == 'ARMATURE' and m.object == arm for m in o.modifiers)]
    actions = set()
    if arm.animation_data:
        if arm.animation_data.action:
            actions.add(arm.animation_data.action)
        for t in arm.animation_data.nla_tracks:
            for s in t.strips:
                if s.action:
                    actions.add(s.action)
    for a in bpy.data.actions:  # importers keep the others as stashed or fake-user actions
        if any(bone_of(fc)[0] and bone_of(fc)[0] in arm.data.bones for fc in fcurves(a)):
            actions.add(a)
    dropped = 0
    for a in actions:  # object-level transform keys (FBX bakes the armature's): core moves the NPC
        for fc in fcurves(a):
            if bone_of(fc)[0] is None:
                remove_fcurve(a, fc); dropped += 1
    if dropped:
        step(f'{os.path.basename(path)}: dropped {dropped} object-level animation curves (core moves the NPC)')
    return arm, meshes, sorted(actions, key=lambda a: a.name), new


def world_bounds(meshes):
    pts = [ob.matrix_world @ Vector(c) for ob in meshes for c in ob.bound_box]
    lo = Vector((min(p.x for p in pts), min(p.y for p in pts), min(p.z for p in pts)))
    hi = Vector((max(p.x for p in pts), max(p.y for p in pts), max(p.z for p in pts)))
    return lo, hi


def apply_transforms(objs):
    bpy.ops.object.select_all(action='DESELECT')
    for o in objs:
        o.select_set(True)
    bpy.context.view_layer.objects.active = objs[0]
    bpy.ops.object.transform_apply(location=True, rotation=True, scale=True)


def normalise(arm, meshes, actions, label):
    """Metres, Z up (Blender), facing -Y, feet at the origin; transforms applied."""
    for o in [arm] + meshes:  # unparent meshes (keeping their world transform) so each applies cleanly
        if o is not arm and o.parent:  # (FBX children carry a parent inverse: reset it)
            mw = o.matrix_world.copy(); o.parent = None; o.matrix_parent_inverse = Matrix.Identity(4); o.matrix_world = mw
    lo, hi = world_bounds(meshes)
    height = hi.z - lo.z
    factor = 1.0
    if 50 <= height <= 300:
        factor = .01
    elif 500 <= height <= 3000:
        factor = .001
    elif not .5 <= height <= 3:
        warn(f'{label}: {height:.2f} units tall after import: not a recognisable unit; left unscaled')
    if factor != 1:
        step(f'{label}: scaled x{factor} ({height:.1f} units tall: {"centimetres" if factor == .01 else "millimetres"})')
    # Pose-bone translations are in bone space and scale with the armature: fold the
    # armature object's scale (FBX: often 0.01) times the unit fix into the location keys.
    total = arm.matrix_world.to_scale().x * factor
    for o in [arm] + meshes:
        o.matrix_world = Matrix.Scale(factor, 4) @ o.matrix_world
    apply_transforms([arm] + meshes)
    if abs(total - 1) > 1e-6:
        for a in actions:
            for fc in fcurves(a):
                if bone_of(fc)[1] == 'location':
                    for k in fc.keyframe_points:
                        k.co.y *= total; k.handle_left.y *= total; k.handle_right.y *= total
    # Facing: toes ahead of the ankles should point -Y (glTF +Z).
    bones = arm.data.bones
    pairs = [(b, b.parent) for b in bones if 'toe' in b.name.lower() and 'end' not in b.name.lower() and b.parent]
    if pairs:
        d = sum(((b.head_local - p.head_local) for b, p in pairs), Vector())
        angle = math.atan2(d.x, -d.y)  # rotation that brings d to -Y
        if abs(angle) > math.radians(10):
            for o in [arm] + meshes:
                o.matrix_world = Matrix.Rotation(-angle, 4, 'Z') @ o.matrix_world
            apply_transforms([arm] + meshes)
            step(f'{label}: turned {math.degrees(-angle):.0f} deg to face +Z (glTF)')
    else:
        warn(f'{label}: no toe bones: facing not checked')
    lo, hi = world_bounds(meshes)
    hips = hips_bone(arm)
    offset = Vector((-(hips.head_local.x if hips else 0), -(hips.head_local.y if hips else 0), -lo.z))
    if offset.length > 1e-4:
        for o in [arm] + meshes:
            o.matrix_world = Matrix.Translation(offset) @ o.matrix_world
        apply_transforms([arm] + meshes)
    for o in meshes:  # the armature's transform is identity now: plain parenting keeps them in place
        o.parent = arm
        o.matrix_parent_inverse = Matrix.Identity(4)
    return hi.z - lo.z


def hips_bone(arm):
    for b in arm.data.bones:
        key = b.name.split(':')[-1].lower()
        if key in ('hips', 'pelvis'):
            return b
    return None


def add_root(arm):
    if any(b.name.split(':')[-1].lower() == 'root' for b in arm.data.bones):
        return
    bpy.context.view_layer.objects.active = arm
    bpy.ops.object.mode_set(mode='EDIT')
    eb = arm.data.edit_bones
    root = eb.new('root'); root.head = (0, 0, 0); root.tail = (0, 0, .1)
    for b in eb:
        if b.parent is None and b is not root:
            b.parent = root; b.use_connect = False
    bpy.ops.object.mode_set(mode='OBJECT')
    step('added `root` at the feet (parent of the hips)')


FINGERS = ('thumb', 'index', 'middle', 'ring', 'pinky', 'finger')
def strip_fingers(arm, meshes):
    names = [b.name for b in arm.data.bones if any(f in b.name.split(':')[-1].lower() for f in FINGERS)]
    if not names:
        return
    for ob in meshes:  # weights move to the hand that holds the finger
        for name in names:
            vg = ob.vertex_groups.get(name)
            if not vg:
                continue
            hand = arm.data.bones[name]
            while hand.parent and any(f in hand.name.split(':')[-1].lower() for f in FINGERS):
                hand = hand.parent
            target = ob.vertex_groups.get(hand.name) or ob.vertex_groups.new(name=hand.name)
            for v in ob.data.vertices:
                for g in v.groups:
                    if g.group == vg.index and g.weight > 0:
                        target.add([v.index], g.weight, 'ADD')
            ob.vertex_groups.remove(vg)
    bpy.context.view_layer.objects.active = arm
    bpy.ops.object.mode_set(mode='EDIT')
    for name in names:
        arm.data.edit_bones.remove(arm.data.edit_bones[name])
    bpy.ops.object.mode_set(mode='OBJECT')
    for a in bpy.data.actions:
        for fc in fcurves(a):
            if bone_of(fc)[0] in names:
                remove_fcurve(a, fc)
    step(f'stripped {len(names)} finger bones (weights moved to the hands)')


def transfer_clips(target, source, actions):
    """Copy clips by bone name: rotations as they are, Hips translation scaled by hip height."""
    th, sh = hips_bone(target), hips_bone(source)
    ratio = th.head_local.z / sh.head_local.z if th and sh and sh.head_local.z > 1e-4 else 1
    tnames, snames = {b.name for b in target.data.bones}, {b.name for b in source.data.bones}
    missing, extra = sorted(snames - tnames), sorted(tnames - snames - {'root'})
    twisted = []
    for name in sorted(snames & tnames):  # same template: rest orientations should agree
        a, b = target.data.bones[name].matrix_local.to_quaternion(), source.data.bones[name].matrix_local.to_quaternion()
        if math.degrees(a.rotation_difference(b).angle) > 5:
            twisted.append(name)
    copied = []
    for act in actions:
        name = act.name
        act.name = name + ' (source)'  # frees the name for the copy
        new = act.copy(); new.name = name
        for fc in fcurves(new):
            bone, prop = bone_of(fc)
            if bone is None:
                continue
            if bone not in tnames or prop == 'scale' or (prop == 'location' and (not th or bone != th.name)):
                remove_fcurve(new, fc); continue
            if prop == 'location':
                for k in fc.keyframe_points:
                    k.co.y *= ratio; k.handle_left.y *= ratio; k.handle_right.y *= ratio
        copied.append(new)
    report['clipsFrom'] = {'source': os.path.basename(CLIPS_FROM), 'hipHeightRatio': round(ratio, 4), 'clips': [a.name for a in copied],
                           'missingBones': missing, 'extraBones': extra, 'restOrientationDiffers': twisted}
    step(f'copied {len(copied)} clips from {os.path.basename(CLIPS_FROM)} (hips x{ratio:.3f})')
    if missing:
        warn(f'bones in the animated rig but not here (their keys are dropped): {", ".join(missing)}')
    if extra:
        warn(f'bones here but not animated by the source (they keep their rest pose): {", ".join(extra)}')
    if twisted:
        warn(f'rest orientation differs by more than 5 deg (rotations may twist): {", ".join(twisted)}')
    return copied


def clip_name(name, mapping):
    clean = name
    while re.match(r'^(armature|mixamo\.com)\|', clean, flags=re.I):
        clean = re.sub(r'^(armature|mixamo\.com)\|', '', clean, flags=re.I)
    while re.search(r'\|(baselayer|mixamo\.com)$', clean, flags=re.I):
        clean = re.sub(r'\|(baselayer|mixamo\.com)$', '', clean, flags=re.I)
    clean = clean.strip()
    key = re.sub(r'[^a-z0-9]+', ' ', clean.lower()).strip()
    for canonical, aliases in mapping.items():
        if key == canonical.replace('_', ' ') or key in [re.sub(r'[^a-z0-9]+', ' ', a.lower()).strip() for a in aliases]:
            return canonical
    return clean


def in_place(arm, actions):
    """Hold the Hips over the root (no root motion); keep the speed it had as extras.speed."""
    hips = hips_bone(arm)
    if not hips:
        warn('no hips bone: root motion not removed'); return
    R = hips.matrix_local.to_3x3()  # bone space -> armature space (the armature is the world now)
    Ri = R.inverted()
    for act in actions:
        curves = {fc.array_index: fc for fc in fcurves(act) if bone_of(fc) == (hips.name, 'location')}
        if not curves:
            continue
        frames = sorted({round(k.co.x, 3) for fc in curves.values() for k in fc.keyframe_points})
        if len(frames) < 2:
            continue
        vals = [R @ Vector([curves[i].evaluate(f) if i in curves else 0 for i in range(3)]) for f in frames]
        drift = Vector((vals[-1].x - vals[0].x, vals[-1].y - vals[0].y, 0))
        seconds = (frames[-1] - frames[0]) / bpy.context.scene.render.fps
        if drift.length > .05 and seconds > 0:
            act['speed'] = round(drift.length / seconds, 3)  # compress.mjs writes it as animation extras
            report.setdefault('speeds', {})[act.name] = act['speed']
        for i in range(3):
            if i not in curves:
                curves[i] = (channelbags(act)[0].fcurves if channelbags(act) else act.fcurves).new(f'pose.bones["{hips.name}"].location', index=i)
        for fc in curves.values():
            fc.keyframe_points.clear()
        for f, v in zip(frames, vals):
            u = (f - frames[0]) / (frames[-1] - frames[0])
            if KEEP_SWAY:  # remove only the travel (linear trend), keep the sway
                h = Vector((v.x - drift.x * u - vals[0].x, v.y - drift.y * u - vals[0].y, v.z))
            else:  # owner's rule: zero the horizontal Hips translation
                h = Vector((0, 0, v.z))
            local = Ri @ h
            for i in range(3):
                curves[i].keyframe_points.insert(f, local[i], options={'FAST'}).interpolation = 'LINEAR'
        if drift.length > .05:
            step(f'clip `{act.name}`: removed {drift.length:.2f} m of root motion ({act.get("speed", 0)} m/s kept as extras.speed)')


def limit_weights(meshes):
    for ob in meshes:
        bpy.ops.object.select_all(action='DESELECT'); ob.select_set(True); bpy.context.view_layer.objects.active = ob
        bpy.ops.object.vertex_group_limit_total(group_select_mode='ALL', limit=4)
        bpy.ops.object.vertex_group_normalize_all(group_select_mode='ALL', lock_active=False)


def triangles(meshes):
    return sum(sum(len(p.vertices) - 2 for p in ob.data.polygons) for ob in meshes)


# --- run ---
bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.context.scene.render.fps = FPS  # importers convert times with the scene rate: keys land on 30 fps
mapping = json.load(open(MAP))
arm, meshes, actions, objs = load(SRC)
report['bonesIn'], report['trianglesIn'] = len(arm.data.bones), triangles(meshes)
report['height'] = round(normalise(arm, meshes, actions, 'model'), 3)
if CLIPS_FROM:
    sarm, smeshes, sactions, sobjs = load(CLIPS_FROM)
    normalise(sarm, smeshes, sactions, 'clip source')
    for a in actions:  # the target's own default clips give way to the shared set
        bpy.data.actions.remove(a)
    actions = transfer_clips(arm, sarm, sactions)
    for o in sobjs:
        bpy.data.objects.remove(o, do_unlink=True)
    for a in sactions:
        bpy.data.actions.remove(a)
if STRIP:
    strip_fingers(arm, meshes)
add_root(arm)
names = {}
for act in actions:
    name = clip_name(act.name, mapping)
    if name in names.values():
        warn(f'clip `{act.name}` maps to `{name}` again: kept as `{act.name}`'); name = act.name
    names[act.name] = name
for act in actions:
    act.name = names[act.name]
report['clips'] = {old: new for old, new in names.items()}
step('clips: ' + ', '.join(f'{o} -> {n}' if o != n else o for o, n in names.items()))
in_place(arm, actions)
limit_weights(meshes)
tris = triangles(meshes)
if tris > MAX_TRIS:
    for ob in meshes:
        mod = ob.modifiers.new('budget', 'DECIMATE'); mod.ratio = MAX_TRIS / tris
        bpy.context.view_layer.objects.active = ob
        with bpy.context.temp_override(object=ob):
            bpy.ops.object.modifier_move_to_index(modifier='budget', index=0)
            bpy.ops.object.modifier_apply(modifier='budget')
    step(f'decimated {tris} -> {triangles(meshes)} triangles (budget {MAX_TRIS})')
report['trianglesOut'], report['bonesOut'] = triangles(meshes), len(arm.data.bones)
# Every clip as its own glTF animation: one NLA track each.
arm.animation_data_create()
arm.animation_data.action = None
for t in list(arm.animation_data.nla_tracks):
    arm.animation_data.nla_tracks.remove(t)
for act in actions:
    track = arm.animation_data.nla_tracks.new(); track.name = act.name
    strip = track.strips.new(act.name, int(act.frame_range[0]), act)
    if getattr(act, 'slots', None) and len(act.slots) and hasattr(strip, 'action_slot'):
        strip.action_slot = act.slots[0]
for ob in list(bpy.data.objects):  # nothing else in the file
    if ob is not arm and ob not in meshes:
        bpy.data.objects.remove(ob, do_unlink=True)
bpy.ops.export_scene.gltf(filepath=OUT, export_format='GLB', export_yup=True, export_animation_mode='NLA_TRACKS',
                          export_force_sampling=True, export_frame_step=1, export_extras=True, export_skins=True,
                          export_all_influences=False, export_morph=False, export_apply=False, export_lights=False, export_cameras=False)
step(f'wrote {os.path.basename(OUT)}')
json.dump(report, open(REPORT, 'w'), indent=2)
