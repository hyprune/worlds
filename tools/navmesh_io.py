# SPDX-License-Identifier: MIT
"""Shared Recast navmesh build (recast-navigation-js helper in tools/navmesh/)
for check-navmesh.py and derive-blueprint.py: the package's collision
triangles and one tiled navmesh with the RFC-0004 agent."""
import json,math,subprocess,sys,tempfile
from pathlib import Path
import numpy as np

RADIUS,HEIGHT,CLIMB=.3,1.8,.35   # RFC-0004 capsule; core Camera.hpp, Config.cpp step_height
CELL,STEP=.1,.05
HELPER=Path(__file__).parent/'navmesh'/'navmesh.mjs'

def require_helper():
 if not (HELPER.parent/'node_modules'/'recast-navigation').exists():sys.exit('recast-navigation missing: run `make navmesh-deps` (npm ci in tools/navmesh)')

def collision_triangles(scene):
 """World-space (n,3,3) triangles of every manifest collision node."""
 collision={c['node'] for c in scene.manifest['collision']}
 return np.concatenate([pos[idx] for i,_,_,pos,idx in scene.primitives(visible=False) if i in collision]).astype(float)

def build(tri,slope,points=(),rays=(),widths=()):
 """Tiled navmesh of `tri` with walkable slope `slope` (degrees); polygons
 carry verts, open-edge flags, island ids, area and a numpy `v`."""
 cfg=dict(cs=CELL,ch=STEP,tileSize=128,walkableSlopeAngle=slope,walkableHeight=math.ceil(HEIGHT/STEP-1e-6),
  walkableClimb=math.floor(CLIMB/STEP+1e-6),walkableRadius=math.ceil(RADIUS/CELL-1e-6),maxEdgeLen=int(12/CELL),
  # Region sizes are side lengths in cells (the generator squares them):
  # islands under 0.5 x 0.5 m are dropped.
  maxSimplificationError=1.3,minRegionArea=round(.5/CELL),mergeRegionArea=round(2/CELL),maxVertsPerPoly=6,
  detailSampleDist=1.0,detailSampleMaxError=STEP,
  # Recast clips spans at the heightfield top: a walkable top exactly at the
  # mesh's max height vanishes, so pad the bounds by the agent height.
  bounds=[(tri.min(axis=(0,1))-1).tolist(),(tri.max(axis=(0,1))+[1,HEIGHT+1,1]).tolist()])
 with tempfile.NamedTemporaryFile('w',suffix='.json') as f:
  json.dump({'positions':tri.reshape(-1).round(5).tolist(),'indices':list(range(len(tri)*3)),'config':cfg,
   'points':list(points),'rays':list(rays),'widths':list(widths)},f);f.flush()
  out=subprocess.run(['node',str(HELPER),f.name],capture_output=True,text=True)
 if out.returncode:sys.exit('navmesh helper failed: '+out.stderr[-2000:])
 r=json.loads(out.stdout);r['config']=cfg
 for q in r['polys']:
  v=np.array(q['verts']);q['area']=.5*abs(np.dot(v[:,0],np.roll(v[:,2],1))-np.dot(v[:,2],np.roll(v[:,0],1)));q['v']=v
 return r

class Floor:
 """Point-on-navmesh test over convex Recast polygons (any island)."""
 def __init__(self,polys,cell=2.0):
  self.polys=polys;self.cell=cell;self.grid={}
  for i,q in enumerate(polys):
   v=q['v'];lo=np.floor(v[:,[0,2]].min(0)/cell).astype(int);hi=np.floor(v[:,[0,2]].max(0)/cell).astype(int)
   for gx in range(lo[0],hi[0]+1):
    for gz in range(lo[1],hi[1]+1):self.grid.setdefault((gx,gz),[]).append(i)
 def find(self,p,reach=0.,dy=.4):
  """Index of a polygon whose surface is within `reach` horizontally and `dy`
  vertically of feet point p, else None."""
  key=(int(math.floor(p[0]/self.cell)),int(math.floor(p[2]/self.cell)));best=None
  for gx in range(key[0]-1,key[0]+2):
   for gz in range(key[1]-1,key[1]+2):
    for i in self.grid.get((gx,gz),()):
     v=self.polys[i]['v'];d=self.distance(v,p)
     if d<=reach and abs(self.height(v,p)-p[1])<=dy and (best is None or d<best[0]):best=(d,i)
  return None if best is None else best[1]
 @staticmethod
 def distance(v,p):
  # Horizontal distance from p to a convex polygon (0 inside).
  q=np.array([p[0],p[2]]);xz=v[:,[0,2]];n=len(xz);inside=True;best=1e9
  area=np.sum(xz[:,0]*np.roll(xz[:,1],-1)-np.roll(xz[:,0],-1)*xz[:,1])
  for j in range(n):
   a,b=xz[j],xz[(j+1)%n];e=b-a;cross=e[0]*(q[1]-a[1])-e[1]*(q[0]-a[0])
   if cross*area<0:inside=False
   t=np.clip(np.dot(q-a,e)/max(np.dot(e,e),1e-12),0,1);best=min(best,float(np.linalg.norm(a+e*t-q)))
  return 0. if inside else best
 @staticmethod
 def height(v,p):
  # Plane height of the polygon under p (Recast polygons are near planar).
  a,b,c=v[0],v[1],v[2];n=np.cross(b-a,c-a)
  if abs(n[1])<1e-9:return float(v[:,1].mean())
  return float(a[1]-(n[0]*(p[0]-a[0])+n[2]*(p[2]-a[2]))/n[1])
