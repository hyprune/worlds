# SPDX-License-Identifier: MIT
"""Small offline glTF reader for this author's separate-buffer triangle export."""
import json
from pathlib import Path
import numpy as np
DT={5120:'i1',5121:'u1',5122:'<i2',5123:'<u2',5125:'<u4',5126:'<f4'}
DIMS={'SCALAR':1,'VEC2':2,'VEC3':3,'VEC4':4,'MAT4':16}
class Scene:
 def __init__(self,root):
  self.root=Path(root);self.manifest=json.loads((self.root/'world.json').read_text());self.doc=json.loads((self.root/self.manifest['scene']).read_text());self.buffers=[(self.root/b['uri']).read_bytes() for b in self.doc['buffers']]
  self.parents={c:i for i,n in enumerate(self.doc['nodes']) for c in n.get('children',[])}
 def accessor(self,index):
  a=self.doc['accessors'][index];v=self.doc['bufferViews'][a['bufferView']];dim=DIMS[a['type']];dt=np.dtype(DT[a['componentType']]);off=v.get('byteOffset',0)+a.get('byteOffset',0);stride=v.get('byteStride',dim*dt.itemsize)
  return np.ndarray((a['count'],dim),dtype=dt,buffer=self.buffers[v['buffer']],offset=off,strides=(stride,dt.itemsize)).copy()
 def transform(self,i):
  n=self.doc['nodes'][i]
  if 'matrix' in n:m=np.array(n['matrix']).reshape(4,4).T
  else:
   x,y,z,w=n.get('rotation',[0,0,0,1]);m=np.eye(4)
   m[:3,:3]=np.array([[1-2*(y*y+z*z),2*(x*y-z*w),2*(x*z+y*w)],[2*(x*y+z*w),1-2*(x*x+z*z),2*(y*z-x*w)],[2*(x*z-y*w),2*(y*z+x*w),1-2*(x*x+y*y)]])@np.diag(n.get('scale',[1,1,1]));m[:3,3]=n.get('translation',[0,0,0])
  return self.transform(self.parents[i])@m if i in self.parents else m
 def visible(self):
  result=set()
  def walk(i):
   result.add(i)
   for c in self.doc['nodes'][i].get('children',[]):walk(c)
  for i in self.doc['scenes'][self.doc.get('scene',0)]['nodes']:walk(i)
  return result
 def primitives(self,visible=True):
  visible_nodes=self.visible() if visible else set(range(len(self.doc['nodes'])))
  for i,n in enumerate(self.doc['nodes']):
   if i not in visible_nodes or 'mesh' not in n:continue
   transform=self.transform(i)
   for p in self.doc['meshes'][n['mesh']]['primitives']:
    a=self.accessor(p['attributes']['POSITION']);a=(np.column_stack([a,np.ones(len(a))])@transform.T)[:,:3];idx=self.accessor(p['indices']).reshape(-1) if 'indices' in p else np.arange(len(a))
    yield i,n.get('name',str(i)),p,a,idx.reshape(-1,3)

COMPRESSED={'EXT_meshopt_compression','KHR_mesh_quantization'}
def load(root):
 """Scene of a source package (world format <= 0.6) or of a 0.7 release
 package: meshopt/quantised geometry is decoded by tools/gltf/decode.mjs
 (`make gltf-deps`) into a temporary copy, removed at exit. `scene.package`
 is always the package directory."""
 import atexit,shutil,subprocess,sys,tempfile
 root=Path(root);m=json.loads((root/'world.json').read_text());doc=json.loads((root/m['scene']).read_text())
 if not COMPRESSED&set(doc.get('extensionsUsed',[])):
  s=Scene(root);s.package=root;return s
 helper=Path(__file__).parent/'gltf'/'decode.mjs'
 if not (helper.parent/'node_modules'/'meshoptimizer').exists():sys.exit('glTF-Transform missing: run `make gltf-deps` (npm ci in tools/gltf)')
 tmp=Path(tempfile.mkdtemp(prefix='hyprune-decode-'));atexit.register(shutil.rmtree,tmp,True)
 out=subprocess.run(['node',str(helper),str(root),str(tmp)],capture_output=True,text=True)
 if out.returncode:sys.exit('decode.mjs failed: '+out.stderr[-2000:])
 (tmp/'world.json').write_text(json.dumps(m|{'scene':'scene.gltf'}))
 s=Scene(tmp);s.package=root;return s
