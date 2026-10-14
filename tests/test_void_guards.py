# SPDX-License-Identifier: MIT
"""tools/derive-void-guards.py guards floor edges with nothing below, only.

A synthetic package (the navmesh test's builder): a 10 x 10 m floor walled on
two sides, with a lower floor 3 m down beyond a third side (a drop) and
nothing beyond the fourth (a void), plus a 2 m slot cut into the floor next to
the void edge's wall. Expected: guards on the void edge only, along the true
floor edge; the walls and the drop get none. The lower floor's own outer
edges are voids too. Needs node and
tools/navmesh/node_modules (npm ci there).
"""
import json,subprocess,sys,tempfile,unittest
from pathlib import Path
import numpy as np
sys.path.insert(0,str(Path(__file__).parent))
from test_navmesh_check import FACES,box
ROOT=Path(__file__).resolve().parents[1]

def package(root,solids):
 pts=np.array([v for s in solids for v in s],'<f4');idx=np.array([FACES for _ in solids],'<u4').reshape(-1)
 (root/'scene.bin').write_bytes(pts.tobytes()+idx.tobytes())
 views=[{'buffer':0,'byteLength':pts.nbytes},{'buffer':0,'byteOffset':pts.nbytes,'byteLength':idx.nbytes}];acc=[];meshes=[];nodes=[]
 for i in range(len(solids)):
  acc+=[{'bufferView':0,'byteOffset':i*96,'componentType':5126,'count':8,'type':'VEC3'},{'bufferView':1,'byteOffset':i*144,'componentType':5125,'count':36,'type':'SCALAR'}]
  meshes.append({'primitives':[{'attributes':{'POSITION':2*i},'indices':2*i+1}]});nodes.append({'mesh':i,'name':f'Collision-{i}'})
 (root/'scene.gltf').write_text(json.dumps({'asset':{'version':'2.0'},'buffers':[{'uri':'scene.bin','byteLength':pts.nbytes+idx.nbytes}],'bufferViews':views,'accessors':acc,'meshes':meshes,'nodes':nodes,'scenes':[{'nodes':list(range(len(nodes)))}]}))
 (root/'world.json').write_text(json.dumps({'id':'test.void','version':'0','scene':'scene.gltf','defaultSpawn':'a','spawns':[{'id':'a','pose':{'position':[0,0,0],'rotation':[0,0,0,1]}}],
  'anchors':[],'collision':[{'node':i,'shape':'mesh','layer':'static'} for i in range(len(nodes))]}))

class VoidGuards(unittest.TestCase):
 def test_void_edge_only(self):
  with tempfile.TemporaryDirectory() as tmp:
   root=Path(tmp)
   package(root,[box([-5,-.2,-5],[5,0,5]),                      # floor
    box([-5.5,0,-5.5],[-5,3,5]),box([-5.5,0,-5.5],[5,3,-5]),       # walls west, north
    box([5,-3.2,-5],[12,-3,5])])                                   # lower floor east (a drop)
   out=root/'guards.json'
   run=subprocess.run([sys.executable,str(ROOT/'tools/derive-void-guards.py'),str(root),'--output',str(out)],capture_output=True,text=True)
   self.assertEqual(run.returncode,0,run.stderr)
   g=json.loads(out.read_text())['guards']
   upper=[x for x in g if abs(x['floor'])<.05];lower=[x for x in g if abs(x['floor']+3)<.05]
   self.assertEqual(len(upper)+len(lower),len(g),g)
   # Upper floor: the south edge (z 5) only, just past the floor, corner to corner.
   self.assertTrue(upper,'the south edge over the void is not guarded')
   for x in upper:
    self.assertAlmostEqual(x['a'][2],5.07,delta=.1);self.assertAlmostEqual(x['b'][2],5.07,delta=.1);self.assertEqual(x['outward'],[0,0,1])
   span=sorted(v for x in upper for v in (x['a'][0],x['b'][0]))
   self.assertLess(span[0],-4.2);self.assertGreater(span[-1],4.2)
   # Lower floor: all four sides end over the void.
   self.assertEqual({tuple(x['outward']) for x in lower},{(1,0,0),(-1,0,0),(0,0,1),(0,0,-1)},lower)

if __name__=='__main__':unittest.main()
