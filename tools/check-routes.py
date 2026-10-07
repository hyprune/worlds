#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Check authored centerlines, navmesh connectivity and default spawn clearance."""
import json,sys,math
from collections import deque
from pathlib import Path
import numpy as np
from gltf_io import Scene
m=json.loads((Path(sys.argv[1])/'world.json').read_text());a=json.loads(Path(sys.argv[2]).read_text())
scene=Scene(sys.argv[1]); exported={}
for ni,name,primitive,pos,indices in scene.primitives(visible=False):
 exported.setdefault(ni,[]).append(pos[indices].reshape(-1,3))
blocks=[]
assert len(m['collision'])==len(a['collisionBoxes'])
for collision,authored in zip(m['collision'],a['collisionBoxes']):
 vertices=np.concatenate(exported[collision['node']]);lo=vertices.min(axis=0);hi=vertices.max(axis=0)
 _,bl,bh=authored
 assert np.allclose(lo,[bl[0],bl[2],-bh[1]],atol=1e-5) and np.allclose(hi,[bh[0],bh[2],-bl[1]],atol=1e-5),'collision export drift'
 if hi[1]>.08 and lo[1]<1.8:blocks.append(([lo[0],-hi[2],lo[1]],[hi[0],-lo[2],hi[1]]))
nav=np.concatenate(exported[m['navigation']['node']]).reshape(-1,3,3)
assert len(nav)==2*len(a['navCells']) and np.allclose(nav[:,:,1],0,atol=1e-6)
assert (np.cross(nav[:,1]-nav[:,0],nav[:,2]-nav[:,0])[:,1]>0).all(),'navigation winding'
center=nav.mean(axis=1);actualCells={(math.floor((v[0]-a['gridOrigin'][0])/a['step']),math.floor((-v[2]-a['gridOrigin'][1])/a['step'])) for v in center}
assert actualCells=={tuple(c) for c in a['navCells']},'navigation export drift'
radius=.3;height=1.8
# Convert world-space foot position to authoring XY.
def free(p):
 x,z,y=p[0],p[1],-p[2]
 if not (-20+radius<=x<=20-radius and -12+radius<=y<=30-radius):return False
 return not any(lo[2]<z+height and hi[2]>z+.01 and max(lo[0]-x,0,x-hi[0])**2+max(lo[1]-y,0,y-hi[1])**2<radius**2-1e-8 for lo,hi in blocks)
for spawn in m['spawns']:assert free(spawn['pose']['position']),('blocked spawn',spawn['id'])
g=m['extensions']['com.hyprune.switchyard.routes'];lookup={p['id']:p['position'] for p in g['nodes']};samples=0
for e in g['edges']:
 p,q=lookup[e['from']],lookup[e['to']];n=math.ceil(math.dist(p,q)/.05)
 for i in range(n+1):
  t=i/n;r=[v*(1-t)+w*t for v,w in zip(p,q)];assert free(r),('blocked route',e,r);samples+=1
cells={tuple(c) for c in a['navCells']};start=next(iter(cells));visited={start};queue=deque([start])
while queue:
 x,y=queue.popleft()
 for p in [(x-1,y),(x+1,y),(x,y-1),(x,y+1)]:
  if p in cells and p not in visited:visited.add(p);queue.append(p)
assert len(cells)==len(visited),('disconnected navigation',len(cells)-len(visited))
for p in lookup.values():
 x,y=p[0],-p[2];cell=(math.floor((x-a['gridOrigin'][0])/a['step']),math.floor((y-a['gridOrigin'][1])/a['step']))
 assert cell in cells,('route node outside navmesh',p)
print(json.dumps({'status':'PASS','routeEdges':len(g['edges']),'centerlineCapsuleSamples':samples,'connectedNavCells':len(cells),'exportedNavTriangles':len(nav),'collisionExportMatchesSource':True,'agentRadius':radius,'agentHeight':height},indent=2))
