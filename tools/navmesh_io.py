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
