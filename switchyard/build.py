# SPDX-License-Identifier: MIT
"""Original procedural Switchyard. Run ONLY via tools/remote-blender.sh.
Blender authoring uses Z up; exporter converts to glTF +Y up: (x,z,-y).
No imported models, fonts, images or other art assets.
"""
import argparse, hashlib, json, math, os, shutil, socket, subprocess, sys, time
from pathlib import Path
import bpy
import numpy as np
from mathutils import Vector

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

def material(name,color,noise=.006,metal=0,emit=0):
 m=bpy.data.materials.new(name);m.use_nodes=True;p=m.node_tree.nodes.get('Principled BSDF')
 p.inputs['Roughness'].default_value=.68;p.inputs['Metallic'].default_value=metal
 # All original albedos are UV0 images, independent of illumination.
 im=texture('albedo-'+name,color,noise);n=m.node_tree.nodes.new('ShaderNodeTexImage');n.image=im
 uv=m.node_tree.nodes.new('ShaderNodeUVMap');uv.uv_map='UV0';m.node_tree.links.new(uv.outputs['UV'],n.inputs['Vector']);m.node_tree.links.new(n.outputs['Color'],p.inputs['Base Color'])
 if emit:p.inputs['Emission Color'].default_value=(*color,1);p.inputs['Emission Strength'].default_value=emit
 MATS[name]=m;return m

def add(o,name,mat,group,collision=False):
 o.name=name;o.data.materials.append(MATS[mat]);GROUPS.setdefault(group,[]).append(o)
 # UV0 is tiled in physical world space, independent of UV1 packing.
 if not o.data.uv_layers:o.data.uv_layers.new(name='UV0')
 uv=o.data.uv_layers[0];uv.name='UV0';o.data.calc_loop_triangles()
 for p in o.data.polygons:
  axis=max(range(3),key=lambda a:abs(p.normal[a]));axes=[a for a in range(3) if a!=axis]
  for li in p.loop_indices:
   v=o.matrix_world@o.data.vertices[o.data.loops[li].vertex_index].co;uv.data[li].uv=(v[axes[0]]*.5,v[axes[1]]*.5)
 if collision:
  vs=[o.matrix_world@Vector(v) for v in o.bound_box];lo=[min(v[i] for v in vs) for i in range(3)];hi=[max(v[i] for v in vs) for i in range(3)]
  COLL.append((name,lo,hi))
  if hi[2]>.08 and lo[2]<1.8:BLOCKS.append((lo,hi))
 return o

def box(name,pos,size,mat='stone',group='hall',bevel=.035,collision=False):
 bpy.ops.mesh.primitive_cube_add(size=1,location=pos);o=bpy.context.object;o.dimensions=size;bpy.ops.object.transform_apply(location=False,rotation=False,scale=True)
 if bevel:
  mod=o.modifiers.new('Soft machined edge','BEVEL');mod.width=bevel;mod.segments=2;bpy.ops.object.modifier_apply(modifier=mod.name)
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
 for args in [('stone',(.48,.43,.34),.012),('ivory',(.72,.68,.57),.008),('metal',(.035,.061,.071),.003),('panel',(.018,.032,.04),.001),('wood',(.26,.12,.055),.009),('leaf',(.095,.22,.15),.006),('soil',(.055,.04,.027),.012),('letter',(.8,.84,.76),0),('warm',(.96,.72,.37),0,0,2),('white',(.73,.84,.81),0,0,1.5)]:material(*args)
 for k,c in COLORS.items():material(k,c,.004);material(k+'-glow',c,0,0,2)
 # Continuous level slab: rail graphics are visual; walking never crosses steps.
 box('Foundation',(0,9,-.43),(42,44,.85),'metal','hall',.12)
 box('Concourse',(0,-7,-.10),(40,10,.2),'stone','hall',.02)
 for x in [-12,0,12]:box('Platform',(x,14,-.10),(10,32,.2),'stone','hall',.02)
 # Fill seams/gaps as flush darker paving, not traversable voids.
 for x in [-18.5,-6,6,18.5]:box('Service paving',(x,14,-.12),(3 if abs(x)>10 else 2,32,.24),'metal','hall',.02)
 # Perimeter walls and guardrails close the walkable boundary.
 box('Back wall',(0,30,2.7),(40,.35,5.4),'ivory','hall',.05,True)
 for x in [-20,20]:
  box('Garden wall',(x,10,.75),(.35,40,1.5),'stone','hall',.045,True)
  for y in [-6,4,14,24]:
   box('Perimeter mast',(x,y,3.9),(.22,.22,8),'metal','hall',.02)
   box('Lantern',(x,y,7.9),(.45,.45,.22),'warm','hall',.02)
 # Each canopy is physically supported outside the circulation/cargo lanes.
 for x in [-12,0,12]:
  for y in [7,18,27]:
   box('Canopy',(x,y,8.2),(10.3,7.2,.18),'ivory','hall',.035)
   for off in [-4.75,4.75]:
    box('Canopy beam',(x+off,y,8.0),(.18,7.3,.3),'metal','hall',.01)
    box('Ceiling ribbon',(x+off,y,7.82),(.07,6.6,.05),'warm','hall',.005)
    for dy in [-2.7,2.7]:box('Canopy column',(x+off,y+dy,3.93),(.20,.20,8.14),'metal','hall',.025,True)
 # Grand entrance portal, open below 5.3m.
 for x in [-18,18]:box('Portal leg',(x,-10,3.4),(.55,.55,6.8),'ivory','hall',.06,True)
 box('Portal header',(0,-10,6.45),(36.5,.6,1.1),'metal','hall',.04)
 text('S W I T C H Y A R D',(0,-10.315,6.48),.45,'letter')
 # Arrival totem, central meeting point, outside the main transverse corridor.
 cylinder('Hub plinth',(0,-8,.20),1.7,.4,'metal','hall',collision=True)
 cylinder('Hub stem',(0,-8,2.65),.17,4.9,'metal','hall')
 bpy.ops.mesh.primitive_torus_add(major_radius=1.35,minor_radius=.055,major_segments=64,minor_segments=8,location=(0,-8,5.1),rotation=(math.pi/2,0,0));add(bpy.context.object,'Concourse halo','warm','hall')
 box('Arrival board',(0,-8,3.95),(5.4,.18,1.4),'panel','hall',.065)
 text('CONCOURSE',(0,-8.11,4.3),.32)
 text('01 02 03 / 04 05 06',(0,-8.11,3.86),.22,'white')
 text('YOUR PLACE IS WAITING',(0,-8.11,3.5),.14)
 # Broad foreground crossing, three route spines and six named docks.
 for x,color in [(-12,'cyan'),(0,'amber'),(12,'coral')]:
  for offset in [-2.9,-2.45]:box('Route stripe',(x+offset,12,.030),(.045,34,.014),color+'-glow','hall',.003)
  box('Concourse branch',(x-1.35,-4.5,.013),(2.7,.045,.015),color+'-glow','hall',.003)
  for y in [-1,13,26]:
   for dx in [-.16,.16]:
    o=box('Route arrow',(x-2.67+dx,y,.062),(.035,.5,.012),color+'-glow','hall',.002);o.rotation_euler.z=math.radians(35 if dx<0 else -35)
 for st in SPEC['stations']:
  x,y,c=st['x'],st['y'],st['color'];g=st['id']
  # Screen pane at eye level: its front is .12m ahead of the backplate.
  box('Dock backplate',(x+1.3,y+1,2.15),(4.7,.22,2.9),'metal',g,.08,True)
  box('Idle dock pane',(x+1.3,y+.87,2.25),(4.2,.025,2.36),'panel',g,.025)
  for dx in [-2.25,2.25]:box('Dock rim',(x+1.3+dx,y+.84,2.25),(.055,.065,2.55),c+'-glow',g,.009)
  for dx in [-1.85,1.85]:box('Dock stand',(x+1.3+dx,y+1,.4),(.18,.38,.8),'metal',g,.02)
  # Preview is a deliberately abstract dock emblem; runtime apps replace it.
  text(st['number'],(x+1.3,y+.846,2.6),.40,c+'-glow',g)
  text('DOCK',(x+1.3,y+.846,1.96),.19,'letter',g)
  box('Station sign',(x+.55,y+1,4.12),(6.2,.18,.72),'metal',g,.035)
  text(st['number']+'  '+st['name'],(x+.55,y+.895,4.13),.29,'letter',g)
  box('Signal pole',(x-3.8,y+1,1.25),(.1,.1,2.5),'metal',g,.015,True)
  box('Signal identity',(x-3.8,y+.92,2.6),(.45,.08,.7),c,g,.035)
  text(st['number'],(x-3.8,y+.874,2.6),.20,'letter',g)
  # Cabinet drawers: pinned files as authored cargo, no runtime data claims.
  for row in range(3):
   cy=y-3+row*.95
   box('Cargo',(x+3.5,cy,.59),(1.35,.78,1.15),'ivory',g,.065,True)
   box('Cargo stripe',(x+3.5,cy-.402,.62),(1.0,.025,.085),c,g,.01)
   box('Cargo grip',(x+3.5,cy-.424,.84),(.26,.035,.055),'metal',g,.01)
  box('Cargo plaque',(x+3.5,y-3.405,1.34),(1.35,.05,.3),'metal',g,.015);text('CARGO',(x+3.5,y-3.438,1.34),.14,'letter',g)
  # Low warm bench along one side, away from the 2.4m route aisle.
  box('Bench seat',(x+1,y-3,.48),(2.8,.65,.12),'wood',g,.04,True)
  for dx in [-1,1]:box('Bench foot',(x+1+dx,y-3,.22),(.15,.5,.44),'metal',g,.025)
  tree(x+3.55,y+4,g)
  area('Dock pool '+g,(x,y-1,6.9),(x,y,0),350,(1,.78,.52),5)
 # Paving seams have a real 1cm separation above substrate, never coplanar.
 for y in range(-11,30,2):
  for x in [-12,0,12]:box('Paving joint',(x,y,.010),(9.8,.016,.012),'metal','hall',0)
 # Remote-only lighting/render setup.
 s=bpy.context.scene;s.render.engine='CYCLES';s.cycles.samples=96;s.cycles.use_denoising=True
 prefs=bpy.context.preferences.addons['cycles'].preferences;prefs.compute_device_type='OPTIX';prefs.get_devices()
 for d in prefs.devices:d.use=d.type=='OPTIX'
 s.cycles.device='GPU'
 s.world=bpy.data.worlds.new('Quiet afternoon');s.world.use_nodes=True
 s.world.node_tree.nodes['Background'].inputs[0].default_value=(.34,.45,.52,1);s.world.node_tree.nodes['Background'].inputs[1].default_value=.32
 area('Afternoon key',(-18,-12,23),(0,10,0),11000,(1,.81,.58),18)
 area('Sky fill',(14,14,19),(0,12,0),6500,(.57,.77,1),22)
 d=bpy.data.lights.new('Sun','SUN');d.energy=1.5;d.angle=.12;o=bpy.data.objects.new('Sun',d);bpy.context.collection.objects.link(o);o.rotation_euler=(.35,-.45,-.6)
 s.view_settings.view_transform='AgX';s.render.resolution_x=1920;s.render.resolution_y=1080;s.render.resolution_percentage=100
 s.render.image_settings.file_format='PNG'
 s.render.film_transparent=False
 bpy.ops.object.camera_add(location=(35,-39,25));cam=bpy.context.object;cam.name='Beauty camera';cam.data.lens=42;s.camera=cam
 return s

def camera(pos,target,lens=40):
 c=bpy.context.scene.camera;c.location=pos;c.rotation_euler=(Vector(target)-c.location).to_track_quat('-Z','Y').to_euler();c.data.lens=lens

def join_groups():
 for name,obs in list(GROUPS.items()):
  select(obs);bpy.ops.object.join();o=bpy.context.object;o.name='Visual-'+name
  # Each group owns its material bindings and its unique atlas.
  for i,m in enumerate(o.data.materials):o.data.materials[i]=m.copy();o.data.materials[i].name=name+'--'+m.name
  select([o]);uv=o.data.uv_layers.new(name='UV1');o.data.uv_layers.active=uv;uv.active_render=True
  bpy.ops.object.mode_set(mode='EDIT');bpy.ops.mesh.select_all(action='SELECT');bpy.ops.uv.smart_project(angle_limit=math.radians(66),island_margin=.003,margin_method='FRACTION',scale_to_bounds=True);bpy.ops.uv.pack_islands(rotate=True,scale=True,margin_method='FRACTION',margin=8/(4096 if name=='hall' else 2048));bpy.ops.object.mode_set(mode='OBJECT')
  uv=o.data.uv_layers['UV1'];log(f'UV1 {name}: {min(c for d in uv.data for c in d.uv):.5f} .. {max(c for d in uv.data for c in d.uv):.5f}');assert all(-1e-6<=c<=1.000001 for d in uv.data for c in d.uv),name
  o.data.uv_layers['UV0'].active_render=True
  GROUPS[name]=[o]

def save_srgb(name,a):
 s=bpy.context.scene;old=s.view_settings.view_transform;s.view_settings.view_transform='Standard';s.view_settings.look='None';s.view_settings.exposure=0
 im=bpy.data.images.new(name,width=a.shape[1],height=a.shape[0],alpha=False,float_buffer=True);im.pixels.foreach_set(a.ravel())
 s.render.image_settings.color_mode='RGB';s.render.image_settings.color_depth='8';im.save_render(str(OUT/'textures'/f'{name}.png'),scene=s)
 bpy.data.images.remove(im);s.view_settings.view_transform=old

def bake(samples):
 s=bpy.context.scene;s.cycles.samples=samples;s.render.bake.margin=8;s.render.bake.use_clear=True
 rows=[]
 for name,obs in GROUPS.items():
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
 bpy.ops.export_scene.gltf(filepath=str(OUT/'scene.gltf'),export_format='GLTF_SEPARATE',use_selection=True,export_yup=True,export_apply=True,export_animations=False,export_cameras=False,export_lights=False,export_extras=False,export_materials='EXPORT',export_image_format='AUTO',export_texture_dir='textures')
 path=OUT/'scene.gltf';g=json.loads(path.read_text());nodes={n.get('name'):i for i,n in enumerate(g['nodes'])};g['scenes'][g.get('scene',0)]['nodes']=[i for i in g['scenes'][g.get('scene',0)]['nodes'] if not g['nodes'][i].get('name','').startswith(('Collision-','Navigation'))]
 # Lighting is manifest metadata. No fake Khronos extension or occlusion trick.
 lm=[]
 for name,intensity in LIGHTMAPS.items():
  ii=len(g['images']);g['images'].append({'uri':'textures/lightmap-'+name+'.png'})
  ti=len(g['textures']);g['textures'].append({'source':ii,'sampler':len(g.setdefault('samplers',[]))});g['samplers'].append({'magFilter':9729,'minFilter':9729,'wrapS':33071,'wrapT':33071})
  for mi,m in enumerate(g['materials']):
   if m.get('name','').startswith(name+'--'):lm.append({'material':mi,'texture':ti,'texCoord':1,'encoding':'srgb','intensity':intensity})
 # Required base contract uses only core glTF PBR. Our metallics are deliberately matte.
 path.write_text(json.dumps(g,indent=2)+'\n')
 manifest={k:SPEC[k] for k in ['id','version','name','description']};manifest.update(formatVersion='0.1',license='CC-BY-4.0',scene='scene.gltf',preview='preview.png',defaultSpawn='arrival',spawns=[{'id':'arrival','pose':{'position':[-4,0,6],'rotation':[0,0,0,1]}}],attribution=[{'path':'.','author':'Hyprune contributors','license':'CC-BY-4.0','source':'https://github.com/hyprune/worlds/tree/main/switchyard'}],anchors=[],zones=[{'id':'concourse','name':'Concourse','bounds':{'min':[-20,0,2],'max':[20,9,12]}}],navigation={'kind':'mesh','node':nodes['Navigation'],'agentRadius':.3,'agentHeight':1.8},collision=[{'node':nodes[o.name],'shape':'mesh','layer':'static'} for o in cols],lightmaps=lm,audio=[])
 points=[{'id':'concourse','position':[-4,0,4.5]}];edges=[]
 for i,x in enumerate([-12,0,12]):
  p='junction-'+str(i+1);points.append({'id':p,'position':[x-2.67,0,4.5]});edges.append({'from':'concourse','to':p,'width':2.4})
  prior=p
  for st in [s for s in SPEC['stations'] if s['x']==x]:
   points.append({'id':st['id'],'position':[x-2.67,0,-(st['y']-1)]});edges.append({'from':prior,'to':st['id'],'width':2.4});prior=st['id']
 for st in SPEC['stations']:
  x,y=st['x'],st['y'];manifest['anchors'].append({'id':st['id']+'-dock','pose':{'position':[x+1.3,2.25,-(y+.82)],'rotation':[0,0,0,1]},'size':[4.2,2.36],'screenType':'com.hyprune.window'})
  manifest['zones'].append({'id':st['id'],'name':st['name'].title(),'bounds':{'min':[x-5,0,-(y+7)],'max':[x+5,7,-(y-5)]}})
 manifest['extensions']={'com.hyprune.switchyard.map':{'version':'0.1','path':'map.svg','projection':'xz','north':[0,0,-1],'bounds':[-20,-30,20,12]},'com.hyprune.switchyard.routes':{'version':'0.1','nodes':points,'edges':edges,'semantics':'authoring-only; bidirectional walking centerlines'}}
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

def stills():
 s=bpy.context.scene;s.render.engine='BLENDER_EEVEE';s.cycles.samples=64
 shots=[('01-concourse',(36,-45,27),(0,9,2),36),('02-arrival',(-11,-17,3.1),(-1,9,3),25),('03-build',(-17,0,3.2),(-10,7,2.3),32),('04-route',(-15,11,2.6),(-10,23,2.6),28)]
 for name,pos,target,lens in shots:
  camera(pos,target,lens);s.render.filepath=str(ART/(name+'.png'));bpy.ops.render.render(write_still=True)
 import shutil;shutil.copy2(ART/'01-concourse.png',OUT/'preview.png')

def film(preview=False):
 s=bpy.context.scene;s.render.engine='BLENDER_EEVEE';s.render.fps=24
 frames=ART/'film-frames';stamp=ART/'film-cache.sha256';digest=hashlib.sha256((ART/'switchyard.blend').read_bytes()+Path(__file__).read_bytes()).hexdigest()
 if not stamp.exists() or stamp.read_text().strip()!=digest:
  if frames.exists():shutil.rmtree(frames)
  stamp.write_text(digest+'\n')
 frames.mkdir(exist_ok=True)
 # Four gentle shots: overview, arrival, along a route, and a dock portrait.
 shots=[((36,-45,27),(29,-37,23),(0,9,2),(0,11,2),36),((-13,-17,3.2),(-11,-9,3.1),(-1,8,3),(-1,11,3),26),((-14.65,-1,2.6),(-14.65,13,2.6),(-10,13,3),(-10,25,3),29),((-5,12,4),(2,12,3.5),(1,20,2.7),(1,20,2.7),32)]
 for i in ([0,216,432,648] if preview else range(864)):
  if (frames/f'{i:04d}.png').exists():continue
  shot=i//216;t=(i%216)/215;t=t*t*(3-2*t);a,b,c,d,lens=shots[shot]
  mix=lambda p,q:tuple(v*(1-t)+w*t for v,w in zip(p,q))
  camera(mix(a,b),mix(c,d),lens);s.render.filepath=str(frames/f'{i:04d}.png');bpy.ops.render.render(write_still=True)
 if preview:return
 subprocess.run(['ffmpeg','-y','-v','warning','-framerate','24','-i',str(frames/'%04d.png'),'-c:v','libx264','-preset','slow','-crf','22','-maxrate','6500k','-bufsize','13000k','-pix_fmt','yuv420p','-movflags','+faststart',str(ART/'world-switchyard.mp4')],check=True)
 (ART/'world-switchyard.json').write_text(json.dumps({'title':'World: Switchyard','tag':'world','notes':'Original procedural flagship world. Six permanent docks, cargo cabinets and a calm concourse. 36-second remote Blender Eevee flythrough; static dock placeholders, no simulated live system state. CC-BY-4.0, Hyprune contributors.'},indent=2)+'\n')

if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--stage',choices=['build','stills','film','film-preview'],default='build');p.add_argument('--samples',type=int,default=96);a=p.parse_args(sys.argv[sys.argv.index('--')+1:] if '--' in sys.argv else [])
 if socket.gethostname() in ['rick','rick-laptop']:raise SystemExit('Remote Blender only')
 if a.stage=='build':
  s=scene();join_groups();bake(a.samples)
  # Keep a source .blend with actual light sources; helpers added only for export.
  bpy.ops.wm.save_as_mainfile(filepath=str(ART/'switchyard.blend'));cols,nav=metadata();export(cols,nav);stills()
 else:
  bpy.ops.wm.open_mainfile(filepath=str(ART/'switchyard.blend'))
  if a.stage=='stills':stills()
  else:film(a.stage=='film-preview')
 log('Complete '+a.stage)
