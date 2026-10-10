#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Compare two any-angle sweeps of the same package with different visibility
(e.g. hand-written vs tools/derive-visibility.py) at identical poses.

Per view, from core's timings: batches submitted, region-culled and
frustum-culled out of the world's total. Identical frames: each sweep's
culling-on still vs its culling-off still (correctness), and A's still vs
B's still (changed pixels with any channel differing by more than 8 levels).
compare-visibility-sweeps.py <A/report.json> <B/report.json> [--output json]
"""
import argparse,json,statistics
from pathlib import Path
import numpy as np
from PIL import Image
p=argparse.ArgumentParser(description=__doc__,formatter_class=argparse.RawDescriptionHelpFormatter);p.add_argument('a',type=Path);p.add_argument('b',type=Path);p.add_argument('--output',type=Path);x=p.parse_args()
A,B=json.loads(x.a.read_text()),json.loads(x.b.read_text())
bv={v['id']:v for v in B['views']};rows=[]
def diff(p,q):
 a=np.asarray(Image.open(p).convert('RGB'),dtype=np.int16)[100:-100,100:-100];b=np.asarray(Image.open(q).convert('RGB'),dtype=np.int16)[100:-100,100:-100]
 return float(np.mean(np.abs(a-b).max(axis=2)>8))
for va in A['views']:
 vb=bv.get(va['id'])
 if not vb:continue
 ta,tb=va['timings']['visibility'],vb['timings']['visibility']
 rows.append({'id':va['id'],'kind':va['kind'],'total':ta['total'],'submittedA':ta['submitted'],'submittedB':tb['submitted'],'regionCulledA':ta['culled'],'regionCulledB':tb['culled'],'frustumCulledA':ta['frustumCulled'],'frustumCulledB':tb['frustumCulled'],
  'cullingChangedA':va.get('cullingChangedPixelFraction'),'cullingChangedB':vb.get('cullingChangedPixelFraction'),'changedAB':diff(va['path'],vb['path'])})
sa=[r['submittedA'] for r in rows];sb=[r['submittedB'] for r in rows]
summary={'views':len(rows),'batchesTotal':rows[0]['total'],'submittedMean':{'A':round(statistics.mean(sa),2),'B':round(statistics.mean(sb),2)},'submittedMedian':{'A':statistics.median(sa),'B':statistics.median(sb)},
 'regionCulledMean':{'A':round(statistics.mean(r['regionCulledA'] for r in rows),2),'B':round(statistics.mean(r['regionCulledB'] for r in rows),2)},
 'viewsBFewer':sum(b<a for a,b in zip(sa,sb)),'viewsEqual':sum(b==a for a,b in zip(sa,sb)),'viewsBMore':sum(b>a for a,b in zip(sa,sb)),
 'identicalCulledVsUnculled':{'A':sum((r['cullingChangedA'] or 0)==0 for r in rows),'B':sum((r['cullingChangedB'] or 0)==0 for r in rows)},
 'identicalAvsB':sum(r['changedAB']==0 for r in rows),'maxChangedAB':max(r['changedAB'] for r in rows)}
out={'method':__doc__.strip(),'a':str(x.a),'b':str(x.b),'summary':summary,'views':rows}
if x.output:x.output.write_text(json.dumps(out,indent=1)+'\n')
print(json.dumps(summary,indent=1))
