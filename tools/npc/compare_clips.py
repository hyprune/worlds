#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Compare two clips of the same skeleton (local rotations per bone, per frame).

    compare_clips.py A.glb CLIP_A B.glb CLIP_B  ->  median and worst bones (degrees)

For checking a retargeted clip against a rig's own clip as ground truth."""
import json, math, struct, sys
import numpy as np

def load(path):
    d = open(path, 'rb').read()
    n = struct.unpack('<I', d[12:16])[0]
    g = json.loads(d[20:20 + n]); b = d[20 + n + 8:]
    return g, b
def acc(g, b, i):
    a = g['accessors'][i]; v = g['bufferViews'][a['bufferView']]
    k = {'SCALAR': 1, 'VEC3': 3, 'VEC4': 4}[a['type']]
    return np.frombuffer(b, np.float32, a['count'] * k, v.get('byteOffset', 0) + a.get('byteOffset', 0)).reshape(a['count'], k)
def clip(g, b, name):
    a = next(x for x in g['animations'] if x['name'] == name)
    out = {}
    for c in a['channels']:
        if c['target']['path'] == 'rotation':
            s = a['samplers'][c['sampler']]
            out[g['nodes'][c['target']['node']]['name']] = (acc(g, b, s['input'])[:, 0], acc(g, b, s['output']))
    return out
def angle(p, q):
    d = abs(float(np.dot(p, q)) / (np.linalg.norm(p) * np.linalg.norm(q)))
    return math.degrees(2 * math.acos(min(1, d)))
ga, ba = load(sys.argv[1]); gb, bb = load(sys.argv[3])
ca, cb = clip(ga, ba, sys.argv[2]), clip(gb, bb, sys.argv[4])
bones = sorted(set(ca) & set(cb))
errs = {}
for bone in bones:
    ta, va = ca[bone]; tb, vb = cb[bone]
    n = min(len(va), len(vb))
    # resample both to n phases of their own cycle (clips may differ in length)
    ia = np.linspace(0, len(va) - 1, n).round().astype(int); ib = np.linspace(0, len(vb) - 1, n).round().astype(int)
    errs[bone] = [angle(va[i], vb[j]) for i, j in zip(ia, ib)]
med = {b: float(np.median(e)) for b, e in errs.items()}
worst = {b: float(np.max(e)) for b, e in errs.items()}
legs = [b for b in bones if any(k in b for k in ('UpLeg', 'Leg', 'Foot'))]
print(json.dumps({'medianDeg': round(float(np.median(list(med.values()))), 2),
                  'legsMedianDeg': round(float(np.median([med[b] for b in legs])), 2) if legs else None,
                  'legsWorstDeg': round(max(worst[b] for b in legs), 1) if legs else None,
                  'worstBones': [(b.split(':')[-1], round(worst[b], 1)) for b in sorted(worst, key=lambda b: -worst[b])[:6]]}))


def qmul(a, b):
    x1, y1, z1, w1 = a; x2, y2, z2, w2 = b
    return np.array([w1 * x2 + x1 * w2 + y1 * z2 - z1 * y2, w1 * y2 - x1 * z2 + y1 * w2 + z1 * x2,
                     w1 * z2 + x1 * y2 - y1 * x2 + z1 * w2, w1 * w2 - x1 * x2 - y1 * y2 - z1 * z2])
def qrot(q, v):
    return qmul(qmul(q, np.array([v[0], v[1], v[2], 0.0])), np.array([-q[0], -q[1], -q[2], q[3]]))[:3]
def sliding(g, b, name):
    """Foot sliding of an in-place locomotion clip: the planted foot should move back at one
    steady speed. Returns the median planted-foot speed and its spread (mean |v - median| / median)."""
    a = next(x for x in g['animations'] if x['name'] == name)
    ch = {}
    for c in a['channels']:
        s = a['samplers'][c['sampler']]
        ch[(c['target']['node'], c['target']['path'])] = (acc(g, b, s['input'])[:, 0], acc(g, b, s['output']))
    parent = {c: i for i, n in enumerate(g['nodes']) for c in n.get('children', [])}
    names = {n.get('name'): i for i, n in enumerate(g['nodes'])}
    feet = [names[n] for n in ('mixamorig:LeftToeBase', 'mixamorig:RightToeBase') if n in names]
    frames = max(len(v[0]) for v in ch.values())
    track = []
    for k in range(frames):
        cache = {}
        def world(i):
            if i in cache: return cache[i]
            n = g['nodes'][i]
            r = ch[(i, 'rotation')][1][min(k, len(ch[(i, 'rotation')][1]) - 1)] if (i, 'rotation') in ch else np.array(n.get('rotation', [0, 0, 0, 1]), float)
            t = ch[(i, 'translation')][1][min(k, len(ch[(i, 'translation')][1]) - 1)] if (i, 'translation') in ch else np.array(n.get('translation', [0, 0, 0]), float)
            if i in parent:
                pr, pt = world(parent[i]); cache[i] = (qmul(pr, r), pt + qrot(pr, t))
            else:
                cache[i] = (np.array(r, float), np.array(t, float))
            return cache[i]
        track.append({f: world(f)[1] for f in feet})
    fps = 30
    low = min(p[f][1] for p in track for f in feet)
    v = []
    for k in range(len(track) - 1):
        f = min(feet, key=lambda f: track[k][f][1])
        if track[k][f][1] < low + .03:
            d = track[k + 1][f] - track[k][f]; v.append(math.hypot(d[0], d[2]) * fps)
    if not v:
        return None
    m = float(np.median(v))
    return {'plantedSpeed': round(m, 3), 'slide': round(float(np.mean([abs(x - m) for x in v])) / max(m, 1e-6), 3)}
if len(sys.argv) > 5 and sys.argv[5] == '--sliding':
    print(json.dumps({'a': sliding(ga, ba, sys.argv[2]), 'b': sliding(gb, bb, sys.argv[4])}))
