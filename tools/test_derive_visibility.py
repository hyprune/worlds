#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Derived visibility on a synthetic two-room package: a solid wall hides room B
from deep inside room A; a doorway makes it visible again. Runs the kernel
locally with small sample counts (seconds, CPU only)."""
import json,subprocess,sys,tempfile,unittest
from pathlib import Path
import numpy as np
TOOL=Path(__file__).with_name('derive-visibility.py')

def box(lo,hi):
 x0,y0,z0=lo;x1,y1,z1=hi
 v=[[x0,y0,z0],[x1,y0,z0],[x1,y1,z0],[x0,y1,z0],[x0,y0,z1],[x1,y0,z1],[x1,y1,z1],[x0,y1,z1]]
 f=[[0,2,1],[0,3,2],[4,5,6],[4,6,7],[0,1,5],[0,5,4],[3,7,6],[3,6,2],[0,4,7],[0,7,3],[1,2,6],[1,6,5]]   # outward
 return np.array(v,float),np.array(f)

def quad(x0,x1,z0,z1):
 return np.array([[x0,0,z0],[x1,0,z0],[x1,0,z1],[x0,0,z1]],float),np.array([[0,2,1],[0,3,2]])   # faces +y

def merge(parts):
 v=[];f=[];n=0
 for pv,pf in parts:v.append(pv);f.append(pf+n);n+=len(pv)
 return np.concatenate(v),np.concatenate(f)

def package(root,door):
 wall=[box([-.2,0,0],[.2,4,4]),box([-.2,0,6],[.2,4,10]),box([-.2,2.5,4],[.2,4,6])] if door else [box([-.2,0,0],[.2,4,10])]
 meshes={'Visual-a':merge([quad(-10,0,0,10),*wall]),'Visual-b':merge([quad(0,10,0,10),box([6,0,4],[7,3,6])])}
 meshes['Collision']=merge([quad(-10,0,0,10),quad(0,10,0,10),*wall,box([6,0,4],[7,3,6])])
 blob=b'';views=[];acc=[];gl_meshes=[];nodes=[]
 for i,(name,(v,f)) in enumerate(meshes.items()):
  for data,kind,comp,count,extra in [(v.astype('<f4').tobytes(),'VEC3',5126,len(v),{'min':v.min(0).tolist(),'max':v.max(0).tolist()}),(f.astype('<u4').tobytes(),'SCALAR',5125,f.size,{})]:
   views.append({'buffer':0,'byteOffset':len(blob),'byteLength':len(data)});acc.append({'bufferView':len(views)-1,'componentType':comp,'count':count,'type':kind,**extra});blob+=data
  gl_meshes.append({'primitives':[{'attributes':{'POSITION':len(acc)-2},'indices':len(acc)-1,'material':0}]});nodes.append({'name':name,'mesh':i})
 (root/'scene.bin').write_bytes(blob)
 (root/'scene.gltf').write_text(json.dumps({'asset':{'version':'2.0'},'scene':0,'scenes':[{'nodes':[0,1,2]}],'nodes':nodes,'meshes':gl_meshes,
  'materials':[{'name':'m'}],'buffers':[{'uri':'scene.bin','byteLength':len(blob)}],'bufferViews':views,'accessors':acc}))
 (root/'world.json').write_text(json.dumps({'formatVersion':'0.5','id':'org.hyprune.rooms','version':'0.1.0','name':'Rooms','license':'CC0-1.0','scene':'scene.gltf',
  'defaultSpawn':'a','spawns':[{'id':'a','pose':{'position':[-8,0,5],'rotation':[0,0,0,1]}}],'attribution':[{'path':'.','author':'tests','license':'CC0-1.0'}],
  'collision':[{'node':2,'shape':'mesh','layer':'static'}]}))

def visible_units(spec,eye):
 """Core semantics: an owner area's nodes draw when the eye is in the area or in a listed source; outside every area all draw."""
 inside=lambda a:all(a['bounds']['min'][d]<=eye[d]<=a['bounds']['max'][d] for d in range(3))
 cur={a['id'] for a in spec['areas'] if inside(a)}
 hidden=set()
 if cur:
  for a in spec['areas']:
   if not (a['id'] in cur or set(a['visibleFrom'])&cur):hidden|=set(a['nodeNames'])
 return {'Visual-a','Visual-b'}-hidden

class DerivedVisibility(unittest.TestCase):
 def derive(self,door):
  with tempfile.TemporaryDirectory() as tmp:
   root=Path(tmp)/'pkg';root.mkdir();package(root,door);out=Path(tmp)/'out'
   subprocess.run([sys.executable,str(TOOL),str(root),'--output',str(out),'--local','--targets','256','--forward','1024'],check=True,capture_output=True,text=True)
   return json.loads((out/'visibility.generated.json').read_text()),json.loads((out/'report.json').read_text())
 def test_wall_hides_far_room_doorway_reveals_it(self):
  spec,report=self.derive(door=False)
  self.assertGreater(report['cells'],8)
  self.assertEqual(visible_units(spec,[-9.5,1.7,5]),{"Visual-a"})        # deep in A (beyond the conservative band), solid wall
  self.assertIn('Visual-b',visible_units(spec,[-1,1.7,5]))               # beside the wall: near rule
  self.assertEqual(visible_units(spec,[8,1.7,5]),{'Visual-a','Visual-b'}) # the wall itself is unit A
  self.assertEqual(visible_units(spec,[-8,40,5]),{'Visual-a','Visual-b'}) # flying above all cells
  self.assertEqual(report['eyesWhereGeneratedHidesASampledVisibleUnit'],0)
  spec,report=self.derive(door=True)
  self.assertIn("Visual-b",visible_units(spec,[-9.5,1.7,5]))             # same spot, looking through the doorway
  self.assertEqual(report['eyesWhereGeneratedHidesASampledVisibleUnit'],0)

if __name__=='__main__':unittest.main()
