#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Primary workspace frames are 16:9 and area signs sit clear of other geometry.

Owner live test, 0.9.0: the Sun Court and Array Hall walls were not the
workspace's aspect (a 3840x2160 window letterboxed inside them) and the
"01 SUN COURT" / "02 ARRAY HALL" signs ran into the cornice and the roof.
- frames: every primary anchor (mount role mounted-workspace, one per area)
  is 16:9 within 0.5 %, and its placeholder screen (the area's
  ui-<theme>-workspace material) exactly fills the anchor rectangle (1 cm).
  Tool mounts, kiosks and data screens keep their varied aspects on purpose.
- signs: for each sign in the package's sign-audit.json (written by the
  build's label()), no visible triangle other than the sign's own letters
  enters the box spanning the plaque face and 0.5 m of air in front of it.
"""
import argparse,json,sys
from pathlib import Path
import numpy as np
sys.path.insert(0,str(Path(__file__).parent))
from gltf_io import Scene
p=argparse.ArgumentParser(description=__doc__);p.add_argument('package',type=Path);p.add_argument('--output',type=Path);a=p.parse_args()
s=Scene(a.package);m=s.manifest
ASPECT,ASPECT_TOL,FILL_TOL=16/9,.005,.01
tri=[];mats=[]
for _,name,prim,pos,idx in s.primitives():
 tri.append(pos[idx]);mats.extend([s.doc['materials'][prim['material']].get('name','') if 'material' in prim else '']*len(idx))
tri=np.concatenate(tri).astype(float);mats=np.array(mats);lo=tri.min(axis=1);hi=tri.max(axis=1)

def rotation(q):
 x,y,z,w=q
 return np.array([[1-2*(y*y+z*z),2*(x*y-z*w),2*(x*z+y*w)],[2*(x*y+z*w),1-2*(x*x+z*z),2*(y*z-x*w)],[2*(x*z-y*w),2*(y*z+x*w),1-2*(x*x+y*y)]])

anchors={x['id']:x for x in m['anchors']};frames=[];failures=[]
for area in m['areas']:
 an=anchors[area['primaryAnchor']];role=an.get('mount',{}).get('role')
 w,h=an['size'];ratio=w/h;row={'area':area['id'],'anchor':an['id'],'role':role,'size':[w,h],'aspect':round(ratio,5),'aspectError':round(ratio/ASPECT-1,5)}
 # The placeholder quad in the anchor's own axes (local x right, y up).
 sel=tri[mats==f"vista--ui-{area['theme']}-workspace"].reshape(-1,3)
 if len(sel):
  local=(sel-np.array(an['pose']['position']))@rotation(an['pose']['rotation'])
  row['placeholderSize']=[round(float(np.ptp(local[:,0])),4),round(float(np.ptp(local[:,1])),4)];row['placeholderCentre']=[round(float(v),4) for v in (local.min(axis=0)+local.max(axis=0))[:2]/2]
 ok=role=='mounted-workspace' and abs(ratio/ASPECT-1)<=ASPECT_TOL and len(sel)>0 and all(abs(u-v)<=FILL_TOL for u,v in zip(row['placeholderSize'],[w,h])) and all(abs(c)<=FILL_TOL for c in row['placeholderCentre'])
 row['status']='PASS' if ok else 'FAIL';frames.append(row)
 if not ok:failures.append(f"frame {an['id']}: {row}")

def overlaps(t,bmin,bmax):
 """Triangle/box separating-axis test, vectorised over triangles."""
 c=(bmin+bmax)/2;e=(bmax-bmin)/2;v=t-c;f=[v[:,1]-v[:,0],v[:,2]-v[:,1],v[:,0]-v[:,2]];ok=np.ones(len(t),bool)
 for i in range(3):
  for edge in f:
   ax=np.cross(np.eye(3)[i],edge);pr=np.einsum('nk,nvk->nv',ax,v);r=np.abs(ax)@e
   ok&=~((pr.min(axis=1)>r)|(pr.max(axis=1)<-r))
 n=np.cross(f[0],f[1]);d=np.einsum('nk,nk->n',n,v[:,0]);ok&=np.abs(d)<=np.abs(n)@e
 return ok

signs=[];audit=a.package/'sign-audit.json'
if not audit.exists():failures.append('sign-audit.json missing from the package')
for sg in json.loads(audit.read_text())['signs'] if audit.exists() else []:
 bmin=np.minimum(sg['min'],sg['max']);bmax=np.maximum(sg['min'],sg['max'])
 near=np.nonzero(np.all(hi>=bmin,axis=1)&np.all(lo<=bmax,axis=1))[0]
 # The sign's own letters: flat quads in the letter plane.
 own=np.all(np.abs(tri[near,:,2]-sg['letterPlane'])<1e-3,axis=1)&np.char.endswith(mats[near].astype(str),'--'+sg.get('material','ivory'))
 near=near[~own];hit=near[overlaps(tri[near],bmin,bmax)]
 row={'word':sg['word'],'box':{'min':bmin.round(3).tolist(),'max':bmax.round(3).tolist()},'intruding':int(len(hit)),'materials':sorted({k.split('--')[-1] for k in mats[hit]})}
 if len(hit):row['intrusion']={'min':tri[hit].reshape(-1,3).min(axis=0).round(3).tolist(),'max':tri[hit].reshape(-1,3).max(axis=0).round(3).tolist()};failures.append(f"sign {sg['word']!r}: {len(hit)} triangles ({','.join(row['materials'])}) in its clear volume")
 row['status']='FAIL' if len(hit) else 'PASS';signs.append(row)
report={'status':'FAIL' if failures else 'PASS','aspect':'16:9','aspectTolerance':ASPECT_TOL,'fillToleranceMeters':FILL_TOL,'primaryFrames':frames,'signs':signs,'failures':failures}
text=json.dumps(report,indent=1)+'\n'
if a.output:a.output.write_text(text)
print(text,end='');sys.exit(1 if failures else 0)
