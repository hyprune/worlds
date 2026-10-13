#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Same-facing coplanar overlaps in any plane orientation (check-coplanar.py scans
axis-aligned faces only, on a 0.10 m grid).

Core's depth buffer is 24-bit with a 0.05 m near plane: about 0.5 mm resolution at
20 m and 4 mm at 60 m, so same-facing triangles closer than GAP whose interiors
overlap depth-fight. Triangles are grouped by normal (rounded to 1/1000) and their
plane offsets chained within GAP; every overlapping pair closer than GAP is sampled
on a STEP grid in the intersection of its bounding boxes. Pairs are reported by
scene node and material, with their summed overlap area and one sample point.
Two triangles of one material without a baked lightmap (unlit vista art, its UV0
in world space) shade the same where they overlap: such pairs are listed as
identical and not gated. The gate fails when any other pair overlaps more than
--max-pair square metres or all of them together more than --max-total. GAP 6 mm
fights from about 65 m on.

  check-coplanar-planes.py PACKAGE [--gap 0.006] [--step 0.02] [--max-pair 0.1]
                           [--max-total 2.0] [--output REPORT.json]
"""
import argparse, json
from collections import defaultdict
from pathlib import Path
import numpy as np
from gltf_io import load

p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
p.add_argument('package', type=Path); p.add_argument('--gap', type=float, default=.006); p.add_argument('--step', type=float, default=.02)
p.add_argument('--min-area', type=float, default=.0004); p.add_argument('--max-pair', type=float, default=.1); p.add_argument('--max-total', type=float, default=2.0)
p.add_argument('--output', type=Path); a = p.parse_args()
s = load(a.package); T = []; NAME = []; MAT = []
LIT = {b['material'] for b in s.manifest.get('lightmaps', [])}; UNBAKED = set()
for _, name, prim, pos, idx in s.primitives():
    T.append(pos[idx]); NAME += [name]*len(idx); MAT += [s.doc['materials'][prim['material']]['name'] if 'material' in prim else '']*len(idx)
    if prim.get('material') not in LIT:
        UNBAKED.add(s.doc['materials'][prim['material']]['name'] if 'material' in prim else '')
T = np.concatenate(T).astype(np.float64)
n = np.cross(T[:, 1]-T[:, 0], T[:, 2]-T[:, 0]); area = np.linalg.norm(n, axis=1)*.5; ok = area > 1e-7; n[ok] /= (2*area[ok])[:, None]
d = np.einsum('ij,ij->i', n, T[:, 0]); q = np.round(n*1000).astype(int)
byn = defaultdict(list)
for i in np.where(ok)[0]:
    byn[tuple(q[i])].append(i)


def basis(nn):
    t = np.array([1., 0, 0]) if abs(nn[0]) < .9 else np.array([0, 1., 0]); u = np.cross(nn, t); u /= np.linalg.norm(u)
    return u, np.cross(nn, u)


def inside(pts, tri):
    a0, b0, c0 = tri; v0 = c0-a0; v1 = b0-a0; v2 = pts-a0
    d00, d01, d11 = v0@v0, v0@v1, v1@v1; d20, d21 = v2@v0, v2@v1; den = d00*d11-d01*d01
    if abs(den) < 1e-14:
        return np.zeros(len(pts), bool)
    v = (d11*d20-d01*d21)/den; w = (d00*d21-d01*d20)/den
    return (v > 1e-6) & (w > 1e-6) & (v+w < 1-1e-6)


pairs = defaultdict(lambda: {'area': 0., 'gap': 0., 'at': None})
for ids in byn.values():
    if len(ids) < 2:
        continue
    ids = np.array(ids); ids = ids[np.argsort(d[ids])]
    for cl in np.split(ids, np.where(np.diff(d[ids]) > a.gap)[0]+1):
        if len(cl) < 2:
            continue
        nn = n[cl[0]]; u, v = basis(nn); P2 = np.stack([T[cl]@u, T[cl]@v], -1); lo = P2.min(1); hi = P2.max(1); order = np.argsort(lo[:, 0])
        for k, i in enumerate(order):
            for j in order[k+1:]:
                if lo[j, 0] >= hi[i, 0]:
                    break
                if lo[j, 1] >= hi[i, 1] or hi[j, 1] <= lo[i, 1] or abs(d[cl[i]]-d[cl[j]]) >= a.gap:
                    continue
                bl = np.maximum(lo[i], lo[j]); bh = np.minimum(hi[i], hi[j])
                if (bh-bl).min() < a.step*.5:
                    continue
                xs = np.arange(bl[0]+a.step/2, bh[0], a.step); ys = np.arange(bl[1]+a.step/2, bh[1], a.step)
                g = np.stack(np.meshgrid(xs, ys), -1).reshape(-1, 2)
                m = inside(g, P2[i]) & inside(g, P2[j]); c = int(m.sum())
                if not c:
                    continue
                ti, tj = cl[i], cl[j]; key = tuple(sorted([(NAME[ti], MAT[ti]), (NAME[tj], MAT[tj])]))
                r = pairs[key]; r['area'] += c*a.step*a.step; r['gap'] = max(r['gap'], abs(float(d[ti]-d[tj])))
                if r['at'] is None:
                    pp = g[m][0]; r['at'] = [round(float(x), 3) for x in pp[0]*u+pp[1]*v+d[ti]*nn]; r['normal'] = [round(float(x), 3) for x in nn]
rows = sorted(({'a': list(k[0]), 'b': list(k[1]), 'area': round(r['area'], 4), 'gap': round(r['gap'], 4), 'normal': r['normal'], 'at': r['at'],
                 'identical': k[0] == k[1] and k[0][1] in UNBAKED}
               for k, r in pairs.items() if r['area'] >= a.min_area), key=lambda r: -r['area'])
gated = [r for r in rows if not r['identical']]
total = round(sum(r['area'] for r in gated), 4)
status = 'PASS' if (not gated or gated[0]['area'] <= a.max_pair) and total <= a.max_total else 'FAIL'
report = {'status': status, 'gapMetres': a.gap, 'stepMetres': a.step, 'maxPairM2': a.max_pair, 'maxTotalM2': a.max_total,
          'pairs': len(gated), 'totalM2': total, 'largestM2': gated[0]['area'] if gated else 0,
          'identicalPairs': len(rows)-len(gated), 'identicalM2': round(sum(r['area'] for r in rows if r['identical']), 4), 'rows': rows}
text = json.dumps(report, indent=1)+'\n'
if a.output:
    a.output.parent.mkdir(parents=True, exist_ok=True); a.output.write_text(text)
print(json.dumps({k: v for k, v in report.items() if k != 'rows'}))
raise SystemExit(0 if status == 'PASS' else 1)
