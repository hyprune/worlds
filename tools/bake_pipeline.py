# SPDX-License-Identifier: MIT
"""Reusable remote-only UV/bake/export pipeline extracted from the test world."""
import os,json,math,time,subprocess
from pathlib import Path
if os.environ.get("HYPRUNE_REMOTE_BLENDER")!="1": raise SystemExit("Remote bake host only")
import bpy,bmesh,numpy as np
from mathutils import Vector,Matrix
RESOLUTIONS={};MARGINS={};GROUPS={};BLOCKS=[];COLL=[];MATS={};LIGHTMAPS={};TILE_METERS={};BEVEL_SEGMENTS=2
def log(s): print("LUMEN | "+s,flush=True)

def select(obs):
 bpy.ops.object.select_all(action='DESELECT')
 for o in obs:o.select_set(True)
 bpy.context.view_layer.objects.active=obs[0]


def add(o,name,mat,group,collision=False):
 o.name=name;o.data.materials.append(MATS[mat]);GROUPS.setdefault(group,[]).append(o)
 # UV0 is tiled in physical world space, independent of UV1 packing.
 if not o.data.uv_layers:o.data.uv_layers.new(name='UV0')
 uv=o.data.uv_layers[0];uv.name='UV0';o.data.calc_loop_triangles()
 for p in o.data.polygons:
  axis=max(range(3),key=lambda a:abs(p.normal[a]));axes=[a for a in range(3) if a!=axis]
  for li in p.loop_indices:
   v=o.matrix_world@o.data.vertices[o.data.loops[li].vertex_index].co;uv.data[li].uv=(v[axes[0]]/TILE_METERS.get(mat,1),v[axes[1]]/TILE_METERS.get(mat,1))
   if mat=='trim':
    coords=[(o.matrix_world@o.data.vertices[o.data.loops[j].vertex_index].co)[axes[1]] for j in p.loop_indices];span=max(coords)-min(coords)
    uv.data[li].uv=(v[axes[0]],.2421875-(v[axes[1]]-min(coords))/max(span,1e-6)*.109375)
 if collision:
  vs=[o.matrix_world@Vector(v) for v in o.bound_box];lo=[min(v[i] for v in vs) for i in range(3)];hi=[max(v[i] for v in vs) for i in range(3)]
  COLL.append((name,lo,hi))
  if hi[2]>.08 and lo[2]<1.8:BLOCKS.append((lo,hi))
 return o

def box(name,pos,size,mat='stone',group='hall',bevel=.035,collision=False):
 me=bpy.data.meshes.new(name);bm=bmesh.new();bmesh.ops.create_cube(bm,size=1)
 for v in bm.verts:v.co.x*=size[0];v.co.y*=size[1];v.co.z*=size[2]
 if bevel:bmesh.ops.bevel(bm,geom=list(bm.edges),offset=min(bevel,min(size)*.45),segments=BEVEL_SEGMENTS,affect='EDGES')
 bm.normal_update();bm.to_mesh(me);bm.free();me.update();o=bpy.data.objects.new(name,me);bpy.context.collection.objects.link(o);o.matrix_world=Matrix.Translation(Vector(pos))
 return add(o,name,mat,group,collision)

def cylinder(name,pos,r,depth,mat='metal',group='hall',vertices=32,collision=False):
 # Direct mesh construction avoids a full dependency-graph update for every pipe.
 me=bpy.data.meshes.new(name);bm=bmesh.new();bmesh.ops.create_cone(bm,cap_ends=True,cap_tris=False,segments=vertices,radius1=r,radius2=r,depth=depth)
 bm.normal_update();bm.to_mesh(me);bm.free();me.update();o=bpy.data.objects.new(name,me);bpy.context.collection.objects.link(o);o.matrix_world=Matrix.Translation(Vector(pos))
 return add(o,name,mat,group,collision)


def area(name,pos,target,power,color,size):
 d=bpy.data.lights.new(name,'AREA');d.energy=power;d.color=color;d.shape='DISK';d.size=size
 d.use_shadow=not name.startswith('Dock pool')
 o=bpy.data.objects.new(name,d);bpy.context.collection.objects.link(o);o.location=pos;o.rotation_euler=(Vector(target)-o.location).to_track_quat('-Z','Y').to_euler()


def gpu():
 prefs=bpy.context.preferences.addons['cycles'].preferences;prefs.compute_device_type='OPTIX';prefs.get_devices()
 for device in prefs.devices:device.use=device.type=='OPTIX'
 bpy.context.scene.cycles.device='GPU'

def camera(pos,target,lens=40):
 c=bpy.context.scene.camera;c.location=pos;c.rotation_euler=(Vector(target)-c.location).to_track_quat('-Z','Y').to_euler();c.data.lens=lens

def join_groups():
 for name,obs in list(GROUPS.items()):
  select(obs);bpy.ops.object.join();o=bpy.context.object;o.name='Visual-'+name
  bm=bmesh.new();bm.from_mesh(o.data);bmesh.ops.triangulate(bm,faces=list(bm.faces));bm.to_mesh(o.data);bm.free();o.data.update()
  # Each group owns its material bindings and its unique atlas.
  for i,m in enumerate(o.data.materials):o.data.materials[i]=m.copy();o.data.materials[i].name=name+'--'+m.name
  if name in {'vista','atmosphere'}:
   GROUPS[name]=[o];continue
  select([o]);uv=o.data.uv_layers.new(name='UV1');o.data.uv_layers.active=uv;uv.active_render=True
  bpy.ops.object.mode_set(mode='EDIT');bpy.ops.mesh.select_all(action='SELECT');bpy.ops.uv.smart_project(angle_limit=math.radians(30),island_margin=.003,margin_method='FRACTION',scale_to_bounds=True);bpy.ops.uv.pack_islands(rotate=True,scale=True,margin_method='FRACTION',margin=MARGINS.get(name,8)/(RESOLUTIONS.get(name,2048)));bpy.ops.object.mode_set(mode='OBJECT')
  uv=o.data.uv_layers['UV1'];log(f'UV1 {name}: {min(c for d in uv.data for c in d.uv):.5f} .. {max(c for d in uv.data for c in d.uv):.5f}');assert all(-1e-6<=c<=1.000001 for d in uv.data for c in d.uv),name
  o.data.uv_layers['UV0'].active_render=True
  GROUPS[name]=[o]

def save_srgb(name,a):
 s=bpy.context.scene;old=(s.view_settings.view_transform,s.view_settings.look,s.view_settings.exposure,s.view_settings.gamma);s.view_settings.view_transform='Standard';s.view_settings.look='None';s.view_settings.exposure=0
 im=bpy.data.images.new(name,width=a.shape[1],height=a.shape[0],alpha=False,float_buffer=True);im.pixels.foreach_set(a.ravel())
 s.render.image_settings.color_mode='RGB';s.render.image_settings.color_depth='8';im.save_render(str(OUT/'textures'/f'{name}.png'),scene=s)
 bpy.data.images.remove(im);s.view_settings.view_transform,s.view_settings.look,s.view_settings.exposure,s.view_settings.gamma=old

def bake(samples):
 s=bpy.context.scene;s.cycles.samples=samples;s.render.bake.margin=8;s.render.bake.use_clear=True
 rows=[]
 for name,obs in GROUPS.items():
  if name in {'vista','atmosphere'}:continue
  t=time.time();o=obs[0];n=RESOLUTIONS.get(name,2048);margin=MARGINS.get(name,8);s.render.bake.margin=margin
  im=bpy.data.images.new('Irradiance '+name,width=n,height=n,alpha=False,float_buffer=True)
  for m in o.data.materials:
   node=m.node_tree.nodes.new('ShaderNodeTexImage');node.name='Lighting bake target';node.image=im;m.node_tree.nodes.active=node
  select([o]);bpy.ops.object.bake(type='DIFFUSE',pass_filter={'DIRECT','INDIRECT'},uv_layer='UV1')
  a=np.empty(n*n*4,dtype=np.float32);im.pixels.foreach_get(a);a=a.reshape(n,n,4)
  # OIDN RTLightmap is lighting-only, HDR-aware; normalize without clipping.
  src=ART/'raw.pfm';dst=ART/'denoised.pfm'
  with src.open('wb') as f:f.write(f'PF\n{n} {n}\n-1.0\n'.encode());f.write(np.ascontiguousarray(a[:,:,:3],dtype='<f4').tobytes())
  subprocess.run(['oidnDenoise','-v','0','-f','RTLightmap','--hdr',str(src),'-o',str(dst),'--threads','12'],check=True)
  with dst.open('rb') as f:
   assert f.readline().strip()==b'PF';assert f.readline().strip()==f'{n} {n}'.encode();assert float(f.readline())<0;a[:,:,:3]=np.frombuffer(f.read(),dtype='<f4').reshape(n,n,3)
  src.unlink();dst.unlink();peak=float(np.max(a[:,:,:3]));assert peak>.1,(name,'empty irradiance bake',peak);intensity=max(1,math.ceil(peak*10)/10)
  a[:,:,:3]=np.clip(a[:,:,:3]/intensity,0,1);a[:,:,3]=1
  save_srgb('lightmap-'+name,a);LIGHTMAPS[name]=intensity
  for m in o.data.materials:m.node_tree.nodes.remove(m.node_tree.nodes['Lighting bake target'])
  bpy.data.images.remove(im);rows.append({'group':name,'resolution':n,'peakLinear':peak,'intensity':intensity,'seconds':round(time.time()-t,2),'samples':samples,'marginPixels':margin,'islandSeparationPixels':margin,'supportedMipLevels':0 if name=='foliage' else 2})
  log('Baked '+name);(ART/'bake-report.json').write_text(json.dumps(rows,indent=2)+'\n')



def export(cols,nav):
 obs=[o for group in GROUPS.values() for o in group]+cols+[nav];select(obs)
 bpy.ops.export_scene.gltf(filepath=str(OUT/'scene.gltf'),export_format='GLTF_SEPARATE',use_selection=True,export_yup=True,export_apply=True,export_tangents=True,export_animations=False,export_cameras=False,export_lights=False,export_extras=False,export_materials='EXPORT',export_image_format='AUTO',export_texture_dir='textures')
 path=OUT/'scene.gltf';g=json.loads(path.read_text());nodes={n.get('name'):i for i,n in enumerate(g['nodes'])};g['scenes'][g.get('scene',0)]['nodes']=[i for i in g['scenes'][g.get('scene',0)]['nodes'] if not g['nodes'][i].get('name','').startswith(('Collision','Navigation','Visual-atmosphere'))]
 # Spatial material copies must share image/sampler resources. Core budgets
 # glTF texture objects, so exporter duplicates would exceed 512 MiB.
 samplers=[];sm={}
 for i,sampler in enumerate(g.get('samplers',[])):
  key=json.dumps(sampler,sort_keys=True)
  if key not in [json.dumps(s,sort_keys=True) for s in samplers]:samplers.append(sampler)
  sm[i]=next(j for j,s in enumerate(samplers) if s==sampler)
 g['samplers']=samplers;textures=[];tm={}
 for i,t in enumerate(g.get('textures',[])):
  if 'sampler' in t:t['sampler']=sm[t['sampler']]
  if t not in textures:textures.append(t)
  tm[i]=textures.index(t)
 g['textures']=textures
 def remap(value):
  if isinstance(value,dict):
   for key,child in value.items():
    if key.endswith('Texture') and isinstance(child,dict) and 'index' in child:child['index']=tm[child['index']]
    else:remap(child)
  elif isinstance(value,list):
   for child in value:remap(child)
 for m in g['materials']:remap(m)
 # Blender 5 exports an emission-only shader as black PBR + emission.
 # Convert intentional skyline art to portable standard unlit base color.
 for m in g['materials']:
  if not m.get('name','').startswith('vista--'):continue
  color=m.pop('emissiveFactor',None)
  if color is None or not any(color):color=m.get('pbrMetallicRoughness',{}).get('baseColorFactor',[1,1,1,1])[:3]
  gain=m.get('extensions',{}).pop('KHR_materials_emissive_strength',{}).get('emissiveStrength',1)
  base_texture=m.get('pbrMetallicRoughness',{}).get('baseColorTexture')
  m['pbrMetallicRoughness']={'baseColorFactor':[min(1,c*gain) for c in color]+[1],'metallicFactor':0,'roughnessFactor':1}
  if 'emissiveTexture' in m:m['pbrMetallicRoughness']['baseColorTexture']=m.pop('emissiveTexture')
  elif base_texture:m['pbrMetallicRoughness']['baseColorTexture']=base_texture
  m.setdefault('extensions',{})['KHR_materials_unlit']={}
  if m.get('name','').startswith('vista--steam-card'):m['alphaMode']='BLEND';m['doubleSided']=True
 if 'KHR_materials_unlit' not in g.setdefault('extensionsUsed',[]):g['extensionsUsed'].append('KHR_materials_unlit')
 # At isolated degenerate UV caps MikkTSpace may output zero tangents.
 # Supply a deterministic unit orthogonal fallback, preserving other tangents.
 buffers={i:bytearray((OUT/b['uri']).read_bytes()) for i,b in enumerate(g['buffers'])};repaired=0
 def acc(index):
  a=g['accessors'][index];v=g['bufferViews'][a['bufferView']];dim={'VEC3':3,'VEC4':4}[a['type']]
  return np.ndarray((a['count'],dim),dtype='<f4',buffer=buffers[v['buffer']],offset=v.get('byteOffset',0)+a.get('byteOffset',0),strides=(v.get('byteStride',dim*4),4))
 for me in g['meshes']:
  for primitive in me['primitives']:
   at=primitive['attributes']
   if 'TANGENT' not in at:continue
   tang=acc(at['TANGENT']);norm=acc(at['NORMAL']);bad=np.linalg.norm(tang[:,:3],axis=1)<1e-6
   if np.any(bad):
    nn=norm[bad];ref=np.eye(3,dtype=np.float32)[np.argmin(np.abs(nn),axis=1)];fallback=np.cross(ref,nn);fallback/=np.linalg.norm(fallback,axis=1)[:,None];tang[bad,:3]=fallback;tang[bad,3]=1;repaired+=int(np.sum(bad))
 for i,data in buffers.items():(OUT/g['buffers'][i]['uri']).write_bytes(data)
 (ART/'tangent-report.json').write_text(json.dumps({'degenerateCapFallbackVertices':repaired,'method':'unit vector orthogonal to geometric normal; unaffected MikkTSpace tangents retained'},indent=2)+'\n')
 # Lighting is manifest metadata. No fake Khronos extension or occlusion trick.
 lm=[];light_sampler=len(g['samplers']);g['samplers'].append({'magFilter':9729,'minFilter':9729,'wrapS':33071,'wrapT':33071})
 for name,intensity in LIGHTMAPS.items():
  ii=len(g['images']);g['images'].append({'uri':'textures/lightmap-'+name+'.png'})
  ti=len(g['textures']);g['textures'].append({'source':ii,'sampler':light_sampler})
  for mi,m in enumerate(g['materials']):
   if m.get('name','').startswith(name+'--'):lm.append({'material':mi,'texture':ti,'texCoord':1,'encoding':'srgb','intensity':intensity})
 # Required base contract uses only core glTF PBR. Our metallics are deliberately matte.
 path.write_text(json.dumps(g,indent=2)+'\n')
 return g,lm,nodes
