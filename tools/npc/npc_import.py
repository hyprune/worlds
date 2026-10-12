# SPDX-License-Identifier: MIT
"""Blender (bake host only): normalise an auto-rigged NPC export to the canonical NPC .glb.

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
from mathutils import Vector, Matrix, Quaternion

argv = sys.argv[sys.argv.index('--') + 1:]
def arg(name, default=None):
    return argv[argv.index(name) + 1] if name in argv else default
SRC, OUT, REPORT = arg('--in'), arg('--out'), arg('--report')
MAP = arg('--map', os.path.join(os.path.dirname(__file__), 'clip-map.json'))
CLIPS_FROM, MAX_TRIS = arg('--clips-from'), int(arg('--max-tris', '8000'))
STRIP, KEEP_SWAY = '--strip-fingers' in argv, '--keep-sway' in argv
KEEP_OWN = [n for n in (arg('--keep-own', '') or '').split(',') if n]  # with --clips-from: keep these own clips
MAX_TEXTURE = int(arg('--max-texture', '1024'))
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
    before, before_actions = set(bpy.data.objects), set(bpy.data.actions)
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
    for a in bpy.data.actions:  # importers keep the others as stashed or fake-user actions (this import's only)
        if a not in before_actions and any(bone_of(fc)[0] and bone_of(fc)[0] in arm.data.bones for fc in fcurves(a)):
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
    # Rest vertices, not bound_box: a skinned mesh's bound_box follows the evaluated pose
    # (the current frame of the active clip), which needn't stand where the rest pose does.
    pts = [ob.matrix_world @ v.co for ob in meshes for v in ob.data.vertices]
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


# --- pose maths on bone hierarchies (armature space = world: transforms are applied) ---
def order(arm):
    out, todo = [], [b for b in arm.data.bones if b.parent is None]
    while todo:
        b = todo.pop(0); out.append(b.name); todo += list(b.children)
    return out
def rest(arm):
    return {b.name: (b.matrix_local.to_quaternion(), b.head_local.copy(), b.parent.name if b.parent else None) for b in arm.data.bones}
def curve_map(action):
    m = {}
    for fc in fcurves(action):
        bone, prop = bone_of(fc)
        if bone:
            m[(bone, prop, fc.array_index)] = fc
    return m
def basis(curves, bone, f):
    q = [curves[(bone, 'rotation_quaternion', i)].evaluate(f) if (bone, 'rotation_quaternion', i) in curves else (1, 0, 0, 0)[i] for i in range(4)]
    l = [curves[(bone, 'location', i)].evaluate(f) if (bone, 'location', i) in curves else 0 for i in range(3)]
    return Quaternion(q).normalized(), Vector(l)
def fk(names, R, curves, f, world=None, loc=None):
    """World rotations P and head positions H. world: fixed world rotations for some bones
    (others take their basis from `curves`, or rest when curves is None); loc: hips basis."""
    P, H = {}, {}
    for b in names:
        rb, hb, p = R[b]
        B, L = basis(curves, b, f) if curves is not None else (Quaternion(), Vector())
        if loc and b in loc:
            L = loc[b]
        Q = P[p] @ R[p][0].inverted() if p else Quaternion()
        P[b] = world[b] if world and b in world else Q @ rb @ B
        H[b] = (H[p] + Q @ (hb - R[p][1]) if p else hb.copy()) + Q @ rb @ L
    return P, H
def to_basis(names, R, P):
    out = {}
    for b in names:
        rb, hb, p = R[b]
        Q = P[p] @ R[p][0].inverted() if p else Quaternion()
        out[b] = (rb.inverted() @ Q.inverted() @ P[b]).normalized()
    return out
def leg_ik(P, H, R, side, target):
    """Two-bone IK: UpLeg/Leg reach the ankle target; the foot keeps its world rotation."""
    u, k, f = (f'mixamorig:{side}UpLeg', f'mixamorig:{side}Leg', f'mixamorig:{side}Foot')
    if not all(n in H for n in (u, k, f)):
        return 0
    hu, kk, ff = H[u], H[k], H[f]
    l1, l2 = (kk - hu).length, (ff - kk).length
    d = target - hu
    dist = min(max(d.length, abs(l1 - l2) + 1e-4), l1 + l2 - 1e-4)
    a, b = hu - kk, ff - kk
    n = a.cross(b)
    if n.length < 1e-6:
        n = P[u] @ Vector((1, 0, 0))
    n.normalize()
    cur = a.angle(b)
    want = math.acos(max(-1, min(1, (l1 * l1 + l2 * l2 - dist * dist) / (2 * l1 * l2))))
    bend = Quaternion(n, want - cur)
    P[k] = bend @ P[k]
    ff2 = kk + bend @ b
    swing = (ff2 - hu).rotation_difference(d)
    P[u] = swing @ P[u]
    P[k] = swing @ P[k]
    return math.degrees(abs(want - cur)) + math.degrees(swing.angle)


def transfer_clips(target, source, actions):
    """Retarget by bone name: rest-relative world rotations on the shared mixamorig bones
    (delta from the source's rest in world space applied to the target's rest), other bones
    at rest; Hips translation x hip-height ratio; walk/run clips get a two-bone leg IK onto the
    source's ankle path (scaled about the target's own stance) so feet plant like the source."""
    Rt, Rs, nt, ns = rest(target), rest(source), order(target), order(source)
    th, sh = hips_bone(target), hips_bone(source)
    ratio = th.head_local.z / sh.head_local.z if th and sh and sh.head_local.z > 1e-4 else 1
    shared = [b for b in nt if b in Rs and b.startswith('mixamorig') and not any(x in b.split(':')[-1].lower() for x in FINGERS)]
    missing = sorted(b for b in Rs if b not in Rt and b.startswith('mixamorig'))
    extra = sorted(b for b in Rt if b not in shared and b != 'root')
    twist = {b: round(math.degrees(Rt[b][0].rotation_difference(Rs[b][0]).angle), 1) for b in shared}
    copied, ik = [], {}
    target.animation_data_create()
    for act in actions:
        name = re.sub(r'\.\d{3}$', '', act.name)  # Blender's suffix when the target had the same clip name
        act.name = name + ' (source)'
        curves = curve_map(act)
        new = bpy.data.actions.new(name)
        assign(target, new)
        f0, f1 = int(round(act.frame_range[0])), int(round(act.frame_range[1]))
        # Experimental: measured against the rigs' own authored clips it adds sliding, so it's opt-in.
        legs = re.search(r'walk|run', name, re.I) is not None and '--leg-ik' in argv
        prev, worst = {}, 0
        for f in range(f0, f1 + 1):
            Ps, Hs = fk(ns, Rs, curves, f)
            world = {b: (Ps[b] @ Rs[b][0].inverted() @ Rt[b][0]).normalized() for b in shared}
            loc = {}
            if th and sh:
                hips = Rt[th.name][1] + (Hs[sh.name] - Rs[sh.name][1]) * ratio
                loc[th.name] = Rt[th.name][0].inverted() @ (hips - Rt[th.name][1])
            P, H = fk(nt, Rt, None, f, world, loc)
            if legs:
                for side in ('Left', 'Right'):
                    foot = f'mixamorig:{side}Foot'
                    if foot in Hs and foot in Rt:
                        goal = Rt[foot][1] + (Hs[foot] - Rs[foot][1]) * ratio
                        worst = max(worst, leg_ik(P, H, Rt, side, goal))
                        P, H = fk(nt, Rt, None, f, P, loc)
            B = to_basis(nt, Rt, P)
            for b in nt:
                pb = target.pose.bones[b]
                pb.rotation_mode = 'QUATERNION'
                q = B[b]
                if b in prev and prev[b].dot(q) < 0:
                    q = -q
                prev[b] = q
                pb.rotation_quaternion = q
                pb.keyframe_insert('rotation_quaternion', frame=f)
                if b in loc:
                    pb.location = loc[b]
                    pb.keyframe_insert('location', frame=f)
        if legs:
            ik[name] = round(worst, 1)
        target.animation_data.action = None
        copied.append(new)
    report['clipsFrom'] = {'source': os.path.basename(CLIPS_FROM), 'method': 'rest-relative world-space rotations on shared mixamorig bones',
                           'hipHeightRatio': round(ratio, 4), 'sharedBones': len(shared), 'clips': [a.name for a in copied],
                           'missingBones': missing, 'boneNotRetargeted': extra, 'restDifferenceDeg': twist, 'legIkMaxCorrectionDeg': ik}
    step(f'retargeted {len(copied)} clips from {os.path.basename(CLIPS_FROM)} on {len(shared)} shared bones (hips x{ratio:.3f}, leg IK on {len(ik)})')
    if missing:
        warn(f'mixamorig bones in the animated rig but not here: {", ".join(missing)}')
    if extra:
        step(f'at rest in retargeted clips (not shared): {", ".join(extra)}')
    return copied


def clean_channels(arm, actions):
    """Rotations on every bone; translation on the Hips only; no scale (some exporters key all three)."""
    hips = hips_bone(arm)
    dropped = 0
    for a in actions:
        for fc in fcurves(a):
            bone, prop = bone_of(fc)
            if prop == 'scale' or (prop == 'location' and (not hips or bone != hips.name)):
                remove_fcurve(a, fc); dropped += 1
    if dropped:
        step(f'dropped {dropped} translation/scale channels (translation kept on the Hips only)')


ARM_BONES = ('shoulder', 'arm', 'forearm', 'hand')


def arm_motion(act):
    """Mean angular speed of the arm chains (shoulder, arm, forearm, hand; both sides), deg/s:
    how busy the arms are, to pick the calmest idle."""
    quats = {}
    for fc in fcurves(act):
        bone, prop = bone_of(fc)
        if prop == 'rotation_quaternion' and re.sub(r'^.*:', '', bone).lower().removeprefix('left').removeprefix('right') in ARM_BONES:
            quats.setdefault(bone, {})[fc.array_index] = fc
    start, end = act.frame_range
    frames = [start + i for i in range(int(end - start) + 1)]
    seconds = max((end - start) / bpy.context.scene.render.fps, 1e-3)
    total = 0.0
    for curves in quats.values():
        q = [Quaternion([curves[i].evaluate(f) if i in curves else (1, 0, 0, 0)[i] for i in range(4)]).normalized() for f in frames]
        total += sum(math.degrees(a.rotation_difference(b).angle) for a, b in zip(q, q[1:]))
    return total / seconds


def map_clips(actions, mapping):
    """Each canonical name takes the first of its aliases present (priority order); every
    other clip keeps its own name, cleaned and lowercased. A canonical entry may instead be
    {"calmest": [...], "then": [...]}: the candidate present with the least arm motion,
    else the first of `then`."""
    def key(n):
        n = re.sub(r'^((armature|mixamo\.com)\|)+', '', n, flags=re.I)
        n = re.sub(r'(\|(baselayer|mixamo\.com))+$', '', n, flags=re.I)
        return re.sub(r'[^a-z0-9]+', '_', n.lower()).strip('_')
    names, taken = {}, set()
    def find(alias):
        return next((a for a in actions if a.name not in names and key(a.name) == key(alias)), None)
    for canonical, aliases in mapping.items():
        if isinstance(aliases, dict):
            candidates = [a for a in map(find, aliases.get('calmest', [])) if a]
            if candidates:
                motion = {a.name: round(arm_motion(a), 1) for a in candidates}
                hit = min(candidates, key=lambda a: motion[a.name])
                report.setdefault('calmest', {})[canonical] = {'chosen': hit.name, 'armMotionDegPerSecond': motion}
                step(f'{canonical}: calmest of {motion} is {hit.name}')
                names[hit.name] = canonical; taken.add(canonical); continue
            aliases = aliases.get('then', [])
        for alias in aliases:
            hit = find(alias)
            if hit:
                names[hit.name] = canonical; taken.add(canonical); break
    for a in actions:
        if a.name not in names:
            n = key(a.name)
            while n in taken or n in names.values():
                n += '_2'
            names[a.name] = n
    return names


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
            else:  # default: zero the horizontal Hips translation
                h = Vector((0, 0, v.z))
            local = Ri @ h
            for i in range(3):
                curves[i].keyframe_points.insert(f, local[i], options={'FAST'}).interpolation = 'LINEAR'
        if drift.length > .05:
            step(f'clip `{act.name}`: removed {drift.length:.2f} m of root motion ({act.get("speed", 0)} m/s kept as extras.speed)')
    # In-place locomotion clips: the speed is how fast the planted foot moves back.
    R, names = rest(arm), order(arm)
    fps = bpy.context.scene.render.fps
    for act in actions:
        if act.name in report.get('speeds', {}) or not re.match(r'(walk|run)', act.name):
            continue
        curves = curve_map(act)
        f0, f1 = int(round(act.frame_range[0])), int(round(act.frame_range[1]))
        feet = [n for n in (f'mixamorig:{s}ToeBase' for s in ('Left', 'Right')) if n in R] or \
               [n for n in (f'mixamorig:{s}Foot' for s in ('Left', 'Right')) if n in R]
        if len(feet) < 2 or f1 - f0 < 4:
            continue
        track = [fk(names, R, curves, f)[1] for f in range(f0, f1 + 1)]
        low = min(h[n].z for h in track for n in feet)
        v = []
        for i in range(len(track) - 1):
            n = min(feet, key=lambda n: track[i][n].z)
            if track[i][n].z < low + .03:
                d = track[i + 1][n] - track[i][n]
                v.append(math.hypot(d.x, d.y) * fps)
        if v:
            v.sort()
            speed = round(v[len(v) // 2], 3)
            if speed > .2:
                report.setdefault('speeds', {})[act.name] = speed
                step(f'clip `{act.name}`: in place; planted-foot speed {speed} m/s (extras.speed)')


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
if len(meshes) == 1 and meshes[0].name.lower() not in ('body', 'head', 'visor'):  # one mesh: it's the body
    step(f'mesh `{meshes[0].name}` named `body`'); meshes[0].name = 'body'; meshes[0].data.name = 'body'
report['height'] = round(normalise(arm, meshes, actions, 'model'), 3)
clean_channels(arm, actions)
for img in bpy.data.images:  # textures at most MAX_TEXTURE px (KTX2 follows in compress.mjs)
    if img.size[0] > MAX_TEXTURE or img.size[1] > MAX_TEXTURE:
        old = tuple(img.size); f = MAX_TEXTURE / max(img.size)
        img.scale(max(1, int(img.size[0] * f)), max(1, int(img.size[1] * f)))
        step(f'texture {img.name}: {old[0]}x{old[1]} -> {img.size[0]}x{img.size[1]}')
if CLIPS_FROM:
    sarm, smeshes, sactions, sobjs = load(CLIPS_FROM)
    normalise(sarm, smeshes, sactions, 'clip source')
    clean_channels(sarm, sactions)
    own = [a for a in actions if a.name in KEEP_OWN]
    for a in actions:  # the target's own clips give way to the shared set (except --keep-own)
        if a not in own:
            bpy.data.actions.remove(a)
    shared_set = transfer_clips(arm, sarm, [a for a in sactions if a.name not in KEEP_OWN or not own])
    actions = own + shared_set
    if own:
        step('kept own clips: ' + ', '.join(a.name for a in own))
    for o in sobjs:
        bpy.data.objects.remove(o, do_unlink=True)
    for a in sactions:
        bpy.data.actions.remove(a)
if STRIP:
    strip_fingers(arm, meshes)
add_root(arm)
names = map_clips(actions, mapping)
for act in actions:
    act.name = names[act.name] + ' (renaming)'
for act in actions:
    act.name = act.name[:-len(' (renaming)')]
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
