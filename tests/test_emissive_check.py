# SPDX-License-Identifier: MIT
"""A 2cm lens missed by the legacy 10cm grid must still reject z-fighting."""
import importlib.util,json,sys,tempfile,unittest
from pathlib import Path
import numpy as np
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'tools'))
spec=importlib.util.spec_from_file_location('emissive',ROOT/'tools/check-emissive.py');audit=importlib.util.module_from_spec(spec);spec.loader.exec_module(audit)
class NarrowLens(unittest.TestCase):
 def scene(self,axis,gap):
  temp=tempfile.TemporaryDirectory();self.addCleanup(temp.cleanup);root=Path(temp.name)
  plane=np.array([[0,0,0],[.02,0,0],[0,1,0]],dtype='<f4');other=plane.copy();other[:,2]+=gap
  points=np.concatenate([plane,other]);points=points[:,np.roll(np.arange(3),axis)].copy();indices=np.arange(6,dtype='<u2');data=points.tobytes()+indices.tobytes()
  (root/'scene.bin').write_bytes(data)
  accessors=[{'bufferView':0,'componentType':5126,'count':6,'type':'VEC3'},{'bufferView':1,'componentType':5123,'count':3,'type':'SCALAR'},{'bufferView':1,'byteOffset':6,'componentType':5123,'count':3,'type':'SCALAR'}]
  doc={'asset':{'version':'2.0'},'buffers':[{'uri':'scene.bin','byteLength':len(data)}],'bufferViews':[{'buffer':0,'byteLength':points.nbytes},{'buffer':0,'byteOffset':points.nbytes,'byteLength':indices.nbytes}],'accessors':accessors,'materials':[{'name':'backplate'},{'name':'narrow lens','emissiveFactor':[1,.4,.1]}],'meshes':[{'primitives':[{'attributes':{'POSITION':0},'indices':1,'material':0},{'attributes':{'POSITION':0},'indices':2,'material':1}]}],'nodes':[{'mesh':0,'name':'Fixture'}],'scenes':[{'nodes':[0]}]}
  (root/'scene.gltf').write_text(json.dumps(doc));(root/'world.json').write_text(json.dumps({'scene':'scene.gltf'}));return root
 def test_small_overlap_all_axes(self):
  for axis in range(3):
   with self.subTest(axis=axis):self.assertEqual(audit.check(self.scene(axis,.002))['status'],'FAIL')
 def test_separated_lens_all_axes(self):
  for axis in range(3):
   with self.subTest(axis=axis):self.assertEqual(audit.check(self.scene(axis,.008))['status'],'PASS')
if __name__=='__main__':unittest.main()
