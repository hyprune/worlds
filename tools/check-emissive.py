# SPDX-License-Identifier: MIT
"""Triangle-interior probes for thin emissive trims, independent of the 10cm grid.
Three interior probes per triangle; all orientations, every visible solid host.
Also verifies the pre-merge named mechanical mounting audit when supplied.
"""
import json,itertools
from collections import defaultdict
from pathlib import Path
import numpy as np
from gltf_io import Scene

def check(root, fixture_report=None, surfaces=False):
 s=Scene(root);triangles=[];names=[];emit=[]
 for _,name,p,positions,indices in s.primitives():
  m=s.doc['materials'][p['material']]
  if 'KHR_materials_unlit' in m.get('extensions',{}):continue
  vs=positions[indices];triangles.extend(vs);names.extend([name+'/'+m['name']]*len(vs));emit.extend([any(m.get('emissiveFactor',[0,0,0]))]*len(vs))
 t=np.asarray(triangles);norm=np.cross(t[:,1]-t[:,0],t[:,2]-t[:,0]);length=np.linalg.norm(norm,axis=1);norm/=np.maximum(length[:,None],1e-20);lo=t.min(axis=1)-.004;hi=t.max(axis=1)+.004
 grid=defaultdict(list);step=2.0
 for j,(a,b) in enumerate(zip(lo,hi)):
  low=np.floor(a/step).astype(int);high=np.floor(b/step).astype(int)
  for key in itertools.product(*(range(low[k],high[k]+1) for k in range(3))):grid[key].append(j)
 grid={k:np.array(v,dtype=int) for k,v in grid.items()}
 hits=[];tested=0
 for i in np.flatnonzero(length>.004 if surfaces else emit):
  if length[i]<1e-9:continue
  tested+=1
  for weights in [(.6,.2,.2),(.2,.6,.2),(.2,.2,.6)]:
   p=np.array(weights)@t[i];idx=grid.get(tuple(np.floor(p/step).astype(int)),np.array([],dtype=int));idx=idx[(idx!=i)&((p>=lo[idx])&(p<=hi[idx])).all(axis=1)]
   if not len(idx):continue
   # Opposite-facing box backs are not z-fighting surfaces.
   idx=idx[norm[idx]@norm[i]>.99999]
   if not len(idx):continue
   distance=np.abs(np.einsum('ij,ij->i',p-t[idx,0],norm[idx]));idx=idx[distance<.0039]
   if not len(idx):continue
   a=t[idx,0];u=t[idx,1]-a;v=t[idx,2]-a;w=p-a
   uu=np.einsum('ij,ij->i',u,u);uv=np.einsum('ij,ij->i',u,v);vv=np.einsum('ij,ij->i',v,v);wu=np.einsum('ij,ij->i',w,u);wv=np.einsum('ij,ij->i',w,v);den=uu*vv-uv*uv
   f=(wu*vv-wv*uv)/np.maximum(den,1e-30);h=(wv*uu-wu*uv)/np.maximum(den,1e-30)
   for j in idx[(f>1e-5)&(h>1e-5)&(f+h<1-1e-5)]:
    if j>i or not emit[j]:hits.append({'emissive':names[i],'other':names[j],'point':p.tolist()})
 rows=json.loads(Path(fixture_report).read_text()) if fixture_report else None
 return {'status':'FAIL' if hits or (rows and rows['status']!='PASS') else 'PASS','method':'three triangle-interior probes, all orientations, 3.9mm same-facing tolerance','emissiveTriangles':int(np.sum(emit)),'probedTriangles':tested,'scope':'physical surfaces above 20 square centimeters' if surfaces else 'all emissive triangles','stacks':hits,'mechanicalMounts':rows,'limitations':'Interior probes are not an exhaustive polygon-intersection proof; mounting rays additionally audit every named thin strip before mesh merging.'}
