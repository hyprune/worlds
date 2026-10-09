#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Share of each lightmap atlas consumed by charts under 2x2 texels, counting
their padded bounding boxes (the bake's margin on every side).
waste.py <dump-dir> <out.json>"""
import json,sys
from pathlib import Path
import numpy as np
d=Path(sys.argv[1]);out_path=Path(sys.argv[2])
src=(Path(__file__).parent/'evaluate.py').read_text();i=src.index('rows=[]')
ns={'__name__':'evaluate'};sys_argv=sys.argv;sys.argv=['x',str(d),'/dev/null'];exec(src[:i],ns);sys.argv=sys_argv
out=[]
for g in ns['groups']:
 z=np.load(d/f"{g['group']}.npz");pos=z['positions'];uv=z['uv'];res=g['resolution'];pad=g['margin']
 ch=ns['charts'](pos,uv);ids,inv=np.unique(ch,return_inverse=True)
 lo=np.full((len(ids),2),9.);hi=np.full((len(ids),2),-9.)
 np.minimum.at(lo,inv,uv.min(axis=1));np.maximum.at(hi,inv,uv.max(axis=1))
 ua=np.abs((uv[:,1,0]-uv[:,0,0])*(uv[:,2,1]-uv[:,0,1])-(uv[:,2,0]-uv[:,0,0])*(uv[:,1,1]-uv[:,0,1]))/2
 px=np.bincount(inv,weights=ua)*res*res;box=np.prod((hi-lo)*res+2*pad,axis=1);tiny=px<4
 out.append({'group':g['group'],'charts':int(len(ids)),'tinyCharts':int(tiny.sum()),'tinyChartsTexelArea':round(float(px[tiny].sum()/res/res),4),'tinyChartsPaddedFootprint':round(float(box[tiny].sum()/res/res),3),'allChartsPaddedFootprint':round(float(box.sum()/res/res),3)})
 print(json.dumps(out[-1]),flush=True)
out_path.write_text(json.dumps(out,indent=1)+'\n')
