# SPDX-License-Identifier: MIT
"""Original procedural Switchyard. Run ONLY via tools/remote-blender.sh.
Blender authoring uses Z up; exporter converts to glTF +Y up: (x,z,-y).
No imported models or fonts. Original imagegen texture masters are recorded in materials/.
"""
import argparse, hashlib, json, math, os, shutil, socket, subprocess, sys, time
from pathlib import Path
import bpy, bmesh
import numpy as np
from mathutils import Vector, Matrix

ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'dist/com.hyprune.switchyard'; ART=ROOT/'artifacts/switchyard'
SPEC=json.loads((Path(__file__).parent/'world.spec.json').read_text())
COLORS={'cyan':(.08,.58,.61),'amber':(.88,.53,.17),'coral':(.73,.25,.17)}
GROUPS={}; BLOCKS=[]; COLL=[]; MATS={}; LIGHTMAPS={}
# A small original pixel alphabet, authored here as geometry, not a font file.
GLYPHS={
'A':['01110','10001','10001','11111','10001','10001','10001'],
'B':['11110','10001','10001','11110','10001','10001','11110'],
'C':['01111','10000','10000','10000','10000','10000','01111'],
'D':['11110','10001','10001','10001','10001','10001','11110'],
'E':['11111','10000','10000','11110','10000','10000','11111'],
'F':['11111','10000','10000','11110','10000','10000','10000'],
'G':['01111','10000','10000','10111','10001','10001','01111'],
'H':['10001','10001','10001','11111','10001','10001','10001'],
'I':['11111','00100','00100','00100','00100','00100','11111'],
'J':['00111','00010','00010','00010','10010','10010','01100'],
'K':['10001','10010','10100','11000','10100','10010','10001'],
'L':['10000','10000','10000','10000','10000','10000','11111'],
'M':['10001','11011','10101','10101','10001','10001','10001'],
'N':['10001','11001','10101','10011','10001','10001','10001'],
'O':['01110','10001','10001','10001','10001','10001','01110'],
'P':['11110','10001','10001','11110','10000','10000','10000'],
'Q':['01110','10001','10001','10001','10101','10010','01101'],
'R':['11110','10001','10001','11110','10100','10010','10001'],
'S':['01111','10000','10000','01110','00001','00001','11110'],
'T':['11111','00100','00100','00100','00100','00100','00100'],
'U':['10001','10001','10001','10001','10001','10001','01110'],
'V':['10001','10001','10001','10001','10001','01010','00100'],
'W':['10001','10001','10001','10101','10101','10101','01010'],
'X':['10001','10001','01010','00100','01010','10001','10001'],
'Y':['10001','10001','01010','00100','00100','00100','00100'],
'Z':['11111','00001','00010','00100','01000','10000','11111'],
'0':['01110','10001','10011','10101','11001','10001','01110'],
'1':['00100','01100','00100','00100','00100','00100','01110'],
'2':['01110','10001','00001','00010','00100','01000','11111'],
'3':['11110','00001','00001','01110','00001','00001','11110'],
'4':['00010','00110','01010','10010','11111','00010','00010'],
'5':['11111','10000','10000','11110','00001','00001','11110'],
'6':['01110','10000','10000','11110','10001','10001','01110'],
'7':['11111','00001','00010','00100','01000','01000','01000'],
'8':['01110','10001','10001','01110','10001','10001','01110'],
'9':['01110','10001','10001','01111','00001','00001','01110'],
'-':['00000','00000','00000','11111','00000','00000','00000'],
'/':['00001','00001','00010','00100','01000','10000','10000']}

def log(s): print('SWITCHYARD | '+s,flush=True)
def select(obs):
 bpy.ops.object.select_all(action='DESELECT')
 for o in obs:o.select_set(True)
 bpy.context.view_layer.objects.active=obs[0]

def texture(name,color,noise):
 n=256; rng=np.random.default_rng(712)
 a=np.ones((n,n,4),np.float32)
 y,x=np.mgrid[:n,:n]
 grain=rng.normal(0,noise,(n,n))+noise*.3*np.sin(x*.13)*np.cos(y*.17)
 for i in range(3):a[:,:,i]=np.clip(color[i]+grain,0,1)
 im=bpy.data.images.new(name,width=n,height=n,alpha=False,float_buffer=True)
 im.pixels.foreach_set(a.ravel()); im.filepath_raw=str(OUT/'textures'/f'{name}.png');im.file_format='PNG';im.save()
 return im

ASSET_MAP={'stone':'stone','ivory':'stone','metal':'metal','wood':'wood','rubber':'rubber','brass':'brass','cloth':'cloth','glass':'glass','panel':'metal','diffuser':'panel'}
TILE_METERS={'stone':2,'ivory':2,'metal':1,'wood':1,'rubber':1,'brass':1,'cloth':1,'glass':2,'panel':1,'diffuser':1}
UNLIT={'sky','city','city-near','distant','city-light','city-cool','moon'}
def material(name,color,noise=.006,metal=0,emit=0,rough=.65,alpha=1):
 m=bpy.data.materials.new(name);m.use_nodes=True;p=m.node_tree.nodes.get('Principled BSDF');p.inputs['Roughness'].default_value=rough;p.inputs['Metallic'].default_value=metal
 tree=m.node_tree;uv=tree.nodes.new('ShaderNodeUVMap');uv.uv_map='UV0'
 asset=ASSET_MAP.get(name)
 if asset:
  path=Path(__file__).parent/'materials/tiles'/f'{asset}-albedo.png';assert path.exists(),path
  im=bpy.data.images.load(str(path),check_existing=True)
 elif name=='trim':im=bpy.data.images.load(str(Path(__file__).parent/'materials/tiles/transit-trim-albedo.png'),check_existing=True)
 else:im=texture('albedo-'+name,color,noise)
 n=tree.nodes.new('ShaderNodeTexImage');n.image=im;tree.links.new(uv.outputs['UV'],n.inputs['Vector']);tree.links.new(n.outputs['Color'],p.inputs['Base Color'])
 if asset:
  norm=tree.nodes.new('ShaderNodeTexImage');norm.image=bpy.data.images.load(str(Path(__file__).parent/'materials/tiles'/f'{asset}-normal.png'),check_existing=True);norm.image.colorspace_settings.name='Non-Color';tree.links.new(uv.outputs['UV'],norm.inputs['Vector']);nm=tree.nodes.new('ShaderNodeNormalMap');nm.inputs['Strength'].default_value=.40;tree.links.new(norm.outputs['Color'],nm.inputs['Color']);tree.links.new(nm.outputs['Normal'],p.inputs['Normal'])
  orm=tree.nodes.new('ShaderNodeTexImage');orm.image=bpy.data.images.load(str(Path(__file__).parent/'materials/tiles'/f'{asset}-orm.png'),check_existing=True);orm.image.colorspace_settings.name='Non-Color';tree.links.new(uv.outputs['UV'],orm.inputs['Vector']);sep=tree.nodes.new('ShaderNodeSeparateColor');sep.mode='RGB';tree.links.new(orm.outputs['Color'],sep.inputs['Color']);tree.links.new(sep.outputs['Green'],p.inputs['Roughness']);tree.links.new(sep.outputs['Blue'],p.inputs['Metallic'])
 if name=='panel':p.inputs['Base Color'].default_value=(.005,.012,.017,1);tree.links.remove(p.inputs['Base Color'].links[0])
 if emit:p.inputs['Emission Color'].default_value=(*color,1);p.inputs['Emission Strength'].default_value=emit
 if name=='diffuser':tree.links.new(n.outputs['Color'],p.inputs['Emission Color']);p.inputs['Emission Strength'].default_value=1.5
 if alpha<1:
  p.inputs['Alpha'].default_value=alpha
  if hasattr(m,'surface_render_method'):m.surface_render_method='DITHERED'
 if name in UNLIT:
  output=tree.nodes.get('Material Output');em=tree.nodes.new('ShaderNodeEmission');em.inputs['Color'].default_value=(*color,1);em.inputs['Strength'].default_value=emit or 1;tree.links.new(em.outputs[0],output.inputs['Surface'])
  if name=='sky':tree.links.new(n.outputs['Color'],em.inputs['Color'])
 MATS[name]=m;return m

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
    uv.data[li].uv=(v[axes[0]],.8671875-(v[axes[1]]-min(coords))/max(span,1e-6)*.109375)
 if collision:
  vs=[o.matrix_world@Vector(v) for v in o.bound_box];lo=[min(v[i] for v in vs) for i in range(3)];hi=[max(v[i] for v in vs) for i in range(3)]
  COLL.append((name,lo,hi))
  if hi[2]>.08 and lo[2]<1.8:BLOCKS.append((lo,hi))
 return o

def box(name,pos,size,mat='stone',group='hall',bevel=.035,collision=False):
 me=bpy.data.meshes.new(name);bm=bmesh.new();bmesh.ops.create_cube(bm,size=1)
 for v in bm.verts:v.co.x*=size[0];v.co.y*=size[1];v.co.z*=size[2]
 if bevel:bmesh.ops.bevel(bm,geom=list(bm.edges),offset=min(bevel,min(size)*.45),segments=2,affect='EDGES')
 bm.normal_update();bm.to_mesh(me);bm.free();me.update();o=bpy.data.objects.new(name,me);bpy.context.collection.objects.link(o);o.matrix_world=Matrix.Translation(Vector(pos))
 return add(o,name,mat,group,collision)

def cylinder(name,pos,r,depth,mat='metal',group='hall',vertices=32,collision=False):
 bpy.ops.mesh.primitive_cylinder_add(vertices=vertices,radius=r,depth=depth,location=pos)
 return add(bpy.context.object,name,mat,group,collision)

def text(word,pos,height,mat='letter',group='hall'):
 pitch=height/7; width=(len(word)*6-1)*pitch;verts=[];faces=[]
 # Original geometric lettering, assembled in one mesh without a font asset.
 for j,char in enumerate(word):
  if char==' ':continue
  for row,bits in enumerate(GLYPHS[char]):
   start=None
   for col,b in enumerate(bits+'0'):
    if b=='1' and start is None:start=col
    if b=='0' and start is not None:
     count=col-start;cx=pos[0]-width/2+(j*6+start+count/2)*pitch;cz=pos[2]+(3-row)*pitch
     sx=count*pitch*.89/2;sz=pitch*.85/2;cy=pos[1];i=len(verts)
     verts.extend([(cx-sx,cy-.006,cz-sz),(cx+sx,cy-.006,cz-sz),(cx+sx,cy+.006,cz-sz),(cx-sx,cy+.006,cz-sz),(cx-sx,cy-.006,cz+sz),(cx+sx,cy-.006,cz+sz),(cx+sx,cy+.006,cz+sz),(cx-sx,cy+.006,cz+sz)])
     faces.extend([tuple(i+k for k in f) for f in [(0,3,2,1),(4,5,6,7),(0,1,5,4),(1,2,6,5),(2,3,7,6),(3,0,4,7)]])
     start=None
 me=bpy.data.meshes.new('Geometric lettering');me.from_pydata(verts,[],faces);me.update();o=bpy.data.objects.new('Sign '+word,me);bpy.context.collection.objects.link(o);add(o,'Sign '+word,mat,group)

def area(name,pos,target,power,color,size):
 d=bpy.data.lights.new(name,'AREA');d.energy=power;d.color=color;d.shape='DISK';d.size=size
 d.use_shadow=not name.startswith('Dock pool')
 o=bpy.data.objects.new(name,d);bpy.context.collection.objects.link(o);o.location=pos;o.rotation_euler=(Vector(target)-o.location).to_track_quat('-Z','Y').to_euler()

def tree(x,y,group):
 box('Planter',(x,y,.35),(2.1,2.1,.7),'stone',group,.12,True)
 cylinder('Earth',(x,y,.72),.85,.08,'soil',group)
 cylinder('Trunk',(x,y,1.9),.14,2.3,'wood',group)
 for dx,dy,z,r in [(-.4,0,3.0,.95),(.5,.25,3.5,1.05),(0,-.2,4.1,.85)]:
  bpy.ops.mesh.primitive_ico_sphere_add(subdivisions=2,radius=r,location=(x+dx,y+dy,z));add(bpy.context.object,'Topiary','leaf',group)

def scene():
 bpy.ops.wm.read_factory_settings(use_empty=True)
 if OUT.exists():shutil.rmtree(OUT)
 OUT.mkdir(parents=True,exist_ok=True);(OUT/'textures').mkdir(exist_ok=True);ART.mkdir(parents=True,exist_ok=True)
 for name,color,rough,metal in [('stone',(.40,.37,.30),.82,0),('ivory',(.65,.58,.41),.7,0),('metal',(.025,.048,.062),.48,.45),('panel',(.004,.010,.016),.25,0),('wood',(.24,.11,.044),.48,0),('rubber',(.028,.033,.036),.91,0),('brass',(.42,.25,.08),.29,.78),('trim',(.42,.25,.08),.29,.78),('cloth',(.15,.23,.13),.9,0),('glass',(.1,.22,.27),.2,0),('leaf',(.07,.21,.11),.62,0),('leaf-dark',(.023,.082,.040),.7,0),('soil',(.022,.014,.009),.95,0),('letter',(.78,.82,.72),.6,0)]:material(name,color,.004,metal,0,rough,.22 if name=='glass' else 1)
 for name,color,strength in [('warm',(1,.49,.13),2.3),('white',(.62,.82,.85),2),('diffuser',(.4,.6,.65),1.5),('city',(.018,.045,.065),.5),('city-near',(.024,.058,.077),.6),('distant',(.066,.105,.125),.7),('city-light',(.70,.36,.10),2),('city-cool',(.08,.44,.56),1.4),('moon',(.73,.76,.58),1),('sky',(.014,.04,.073),1),('haze',(.045,.11,.15),.8)]:material(name,color,0,0,strength,alpha=.055 if name=='haze' else 1)
 for key,color in COLORS.items():material(key,color,.004);material(key+'-glow',color,0,0,3)
 # Original blue-hour sky gradient, without an external panorama or HDRI.
 n=1024;y,x=np.mgrid[:n,:n];a=np.ones((n,n,4),np.float32)
 t=(y/n)[:,:,None];a[:,:,:3]=np.array([.070,.13,.16])[None,None,:]*(1-t)+np.array([.008,.022,.047])[None,None,:]*t
 sky=bpy.data.images.new('Sky gradient',width=n,height=n,alpha=False,float_buffer=True);sky.pixels.foreach_set(a.ravel());sky.filepath_raw=str(OUT/'textures/sky-gradient.png');sky.file_format='PNG';sky.save();node=next(n for n in MATS['sky'].node_tree.nodes if n.type=='TEX_IMAGE');node.image=sky
 sys.path.insert(0,str(Path(__file__).parent));from architecture import construct;construct(sys.modules[__name__])
 s=bpy.context.scene;s.unit_settings.system='METRIC';s.unit_settings.scale_length=1;s.render.engine='CYCLES';s.cycles.samples=64;s.cycles.use_denoising=True;s.cycles.max_bounces=6;s.cycles.diffuse_bounces=4
 prefs=bpy.context.preferences.addons['cycles'].preferences;prefs.compute_device_type='OPTIX';prefs.get_devices()
 for d in prefs.devices:d.use=d.type=='OPTIX'
 s.cycles.device='GPU';s.world=bpy.data.worlds.new('Blue-hour atmosphere');s.world.use_nodes=True
 s.world.node_tree.nodes['Background'].inputs[0].default_value=(.065,.13,.22,1);s.world.node_tree.nodes['Background'].inputs[1].default_value=.22
 area('Concourse warm key',(-10,-5,9),(0,2,1),1500,(1,.60,.30),9)
 area('Sculpture light',(1,-.7,5.8),(0,-.7,1),700,(.35,.75,1),3)
 area('Blue city rim',(12,28,16),(0,3,4),3800,(.23,.51,1),14)
 area('Vault warm bounce',(-15,7,12),(0,12,9),1200,(1,.55,.25),9)
 area('Open-sky cool fill',(0,12,22),(0,12,0),2600,(.32,.56,.80),22)
 s.view_settings.view_transform='AgX';s.view_settings.look='AgX - Medium High Contrast';s.view_settings.exposure=0
 s.render.resolution_x=1920;s.render.resolution_y=1080;s.render.resolution_percentage=100;s.render.image_settings.file_format='PNG';s.render.image_settings.color_mode='RGB';s.render.image_settings.color_depth='8'
 bpy.ops.object.camera_add(location=(-4,-6,1.7));s.camera=bpy.context.object;s.camera.name='Beauty camera';s.camera.data.lens=24
 return s

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
  bpy.ops.object.mode_set(mode='EDIT');bpy.ops.mesh.select_all(action='SELECT');bpy.ops.uv.smart_project(angle_limit=math.radians(30),island_margin=.003,margin_method='FRACTION',scale_to_bounds=True);bpy.ops.uv.pack_islands(rotate=True,scale=True,margin_method='FRACTION',margin=8/(4096 if name=='hall' else 2048));bpy.ops.object.mode_set(mode='OBJECT')
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
  t=time.time();o=obs[0];n=4096 if name=='hall' else 2048
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
  bpy.data.images.remove(im);rows.append({'group':name,'resolution':n,'peakLinear':peak,'intensity':intensity,'seconds':round(time.time()-t,2),'samples':samples,'marginPixels':8,'islandSeparationPixels':8,'supportedMipLevels':2})
  log('Baked '+name);(ART/'bake-report.json').write_text(json.dumps(rows,indent=2)+'\n')


def metadata():
 # Simplified collision boxes are separate nodes outside the visual scene.
 cols=[]
 # Flush slab and all substantial authored props/walls; no tiny visual decals.
 boxes=[('Walkable floor',[-20,-12,-.3],[20,30,0])]+COLL
 for name,lo,hi in boxes:
  bpy.ops.mesh.primitive_cube_add(size=1,location=[(a+b)/2 for a,b in zip(lo,hi)]);o=bpy.context.object;o.name='Collision-'+str(len(cols));o.dimensions=[b-a for a,b in zip(lo,hi)];bpy.ops.object.transform_apply(location=False,rotation=False,scale=True);cols.append(o)
 # Grid navmesh inset for 0.3m capsule; cells intersecting blockers are removed.
 verts=[];faces=[];step=.5;cells=[]
 for xi in range(78):
  for yi in range(82):
   x=-19.5+xi*step;y=-11.5+yi*step
   if any(x+step>lo[0]-.35 and x<hi[0]+.35 and y+step>lo[1]-.35 and y<hi[1]+.35 for lo,hi in BLOCKS):continue
   i=len(verts);verts.extend([(x,y,0),(x+step,y,0),(x+step,y+step,0),(x,y+step,0)]);faces.extend([(i,i+1,i+2),(i,i+2,i+3)]);cells.append([xi,yi])
 m=bpy.data.meshes.new('Route mesh');m.from_pydata(verts,[],faces);nav=bpy.data.objects.new('Navigation',m);bpy.context.collection.objects.link(nav)
 (ART/'spatial-authoring.json').write_text(json.dumps({'blockers':BLOCKS,'navCells':cells,'gridOrigin':[-19.5,-11.5],'step':step,'collisionBoxes':boxes},indent=2)+'\n')
 return cols,nav

def export(cols,nav):
 obs=[o for group in GROUPS.values() for o in group]+cols+[nav];select(obs)
 bpy.ops.export_scene.gltf(filepath=str(OUT/'scene.gltf'),export_format='GLTF_SEPARATE',use_selection=True,export_yup=True,export_apply=True,export_tangents=True,export_animations=False,export_cameras=False,export_lights=False,export_extras=False,export_materials='EXPORT',export_image_format='AUTO',export_texture_dir='textures')
 path=OUT/'scene.gltf';g=json.loads(path.read_text());nodes={n.get('name'):i for i,n in enumerate(g['nodes'])};g['scenes'][g.get('scene',0)]['nodes']=[i for i in g['scenes'][g.get('scene',0)]['nodes'] if not g['nodes'][i].get('name','').startswith(('Collision-','Navigation','Visual-atmosphere'))]
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
  color=m.pop('emissiveFactor',[0,0,0]);gain=m.get('extensions',{}).pop('KHR_materials_emissive_strength',{}).get('emissiveStrength',1)
  m['pbrMetallicRoughness']={'baseColorFactor':[min(1,c*gain) for c in color]+[1],'metallicFactor':0,'roughnessFactor':1}
  if 'emissiveTexture' in m:m['pbrMetallicRoughness']['baseColorTexture']=m.pop('emissiveTexture')
  m.setdefault('extensions',{})['KHR_materials_unlit']={}
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
 manifest={k:SPEC[k] for k in ['id','version','name','description']};manifest.update(formatVersion='0.1',license='CC-BY-4.0',scene='scene.gltf',preview='preview.png',defaultSpawn='arrival',spawns=[{'id':'arrival','pose':{'position':[0,0,10],'rotation':[0,0,0,1]}}],attribution=[{'path':'.','author':'Hyprune contributors','license':'CC-BY-4.0','source':'https://github.com/hyprune/worlds/tree/main/switchyard'}],anchors=[],zones=[{'id':'concourse','name':'Concourse','bounds':{'min':[-20,0,2],'max':[20,9,12]}}],navigation={'kind':'mesh','node':nodes['Navigation'],'agentRadius':.3,'agentHeight':1.8},collision=[{'node':nodes[o.name],'shape':'mesh','layer':'static'} for o in cols],lightmaps=lm,audio=[])
 points=[{'id':'concourse','position':[-4,0,4.5]}];edges=[]
 for i,x in enumerate([-12,0,12]):
  p='junction-'+str(i+1);points.append({'id':p,'position':[x-2.67,0,4.5]});edges.append({'from':'concourse','to':p,'width':2.4})
  prior=p
  for st in [s for s in SPEC['stations'] if s['x']==x]:
   points.append({'id':st['id'],'position':[x-2.67,0,-(st['y']-1)]});edges.append({'from':prior,'to':st['id'],'width':2.4});prior=st['id']
 for st in SPEC['stations']:
  x,y=st['x'],st['y'];manifest['anchors'].append({'id':st['id']+'-dock','pose':{'position':[x+1.3,2.25,-(y+.79)],'rotation':[0,0,0,1]},'size':[4.2,2.36],'screenType':'com.hyprune.window'})
  manifest['zones'].append({'id':st['id'],'name':st['name'].title(),'bounds':{'min':[x-5,0,-(y+7)],'max':[x+5,7,-(y-5)]}})
 manifest['extensions']={'com.hyprune.switchyard.map':{'version':'0.1','path':'map.svg','projection':'xz','north':[0,0,-1],'bounds':[-20,-30,20,12]},'com.hyprune.switchyard.routes':{'version':'0.1','nodes':points,'edges':edges,'semantics':'authoring-only; bidirectional walking centerlines'}}
 # Package-local provenance remains readable independently of authoring sources.
 records=[];masters=json.loads((Path(__file__).parent/'materials/generation.json').read_text())
 for asset in masters:
  for suffix in ['albedo','normal','orm']:
   rel='textures/'+asset['name']+'-'+suffix+'.png'
   if not (OUT/rel).exists():continue
   records.append({'path':rel,'author':asset['author'],'license':asset['license'],'provenance':asset['provenance'],'masterSHA256':asset['masterSHA256'],'recipe':'materials/prepare.py: periodic healing, wrap-safe PBR derivation; original masters and complete prompts in materials/generation.json'})
   manifest['attribution'].append({'path':rel,'author':asset['author'],'license':asset['license'],'source':'https://github.com/hyprune/worlds/tree/main/switchyard/materials'})
 records.append({'path':'textures/transit-trim-albedo.png','author':'Hyprune contributors','license':'CC-BY-4.0','provenance':'Generated for Hyprune, CC-BY-4.0','recipe':'eight bands sliced from the original healed albedo tiles; 8px gutters'})
 (OUT/'texture-provenance.json').write_text(json.dumps(records,indent=2)+'\n')
 manifest['extensions']['com.hyprune.switchyard.materials']={'version':'0.1','path':'texture-provenance.json','uv0TexelDensityPxPerMeter':[512,1024]}
 manifest['requiredExtensions']=[];(OUT/'world.json').write_text(json.dumps(manifest,indent=2)+'\n')
 (OUT/'LICENSE').write_text((ROOT/'LICENSE').read_text());(OUT/'ATTRIBUTION.md').write_text((Path(__file__).parent/'ATTRIBUTION.md').read_text())
 # A vector blueprint derives from exactly the same station/route coordinates.
 svg=['<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 900 1000">','<rect width="900" height="1000" fill="#10232b"/>','<g fill="#e7dfca" font-family="sans-serif"><text x="55" y="70" font-size="36">SWITCHYARD</text><text x="55" y="102" font-size="16">SIX PERMANENT DOCKS / 1 UNIT = 1 M</text></g>']
 def xy(p):return 450+p[0]*19,200-p[2]*18
 lookup={p['id']:p['position'] for p in points}
 for e in edges:
  a,b=xy(lookup[e['from']]),xy(lookup[e['to']]);svg.append(f'<path d="M {a[0]} {a[1]} L {b[0]} {b[1]}" fill="none" stroke="#a5c6bd" stroke-width="5"/>')
 for st in SPEC['stations']:
  x,y=xy([st['x'],0,-st['y']]);c={'cyan':'#44b8bd','amber':'#dcac61','coral':'#cf7760'}[st['color']]
  svg.append(f'<rect x="{x-70}" y="{y-50}" width="170" height="120" rx="10" fill="#1c343d" stroke="{c}" stroke-width="3"/><text x="{x-53}" y="{y-15}" fill="{c}" font-family="sans-serif" font-size="21">{st["number"]}</text><text x="{x-53}" y="{y+17}" fill="#e7dfca" font-family="sans-serif" font-size="15">{st["name"]}</text>')
 svg.append('<text x="55" y="950" fill="#e7dfca" font-family="sans-serif" font-size="18">CONCOURSE / ARRIVAL</text></svg>');(OUT/'map.svg').write_text('\n'.join(svg))

def compositor():
 s=bpy.context.scene;tree=bpy.data.node_groups.new('Switchyard subtle practical bloom','CompositorNodeTree');tree.interface.new_socket(name='Image',in_out='OUTPUT',socket_type='NodeSocketColor')
 render=tree.nodes.new('CompositorNodeRLayers');glow=tree.nodes.new('CompositorNodeGlare');glow.inputs['Type'].default_value='Fog Glow';glow.inputs['Quality'].default_value='High';glow.inputs['Threshold'].default_value=1.4;glow.inputs['Strength'].default_value=.16;glow.inputs['Size'].default_value=.35
 output=tree.nodes.new('NodeGroupOutput');tree.links.new(render.outputs['Image'],glow.inputs['Image']);tree.links.new(glow.outputs['Image'],output.inputs['Image']);s.compositing_node_group=tree

def stills():
 s=bpy.context.scene;s.render.engine='CYCLES';s.cycles.samples=32;compositor()
 shots=[('01-concourse',(0,-10,1.7),(0,14,6.5),22),('02-arrival',(-16,-9,3.0),(0,9,5.0),26),('03-build',(-17,0,2.6),(-10.4,7,2.7),28),('04-route',(-14.67,10,2.2),(-10,24,3.8),26),('05-vault',(28,-21,15),(0,10,6),32)]
 for name,pos,target,lens in shots:
  camera(pos,target,lens);s.render.filepath=str(ART/(name+'.png'));bpy.ops.render.render(write_still=True)
 import shutil;shutil.copy2(ART/'01-concourse.png',OUT/'preview.png')

def film(preview=False):
 s=bpy.context.scene;s.render.engine='CYCLES';s.cycles.samples=24;s.cycles.use_denoising=True;s.render.use_persistent_data=True;s.render.fps=24;gpu();compositor()
 frames=ART/'film-frames';stamp=ART/'film-cache.sha256';digest=hashlib.sha256((ART/'switchyard.blend').read_bytes()+Path(__file__).read_bytes()).hexdigest()
 if not stamp.exists() or stamp.read_text().strip()!=digest:
  if frames.exists():shutil.rmtree(frames)
  stamp.write_text(digest+'\n')
 frames.mkdir(exist_ok=True)
 # Four deliberately composed nine-second shots: arrival, crafted dock,
 # human-scale walking route, then a high view revealing the complete vault.
 shots=[((0,-10,2.2),(-1.2,-8.6,2.4),(0,12,6),(0,14,6.2),22),((-17,-.5,2.6),(-17,1.5,2.5),(-10.4,7,2.7),(-10.4,7,2.7),28),((-14.67,9,2.2),(-14.67,16,2.2),(-10.7,20.8,3.2),(-10.7,20.8,3.2),26),((17,-8,12),(11,-6,9.5),(0,12,4.5),(0,13,4.5),24)]
 for i in ([0,215,216,431,432,647,648,863] if preview else range(864)):
  if (frames/f'{i:04d}.png').exists():continue
  shot=i//216;t=(i%216)/215;t=t*t*(3-2*t);a,b,c,d,lens=shots[shot]
  mix=lambda p,q:tuple(v*(1-t)+w*t for v,w in zip(p,q))
  camera(mix(a,b),mix(c,d),lens);s.render.filepath=str(frames/f'{i:04d}.png');bpy.ops.render.render(write_still=True)
 if preview:return
 subprocess.run(['ffmpeg','-y','-v','warning','-framerate','24','-i',str(frames/'%04d.png'),'-c:v','libx264','-preset','slow','-crf','22','-maxrate','6500k','-bufsize','13000k','-pix_fmt','yuv420p','-movflags','+faststart',str(ART/'world-switchyard.mp4')],check=True)
 (ART/'world-switchyard.json').write_text(json.dumps({'title':'World: Switchyard','tag':'world','notes':'Original procedural flagship world. Grand bronze vault, six timber-canopied project docks, upholstered lounges, labeled cargo, a route sculpture and an original blue-hour rail-city vista. 36-second remote Blender Cycles flythrough; static dock placeholders, no simulated live system state. CC-BY-4.0, Hyprune contributors.'},indent=2)+'\n')

if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--stage',choices=['build','preview','export','stills','film','film-preview'],default='build');p.add_argument('--samples',type=int,default=96);a=p.parse_args(sys.argv[sys.argv.index('--')+1:] if '--' in sys.argv else [])
 if socket.gethostname() in ['rick','rick-laptop']:raise SystemExit('Remote Blender only')
 if a.stage=='preview':
  s=scene();bpy.ops.wm.save_as_mainfile(filepath=str(ART/'switchyard-preview.blend'));stills()
 elif a.stage=='build':
  s=scene();join_groups();bake(a.samples)
  # Keep a source .blend with actual light sources; helpers added only for export.
  bpy.ops.wm.save_as_mainfile(filepath=str(ART/'switchyard.blend'));cols,nav=metadata();export(cols,nav)
  for helper in cols+[nav]:helper.hide_render=True
  stills()
 else:
  bpy.ops.wm.open_mainfile(filepath=str(ART/'switchyard.blend'));gpu()
  if a.stage=='export':
   GROUPS={o.name.removeprefix('Visual-'):[o] for o in bpy.context.scene.objects if o.type=='MESH' and o.name.startswith('Visual-')}
   authoring=json.loads((ART/'spatial-authoring.json').read_text());COLL=[(a,b,c) for a,b,c in authoring['collisionBoxes'][1:]];BLOCKS=authoring['blockers']
   LIGHTMAPS={r['group']:r['intensity'] for r in json.loads((ART/'bake-report.json').read_text())};cols,nav=metadata();export(cols,nav)
  elif a.stage=='stills':stills()
  else:film(a.stage=='film-preview')
 log('Complete '+a.stage)
