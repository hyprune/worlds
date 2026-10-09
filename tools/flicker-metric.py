#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Temporal shimmer from lumen-measure-session.py flicker frames.

Frames are held stills at 3.5 m/s walking, 1/60 s apart, pitched 0.10-0.12 rad
down with a 60 deg FOV. The band 0.44-0.52 of the image height sees floor at
roughly 15-60 m. Per pixel luminance L(t): smooth motion gives small second
differences L(t+1)-2L(t)+L(t-1); shimmer and crawling texels give large ones.
Reports mean |second difference| and its 95th percentile (0-255 luminance),
plus mean |first difference| for scale, per variant and path.
flicker-metric.py <report.json> [--output out.json]
"""
import argparse,json
from pathlib import Path
import numpy as np
from PIL import Image
p=argparse.ArgumentParser(description=__doc__,formatter_class=argparse.RawDescriptionHelpFormatter);p.add_argument('report',type=Path);p.add_argument('--output',type=Path);a=p.parse_args()
r=json.loads(a.report.read_text());rows=[]
for run in r['paths']:
 L=[]
 for f in run['frames']:
  im=np.asarray(Image.open(f).convert('RGB'),dtype=np.float32);h,w,_=im.shape
  band=im[int(.44*h):int(.52*h),int(.1*w):int(.9*w)];L.append(band@np.array([.2126,.7152,.0722],dtype=np.float32))
 L=np.stack(L);d1=np.abs(np.diff(L,axis=0));d2=np.abs(L[2:]-2*L[1:-1]+L[:-2])
 rows.append({'variant':run['variant'],'path':run['path'],'frames':len(L),'meanAbsSecondDiff':round(float(d2.mean()),4),'p95AbsSecondDiff':round(float(np.percentile(d2,95)),3),'meanAbsFirstDiff':round(float(d1.mean()),4)})
out={'method':__doc__.strip(),'rows':rows}
text=json.dumps(out,indent=1)+'\n'
if a.output:a.output.parent.mkdir(parents=True,exist_ok=True);a.output.write_text(text)
for x in rows:print(x)
