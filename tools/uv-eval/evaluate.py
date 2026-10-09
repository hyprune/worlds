#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""xatlas vs Blender smart_project for Lumen's lightmap groups (bake host venv
with xatlas 0.0.10). Same resolution and padding as the bake. Metrics per group:
coverage (UV area used), texel density (area-weighted median px/m, CV), chart
count, collapsed-island risk (charts under 2x2 texels, zero-area UV
triangles), unwrap+pack seconds, atlas count.
evaluate.py <dump-dir> <out.json>"""
import json,sys,time
from pathlib import Path
import numpy as np,xatlas
d=Path(sys.argv[1]);groups=json.loads((d/'groups.json').read_text())
def charts(pos,uv):
 """Connected components over shared UV edges (same position and UV)."""
 key=np.round(np.concatenate([pos,uv],axis=2).reshape(-1,5),6);_,vid=np.unique(key,axis=0,return_inverse=True);vid=vid.reshape(-1,3)
 parent=list(range(len(pos)))
 def find(i):
  r=i
  while parent[r]!=r:r=parent[r]
  while parent[i]!=r:parent[i],i=r,parent[i]
  return r
 edges={}
 for t,(a,b,c) in enumerate(vid):
  for e in [(a,b),(b,c),(c,a)]:
   e=tuple(sorted(e))
   if e in edges:
    x,y=find(t),find(edges[e])
    if x!=y:parent[x]=y
   else:edges[e]=t
 return np.array([find(t) for t in range(len(pos))])
def metrics(pos,uv,res,seconds,extra={}):
 w=np.linalg.norm(np.cross(pos[:,1]-pos[:,0],pos[:,2]-pos[:,0]),axis=1)/2
 ua=np.abs((uv[:,1,0]-uv[:,0,0])*(uv[:,2,1]-uv[:,0,1])-(uv[:,2,0]-uv[:,0,0])*(uv[:,1,1]-uv[:,0,1]))/2
 ok=w>1e-10;dens=np.sqrt(ua[ok]*res*res/w[ok]);wt=w[ok]/w[ok].sum()
 order=np.argsort(dens);cum=np.cumsum(wt[order]);med=float(dens[order][np.searchsorted(cum,.5)]);mean=float((dens*wt).sum());cv=float(np.sqrt(((dens-mean)**2*wt).sum())/mean)
 ch=charts(pos,uv);ids,inv=np.unique(ch,return_inverse=True);chart_px=np.bincount(inv,weights=ua)*res*res
 return {'coverage':round(float(ua.sum()),4),'densityMedianPxPerM':round(med,2),'densityCV':round(cv,3),'charts':int(len(ids)),'chartsUnder2x2Texels':int((chart_px<4).sum()),'zeroAreaUVTriangles':int((ua<1e-12).sum()),'seconds':round(seconds,2),**extra}
rows=[]
for g in groups:
 z=np.load(d/f"{g['group']}.npz");pos=z['positions'];uv=z['uv'];res=g['resolution']
 row={'group':g['group'],'triangles':g['triangles'],'resolution':res,'paddingPx':g['margin'],'bakeSeconds':g['bakeSeconds']}
 row['blender']=metrics(pos,uv,res,g['blenderUnwrapSeconds'])
 key=np.round(pos.reshape(-1,3),6);verts,idx=np.unique(key,axis=0,return_inverse=True)
 # xatlas only approximates `resolution` when texels_per_unit is 0, so shrink
 # texels_per_unit until a single atlas fits res x res at the full padding.
 t=time.time();tpu=0;passes=0
 while True:
  atlas=xatlas.Atlas();atlas.add_mesh(verts.astype(np.float32),idx.reshape(-1,3).astype(np.uint32))
  po=xatlas.PackOptions();po.resolution=res;po.padding=g['margin'];po.bilinear=True;po.rotate_charts=True;po.texels_per_unit=tpu
  atlas.generate(xatlas.ChartOptions(),po);passes+=1
  if atlas.atlas_count==1 and atlas.width<=res and atlas.height<=res:break
  tpu=atlas.texels_per_unit*min(1,res/max(atlas.width,atlas.height))*(.97 if atlas.atlas_count==1 else .85)
 seconds=time.time()-t
 vmap,faces,xuv=atlas[0];xpos=verts[vmap][faces]
 # Normalised to xatlas's atlas size; that atlas sits in the bake's res image.
 xu=xuv[faces]*np.array([atlas.width/res,atlas.height/res]);assert xu.max()<=1+1e-6
 # xatlas scales its texel size to fit resolution; >1 atlas means it spilled.
 row['xatlas']=metrics(xpos.astype(float),xu.astype(float),res,seconds,{'atlasCount':int(atlas.atlas_count),'packPasses':passes,'texelsPerUnit':round(float(atlas.texels_per_unit),3),'utilization':round(float(atlas.get_utilization(0)),4),'atlasSize':[int(atlas.width),int(atlas.height)]})
 np.savez_compressed(d/f"{g['group']}-xatlas.npz",positions=xpos,uv=xu,faces=faces,vmap=vmap)
 rows.append(row);print(json.dumps(row),flush=True)
Path(sys.argv[2]).write_text(json.dumps({'tool':'xatlas 0.0.10 (python bindings, MIT) vs Blender 5.2 smart_project+pack_islands','groups':rows},indent=1)+'\n')
