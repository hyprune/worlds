# SPDX-License-Identifier: MIT
"""The Recast navmesh gate must catch collision regressions a route graph hides.

A synthetic package: a 24 x 12 m floor, a ramp up to a 4 m platform, routes
over both. Mutations (wall across a route, over-steep ramp, narrow door, a
hop-up block) must fail; a reviewed allow-list entry must accept exactly its
finding. Needs node and tools/navmesh/node_modules (npm ci there).
"""
import json,subprocess,sys,tempfile,unittest
from pathlib import Path
import numpy as np
ROOT=Path(__file__).resolve().parents[1]
FACES=[(0,1,2),(0,2,3),(4,6,5),(4,7,6),(0,5,1),(0,4,5),(1,6,2),(1,5,6),(2,7,3),(2,6,7),(3,4,0),(3,7,4)]  # outward CCW

def box(lo,hi):
 (x0,y0,z0),(x1,y1,z1)=lo,hi
 return [[x0,y0,z0],[x1,y0,z0],[x1,y0,z1],[x0,y0,z1],[x0,y1,z0],[x1,y1,z0],[x1,y1,z1],[x0,y1,z1]]

def ramp(x0,x1,ztop,zfoot,rise):
 """Solid wedge rising from 0 at zfoot (south) to `rise` at ztop (north)."""
 c=box([x0,-.2,ztop],[x1,0,zfoot]);c[4][1]=c[5][1]=rise;return c

class NavmeshGate(unittest.TestCase):
 def package(self,solids,allow=None):
  temp=tempfile.TemporaryDirectory();self.addCleanup(temp.cleanup);root=Path(temp.name)
  pts=np.array([v for s in solids for v in s],'<f4');idx=np.array([FACES for _ in solids],'<u4').reshape(-1)
  (root/'scene.bin').write_bytes(pts.tobytes()+idx.tobytes())
  views=[{'buffer':0,'byteLength':pts.nbytes},{'buffer':0,'byteOffset':pts.nbytes,'byteLength':idx.nbytes}]
  acc=[];meshes=[];nodes=[]
  for i in range(len(solids)):
   acc+=[{'bufferView':0,'byteOffset':i*96,'componentType':5126,'count':8,'type':'VEC3'},{'bufferView':1,'byteOffset':i*144,'componentType':5125,'count':36,'type':'SCALAR'}]
   meshes.append({'primitives':[{'attributes':{'POSITION':2*i},'indices':2*i+1}]});nodes.append({'mesh':i,'name':f'Collision-{i}'})
  doc={'asset':{'version':'2.0'},'buffers':[{'uri':'scene.bin','byteLength':pts.nbytes+idx.nbytes}],'bufferViews':views,'accessors':acc,'meshes':meshes,'nodes':nodes,'scenes':[{'nodes':list(range(len(nodes)))}]}
  (root/'scene.gltf').write_text(json.dumps(doc))
  route={'nodes':[{'id':'a','position':[-9,0,10.5]},{'id':'b','position':[9,0,10.5]},{'id':'foot','position':[6,0,10.5]},{'id':'top','position':[6,3,-3]},{'id':'deck','position':[0,3,-3]}],
   'edges':[{'from':'a','to':'b'},{'from':'b','to':'foot'},{'from':'foot','to':'top'},{'from':'top','to':'deck'}]}
  world={'id':'test.navmesh','version':'0','scene':'scene.gltf','defaultSpawn':'a','spawns':[{'id':'a','pose':{'position':[-9,0,10.5],'rotation':[0,0,0,1]}}],
   'anchors':[],'collision':[{'node':i,'shape':'mesh','layer':'static'} for i in range(len(nodes))],
   'visibility':{'areas':[{'id':'all','bounds':{'min':[-13,-1,-7],'max':[13,9,13]}}]},
   'extensions':{'test.routes':route,'test.stairs':{'paths':[{'id':'ramp','from':[6,0,9],'to':[6,3,-1.5],'width':2}]}}}
  (root/'world.json').write_text(json.dumps(world))
  cmd=[sys.executable,str(ROOT/'tools/check-navmesh.py'),str(root),'--output',str(root/'report.json')]
  if allow:(root/'allow.json').write_text(json.dumps(allow));cmd+=['--allow',str(root/'allow.json')]
  run=subprocess.run(cmd,capture_output=True,text=True)
  self.assertIn(run.returncode,(0,1),run.stderr);return json.loads((root/'report.json').read_text())

 def base(self):
  # Floor, perimeter walls, a 3 m deck slab (z -7..-1) reached by a 10 m
  # ramp (slope 0.3) railed along its upper part.
  return [box([-12,-.2,-7],[12,0,12]),box([-12.5,0,-7.5],[12.5,3,-7]),box([-12.5,0,12],[12.5,3,12.5]),box([-12.5,0,-7],[-12,3,12]),box([12,0,-7],[12.5,3,12]),
   box([-12,2.8,-7],[12,3,-1]),ramp(5,7,-1,9,3),box([4.8,0,-1],[5,4,7]),box([7,0,-1],[7.2,4,7])]

 def kinds(self,r):return {(f['kind'],f['id']) for f in r['failures']}

 def test_baseline_passes(self):
  r=self.package(self.base());self.assertEqual(r['status'],'PASS',r['failures'])

 def test_wall_across_route(self):
  r=self.package(self.base()+[box([-.1,0,6],[.1,2.8,12])]);self.assertEqual(r['status'],'FAIL')
  self.assertTrue({('node','b'),('edge','a>b')}&self.kinds(r),r['failures'])

 def test_ramp_too_steep(self):
  # Slope 0.8 (39 deg): over the route limit, under core's 49 deg support.
  s=self.base();s[6]=ramp(5,7,-1,3,3)
  r=self.package(s);self.assertIn(('node','deck'),self.kinds(r),r['failures']);self.assertGreater(r['steepReachable']['area'],5)

 def test_narrow_door(self):
  # A 1.0 m door in a wall across the a>b route: walkable, but under DOOR.
  r=self.package(self.base()+[box([-.1,0,-1],[.1,2.8,10]),box([-.1,0,11],[.1,3,12])])
  self.assertEqual(self.kinds(r),{('chokepoint','a>b')},r['failures'])

 def test_hop_up_block_needs_declaring(self):
  r=self.package(self.base()+[box([-8,0,0],[-5,1,3])]);hop=[f for f in r['failures'] if f['kind']=='island']
  self.assertEqual(len(hop),1,r['failures']);self.assertEqual(hop[0]['reach'],'jump-up')
  r=self.package(self.base()+[box([-8,0,0],[-5,1,3])],allow={'accept':[{'ids':['island:'+hop[0]['id']],'reason':'test'}]})
  self.assertEqual(r['status'],'PASS',r['failures'])

if __name__=='__main__':unittest.main()
