# SPDX-License-Identifier: MIT
"""Lumen Reach: original procedural architecture. Execute only on remote host."""
import os,sys,json,math,shutil,random
from pathlib import Path
if os.environ.get('HYPRUNE_REMOTE_BLENDER')!='1': raise SystemExit('Use tools/remote-lumen.sh; never local Blender')
import bpy,bmesh,numpy as np
from mathutils import Vector,Matrix
ROOT=Path(__file__).resolve().parents[1];HERE=Path(__file__).parent
sys.path.insert(0,str(ROOT/'tools'));import bake_pipeline as P
OUT=ROOT/'dist/com.hyprune.lumen-reach';ART=ROOT/'artifacts/lumen-reach'
P.OUT=OUT;P.ART=ART;P.BEVEL_SEGMENTS=1
ANCHORS=[];OBJECTS=[];AREAS=[];ROUTES=[];EDGES=[];WALK=[];MOUNT_ROWS=[]
NAMES=['sun-court','array-hall','rime-vault','signal-rise']
TITLES=['SUN COURT','ARRAY HALL','RIME VAULT','SIGNAL RISE']
AREA=0;BASE=0;G='sun-court';COUNT={};STAIR_ROUTES=[]
UNLIT=set();VIEWS=[]
LANDMARKS={'arrival': 'Sun Court', 'globe-platform': 'Instrument terrace', 'lookout': 'West lookout', 'cascade-bridge': 'Upper Cascade', 'rooftop': 'Rooftop shelter', 'hall-arrival': 'Array Hall', 'hall-upper': 'Upper balcony', 'vault-arrival': 'Rime Vault', 'vault-platform': 'Maintenance deck', 'rise-arrival': 'Signal Rise', 'fortress-room': 'Gate operator room', 'diagnostics-platform': 'Diagnostics deck', 'dish-platform': 'Dish terrace', 'gantry-west': 'Cable gantry'}

def box(name,pos,size,mat='concrete',bevel=.025,solid=False,group=None):
 return P.box(name,pos,size,mat,group or G,bevel,solid)
def cyl(name,pos,r,d,mat='metal',group=None,vertices=12):
 return P.cylinder(name,pos,r,d,mat,group or G,vertices)
def mesh(name,verts,faces,mat,solid=False,group=None):
 me=bpy.data.meshes.new(name);me.from_pydata(verts,[],faces);me.update();o=bpy.data.objects.new(name,me);bpy.context.collection.objects.link(o);P.add(o,name,mat,group or G)
 if solid:WALK.append(o)
 return o

def rod(name,a,b,r=.035,mat='metal',group=None):
 a,b=Vector(a),Vector(b);o=cyl(name,(a+b)/2,r,(b-a).length,mat,group);o.rotation_euler=(b-a).to_track_quat('Z','Y').to_euler();return o

def torus(name,pos,r,minor=.04,mat='amber',rotation=(0,0,0),group=None):
 bpy.ops.mesh.primitive_torus_add(major_segments=48,minor_segments=6,location=pos,major_radius=r,minor_radius=minor,rotation=rotation);return P.add(bpy.context.object,name,mat,group or G)

def mat(name,color,asset=None,rough=.6,metal=0,emit=False,unlit=False,tint=False):
 m=bpy.data.materials.new(name);m.use_nodes=True;nt=m.node_tree;p=nt.nodes.get('Principled BSDF');p.inputs['Base Color'].default_value=(*color,1);p.inputs['Roughness'].default_value=rough;p.inputs['Metallic'].default_value=metal
 uv=nt.nodes.new('ShaderNodeUVMap');uv.uv_map='UV0'
 if asset:
  for suffix in ['albedo','normal','orm']:
   im=bpy.data.images.load(str(HERE/'materials/tiles'/f'{asset}-{suffix}.png'),check_existing=True);t=nt.nodes.new('ShaderNodeTexImage');t.image=im;nt.links.new(uv.outputs['UV'],t.inputs['Vector'])
   if suffix=='albedo':
    if tint:
     mix=nt.nodes.new('ShaderNodeMixRGB');mix.blend_type='MULTIPLY';mix.inputs[0].default_value=1;mix.inputs[2].default_value=(*color,1);nt.links.new(t.outputs['Color'],mix.inputs[1]);nt.links.new(mix.outputs[0],p.inputs['Base Color'])
    else:nt.links.new(t.outputs['Color'],p.inputs['Base Color'])
   else:
    im.colorspace_settings.name='Non-Color'
    if suffix=='normal':
     n=nt.nodes.new('ShaderNodeNormalMap');n.inputs['Strength'].default_value=.65;nt.links.new(t.outputs['Color'],n.inputs['Color']);nt.links.new(n.outputs['Normal'],p.inputs['Normal'])
    else:
     sep=nt.nodes.new('ShaderNodeSeparateColor');nt.links.new(t.outputs['Color'],sep.inputs['Color']);nt.links.new(sep.outputs['Green'],p.inputs['Roughness']);nt.links.new(sep.outputs['Blue'],p.inputs['Metallic'])
 if emit:p.inputs['Emission Color'].default_value=(*color,1);p.inputs['Emission Strength'].default_value=1
 if unlit:
  e=nt.nodes.new('ShaderNodeEmission');e.inputs['Color'].default_value=(*color,1);e.inputs['Strength'].default_value=1
  if asset and p.inputs['Base Color'].is_linked:nt.links.new(p.inputs['Base Color'].links[0].from_socket,e.inputs['Color'])
  nt.links.new(e.outputs[0],nt.nodes.get('Material Output').inputs['Surface']);UNLIT.add(name)
 if tint:m['lumenAlbedoTint']=list(color)
 P.MATS[name]=m;return m

def init():
 bpy.ops.wm.read_factory_settings(use_empty=True)
 if OUT.exists():shutil.rmtree(OUT)
 OUT.mkdir(parents=True);(OUT/'textures').mkdir();ART.mkdir(parents=True,exist_ok=True)
 for name,asset,col,rough,metal in [('concrete','concrete',(.52,.46,.36),.75,0),('stone','paving',(.24,.28,.3),.3,0),('metal','metal',(.04,.055,.07),.4,.65),('canvas','canvas',(.52,.42,.28),.9,0),('wood','wood',(.3,.16,.07),.6,0),('frost','frost',(.16,.22,.26),.72,.45),('glass','glass',(.025,.06,.09),.18,.2),('grating','grating',(.04,.05,.055),.48,.5),('snow','snow',(.5,.65,.8),.85,0),('strip','strips',(.4,.2,.05),.3,.3),('rock','rock',(.35,.37,.38),.84,0)]:mat(name,col,asset,rough,metal)
 for name,asset,rough,metal in [('vault-metal','frost-metal-v3',.48,.55),('rime-crust','rime-crust-v3',.88,0),('condensation','condensation-v3',.26,.18)]:mat(name,(1,1,1),asset,rough,metal)
 mat('ice-body',(.38,.60,.69),'condensation-v3',rough=.2,tint=True)
 m=mat('ice-rim',(.10,.22,.29),'rime-crust-v3',rough=.18,emit=True,tint=True)
 P.TILE_METERS.update({'vault-metal':2,'rime-crust':1,'condensation':2,'ice-body':1,'ice-rim':1})
 m=mat('trim',(.5,.3,.12),rough=.4,metal=.35);t=m.node_tree.nodes.new('ShaderNodeTexImage');t.image=bpy.data.images.load(str(HERE/'materials/tiles/reach-trim-albedo.png'));uv=m.node_tree.nodes.new('ShaderNodeUVMap');uv.uv_map='UV0';m.node_tree.links.new(uv.outputs['UV'],t.inputs['Vector']);m.node_tree.links.new(t.outputs['Color'],m.node_tree.nodes['Principled BSDF'].inputs['Base Color'])
 P.TILE_METERS.update(concrete=2,stone=2,metal=1,canvas=1,wood=1,frost=1,glass=2,grating=1,snow=2,strip=1,rock=4)
 for name,col,rough in [('red',(.33,.065,.035),.85),('leaf',(.42,.035,.018),.8),('leaf-gold',(.45,.16,.025),.8),('earth',(.035,.022,.012),.95),('ivory',(.7,.66,.54),.65),('black',(.16,.20,.24),.6),('ice',(.22,.38,.45),.45)]:mat(name,col,{'red':'canvas','leaf':'canvas','leaf-gold':'canvas','earth':'concrete','ivory':'concrete','black':'metal','ice':'frost'}[name],rough=rough,tint=True)
 for name,col in [('amber',(1,.42,.085)),('red-light',(.9,.018,.006)),('cyan',(.11,.48,.68)),('white',(.62,.73,.82))]:mat(name,col,'glass',emit=True,tint=True)
 for name,col in [('sky-far',(.24,.38,.49)),('mountain-far',(.29,.38,.43)),('mountain-mid',(.18,.27,.30)),('mountain-near',(.10,.19,.19)),('snow-peak',(.64,.69,.70)),('waterfall',(.47,.68,.74)),('spire',(.67,.64,.54)),('night',(.00060705,.01161225,.04666509)),('night-peak',(.035,.063,.12))]:mat(name,col,'concrete' if name=='spire' else None,unlit=True,tint=True)
 m=mat('steam-card',(1,1,1),emit=True);nt=m.node_tree;t=nt.nodes.new('ShaderNodeTexImage');t.image=bpy.data.images.load(str(HERE/'materials/tiles/steam-albedo.png'));t.extension='EXTEND';u=nt.nodes.new('ShaderNodeUVMap');u.uv_map='UV0';nt.links.new(u.outputs['UV'],t.inputs['Vector']);p=nt.nodes.get('Principled BSDF');nt.links.new(t.outputs['Color'],p.inputs['Base Color']);nt.links.new(t.outputs['Color'],p.inputs['Emission Color']);nt.links.new(t.outputs['Alpha'],p.inputs['Alpha']);m.surface_render_method='DITHERED'
 s=bpy.context.scene;s.unit_settings.system='METRIC';s.unit_settings.scale_length=1;s.render.engine='CYCLES';s.cycles.samples=48;s.cycles.use_denoising=True;s.cycles.max_bounces=5;s.cycles.diffuse_bounces=3;P.gpu()
 s.world=bpy.data.worlds.new('Watershed sky');s.world.use_nodes=True;s.world.node_tree.nodes['Background'].inputs[0].default_value=(.32,.43,.57,1);s.world.node_tree.nodes['Background'].inputs[1].default_value=.28
 s.view_settings.view_transform='AgX';s.view_settings.look='AgX - Medium High Contrast';s.render.resolution_x=1920;s.render.resolution_y=1080;s.render.resolution_percentage=100;s.render.image_settings.file_format='PNG';s.render.image_settings.color_mode='RGB'
 bpy.ops.object.camera_add();s.camera=bpy.context.object;s.camera.data.sensor_fit='HORIZONTAL';s.camera.data.sensor_width=36;s.camera.data.lens=36/(2*math.tan(math.radians(60)/2)*(1920/1080))
 # Architectural warm sunlight is localized so the night home remains cold.
 P.area('Sun Court daylight',(-18,-5,32),(0,7,0),19000,(1,.78,.54),7)
 P.area('Sun Court sky fill',(16,0,28),(0,12,1),4000,(.55,.73,1),26)

def audit_fixtures():
 # Ray-test every thin emissive object before merging loses authoring names.
 # Close gaps with a real metal mounting shoe, never move the lens coplanar.
 from mathutils.bvhtree import BVHTree
 bpy.context.view_layer.update()
 emissive={'amber','red-light','cyan','white'}
 objects=[o for group in P.GROUPS.values() for o in group]
 verts=[];faces=[];owners=[]
 for o in objects:
  if o.data.materials[0].name in emissive or o.name.startswith(('Lettering','Soft vent','Reach horizon','Reach rising stem')):continue
  # Artwork/vistas cannot be a mechanical support.
  if o in P.GROUPS.get('vista',[]):continue
  start=len(verts);verts.extend(o.matrix_world@v.co for v in o.data.vertices)
  for face in o.data.polygons:faces.append(tuple(start+i for i in face.vertices));owners.append(o.name)
 tree=BVHTree.FromPolygons(verts,faces);rows=[]
 for o in objects:
  if o.data.materials[0].name not in emissive:continue
  local=[Vector(v) for v in o.bound_box];lo=Vector([min(v[i] for v in local) for i in range(3)]);hi=Vector([max(v[i] for v in local) for i in range(3)]);size=hi-lo
  # Curved rings, network wires and lamp diffusers are self-contained fixtures.
  if len(o.data.polygons)>70 or not any(k in o.name.lower() for k in ['light','edge','strip','practical','bar','seam','jamb']):continue
  center=o.matrix_world@((lo+hi)/2);best=None
  for axis in range(3):
   if size[axis]>.20:continue
   for sign in [-1,1]:
    direction=o.matrix_world.to_3x3()@Vector([sign if i==axis else 0 for i in range(3)]);direction.normalize()
    loc,norm,index,distance=tree.ray_cast(center,direction,.7)
    if loc is not None and (best is None or distance<best[0]):best=(distance,axis,direction,loc,index)
  if best is None:
   rows.append({'name':o.name,'status':'UNSUPPORTED','position':up(center)});continue
  distance,axis,direction,loc,index=best;half=size[axis]/2;gap=distance-half
  # Geometry penetrates its host, or is already seated; a flush back is safe.
  if gap>.003:
   dims=list(size);dims[axis]=gap+.025
   for i in range(3):
    if i!=axis:dims[i]+=.045
   shoe=P.box(o.name+' mounting shoe',center+direction*(half+gap/2-.005),dims,'metal',next(k for k,v in P.GROUPS.items() if o in v),.003)
   shoe.rotation_mode='QUATERNION';shoe.rotation_quaternion=o.matrix_world.to_quaternion()
  rows.append({'name':o.name,'status':'SEATED','host':owners[index],'originalBackGapMeters':round(gap,5),'position':up(center)})
 decals=[]
 for o in objects:
  if not o.name.startswith(('Lettering','Reach horizon','Reach rising stem')):continue
  samples=[o.matrix_world@p.center for p in o.data.polygons] if o.name.startswith('Lettering') else [sum((o.matrix_world@Vector(v) for v in o.bound_box),Vector())/8]
  gaps=[];hosts=[]
  for center in samples:
   loc,norm,index,distance=tree.ray_cast(center,Vector((0,1,0)),.65)
   if loc is not None:gaps.append(distance);hosts.append(owners[index])
  decals.append({'name':o.name,'probes':len(samples),'supportedProbes':len(gaps),'maxBackingDistanceMeters':round(max(gaps),5) if gaps else None,'hosts':sorted(set(hosts)),'status':'PASS' if len(gaps)==len(samples) and max(gaps,default=0)<=.035 else 'FAIL'})
 (ART/'decal-audit.json').write_text(json.dumps({'status':'PASS' if all(r['status']=='PASS' for r in decals) else 'FAIL','decals':decals},indent=2)+'\n')
 (ART/'fixture-audit.json').write_text(json.dumps({'status':'FAIL' if any(r['status']!='SEATED' for r in rows) else 'PASS','strips':rows},indent=2)+'\n')
 assert all(r['status']=='SEATED' for r in rows),[r for r in rows if r['status']!='SEATED']
 assert all(r['status']=='PASS' for r in decals),[r for r in decals if r['status']!='PASS']

# Original geometric lettering kit, shared implementation with the test world.
sys.path.insert(0,str(ROOT/'switchyard'));from lettering import GLYPHS

def label(word,pos,height=.32,mat='ivory'):
 pitch=height/7;w=(len(word)*6-1)*pitch;verts=[];faces=[]
 x,y,z=pos
 depth={'01 SUN COURT':.38,'03 RIME VAULT':.47,'04 SIGNAL RISE':.50,'SEALED':.14,'CONTINUATION':.14}.get(word,.10)
 box('Sign plaque '+word,(x,y+.018+depth/2,z),(w+.20,depth,height+.16),'metal',.006)
 if word in ['ARRAY HALL','02 ARRAY HALL']:
  # Entrance signs hang from the canopy; atrium plaque brackets meet the wall frame.
  target=4.42 if word=='ARRAY HALL' else 14.15
  for dx in [-w*.38,w*.38]:rod('Sign bracket',(x+dx,y+.07,z),(x+dx,y+.35,target),.035)
 elif word=='RIME VAULT':
  rod('Service direction sign mast',(x,y+.10,0),(x,y+.10,z+.2),.045)
 elif word=='UPPER CASCADE':
  for dx in [-w*.35,w*.35]:rod('Bridge plaque bracket',(x+dx,y+.06,z),(x+dx,12,4.65),.03)
 for j,ch in enumerate(word):
  if ch==' ':continue
  for row,bits in enumerate(GLYPHS[ch]):
   for col,b in enumerate(bits):
    if b!='1':continue
    x=pos[0]-w/2+(j*6+col+.5)*pitch;z=pos[2]+(3-row)*pitch;y=pos[1];q=len(verts);a=pitch*.42
    verts.extend([(x-a,y,z-a),(x+a,y,z-a),(x+a,y,z+a),(x-a,y,z+a)]);faces.append((q,q+1,q+2,q+3))
 return mesh('Lettering '+word,verts,faces,mat,group='vista')

def sigil(pos,h=1,mat='ivory'):
 x,y,z=pos
 for i in range(3):box('Reach horizon',(x+i*h*.15,y,z+i*h*.25),(h*(.9-i*.2),.018,h*.07),mat,0)
 box('Reach rising stem',(x+h*.45,y-.012,z+h*.26),(h*.07,.018,h*.7),mat,0)

def rail(a,b,height=1.0):
 a,b=Vector(a),Vector(b);n=max(1,int((b-a).length/1.7))
 d=b-a;side=Vector((-d.y,d.x,0));side.normalize();side*=.065;upv=Vector((0,0,height))
 verts=[a-side,a+side,b+side,b-side,a-side+upv,a+side+upv,b+side+upv,b-side+upv]
 me=bpy.data.meshes.new('Guard collision');me.from_pydata(verts,[],[(0,3,2,1),(0,1,5,4),(1,2,6,5),(2,3,7,6),(3,0,4,7),(4,5,6,7)]);o=bpy.data.objects.new('Guard collision',me);bpy.context.collection.objects.link(o);o.hide_render=True;WALK.append(o)
 for i in range(n+1):
  p=a+(b-a)*(i/n);rod('Guardrail post',p,p+Vector((0,0,height)),.045)
 for z in [height*.5,height]:rod('Guardrail run',a+Vector((0,0,z)),b+Vector((0,0,z)),.04)

def slab(name,x0,x1,y0,y1,z,mat='stone'):
 o=box(name,((x0+x1)/2,(y0+y1)/2,z-.16),(x1-x0,y1-y0,.32),mat,.015);WALK.append(o)
 return o

def ramp(name,x0,x1,y0,y1,z0,z1,steps=0,mat='concrete',stairs_side='right'):
 faces=[(0,1,2,3),(7,6,5,4),(0,4,5,1),(1,5,6,2),(2,6,7,3),(3,7,4,0)]
 if y1<y0:faces=[tuple(reversed(f)) for f in faces]
 # Exact sloped walking/collision surface. Visible stairs flank a broad ramp.
 o=mesh(name,[(x0,y0,z0),(x1,y0,z0),(x1,y1,z1),(x0,y1,z1),(x0,y0,z0-.25),(x1,y0,z0-.25),(x1,y1,z1-.25),(x0,y1,z1-.25)],faces,mat,True)
 if steps:
  # Continuous collision bed lets core walk the visible steps without a step-up feature.
  xa,xb=(x0-1.7,x0) if stairs_side=='left' else (x1,x1+1.7)
  mesh(name+' stair bed',[(xa,y0,z0),(xb,y0,z0),(xb,y1,z1),(xa,y1,z1),(xa,y0,z0-.3),(xb,y0,z0-.3),(xb,y1,z1-.3),(xa,y1,z1-.3)],faces,mat,True)
  STAIR_ROUTES.append({'id':name.lower().replace(' ','-'),'from':up(((xa+xb)/2,y0,z0)),'to':up(((xa+xb)/2,y1,z1)),'width':1.65})
  for i in range(steps):
   t=(i+1)/steps if z1>=z0 else i/steps;y=y0+(y1-y0)*(i+.5)/steps;z=z0+(z1-z0)*t
   box(name+' stair tread',((xa+xb)/2,y,z-.1),(1.65,abs(y1-y0)/steps,.2),mat,.008)
 left=x0-1.7 if steps and stairs_side=='left' else x0;right=x1 if stairs_side=='left' else x1+1.7
 # Half-meter openings at each landing keep lateral walking approaches clear.
 t=.5/abs(y1-y0)
 for x in [left,right]:rail((x,y0+(y1-y0)*t,z0+(z1-z0)*t),(x,y1-(y1-y0)*t,z1-(z1-z0)*t))
 return o

def point(name,pos,previous=None,width=3):
 ROUTES.append({'id':name,'position':up(pos),'waypoint':name in LANDMARKS,**({'label':LANDMARKS[name]} if name in LANDMARKS else {})})
 if previous:EDGES.append({'from':previous,'to':name,'width':width})
 return name

def up(v):return [round(float(v[0]),5),round(float(v[2]),5),round(float(-v[1]),5)]
def quat(q):
 # Convert the authored local screen axes into glTF world coordinates.
 c=Matrix.Rotation(-math.pi/2,4,'X').to_quaternion();r=c@q;return [r.x,r.y,r.z,r.w]

def owner():return G,AREAS[-1]['workspaceSlot']
def anchor_id(kind):
 area,slot=owner();key=(area,kind);COUNT[key]=COUNT.get(key,0)+1;return f'{area}-slot-{slot}-{kind}-{COUNT[key]:02d}'

def screen(kind,pos,size,role='tool',tilt=0,style='instrument',yaw=0):
 # Screen local X is horizontal, Y is height, Z points into clear floor (-Y).
 ident=anchor_id(kind);w,h=size;q=(Matrix.Rotation(yaw,4,'Z')@Matrix.Rotation(math.pi/2-tilt,4,'X')).to_quaternion();r=q.to_matrix();center=Vector(pos)
 def panel(name,local,size,mat,group=None):
  o=box(name,center+r@Vector(local),size,mat,.025,group=group);o.rotation_mode='QUATERNION';o.rotation_quaternion=q;return o
 panel(ident+' casing',(0,0,-.13),(w+.42,h+.42,.26),'metal')
 panel(ident+' inset',(0,0,-.012),(w+.10,h+.10,.025),'black')
 for x in [-w/2-.14,w/2+.14]:panel(ident+' frame',(x,0,.012),(.11,h+.4,.08),'trim')
 for y in [-h/2-.14,h/2+.14]:panel(ident+' frame',(0,y,.012),(w+.4,.11,.08),'trim')
 panel(ident+' light',(0,h/2+.14,.08),(w,.026,.024),'amber')
 # Mechanical bezel details stay behind the usable screen plane.
 for x in [-w/2-.15,w/2+.15]:
  for y in [-h/2-.15,h/2+.15]:panel(ident+' captive fastener',(x,y,.041),(.055,.055,.028),'ivory')
 for x in [-w*.3,-w*.1,w*.1,w*.3]:panel(ident+' bezel cooling slot',(x,-h/2-.14,.039),(w*.105,.025,.016),'black')
 # Static original UI plane uses its own UV rectangle and unlit material.
 verts=[tuple(center+r@Vector(v)) for v in [(-w/2,-h/2,.025),(w/2,-h/2,.025),(w/2,h/2,.025),(-w/2,h/2,.025)]]
 o=mesh(ident+' placeholder',verts,[(0,1,2,3)],'ui-'+NAMES[AREA]+'-'+style,group='vista')
 uv=o.data.uv_layers[0]
 for i,v in enumerate([(0,0),(1,0),(1,1),(0,1)]):uv.data[i].uv=v
 ANCHORS.append({'id':ident,'pose':{'position':up(center+r@Vector((0,0,.055))),'rotation':quat(q)},'size':[w,h],'screenType':'com.hyprune.window'})
 area,slot=owner();MOUNT_ROWS.append({'anchorId':ident,'areaId':area,'workspaceSlot':slot,'mountType':kind,'role':role,'clearanceMeters':16 if role=='mounted-workspace' else 4})
 return ident

def data(kind,pos,node=None):
 ident=anchor_id(kind);area,slot=owner();OBJECTS.append({'id':ident,'pose':{'position':up(pos),'rotation':[0,0,0,1]},'areaId':area,'workspaceSlot':slot,'mountType':kind})
 return ident

def crate(pos,size=(1.4,1,.8)):
 x,y,z=pos;w,d,h=size;box('Archive case',(x,y,z+h/2),(w,d,h),'metal',.08,solid=True)
 for dx in [-w*.43,w*.43]:box('Case corner',(x+dx,y,z+h/2),(.09,d+.05,h+.06),'strip')
 for dz in [z+.09,z+h-.09]:box('Case band',(x,y-d/2-.018,dz),(w+.03,.04,.055),'ivory')
 box('Case lid',(x,y,z+h+.045),(w+.02,d+.02,.075),'frost',.012)
 for dx in [-w*.28,w*.28]:
  box('Case reinforcing rib',(x+dx,y-d/2-.036,z+h*.46),(.045,.07,h*.55),'metal',0)
 for dx in [-w*.30,w*.30]:box('Case grip',(x+dx,y-d/2-.072,z+h*.82),(.21,.08,.055),'ivory',0)
 box('Case badge backing',(x,y-d/2-.014,z+h*.54),(h*.65,.05,h*.5),'frost',.003)
 box('Case latch',(x,y-d/2-.05,z+h*.65),(.18,.055,.15),'metal');sigil((x,y-d/2-.047,z+h*.45),h*.45);data('crate',(x,y,z+h/2))

def lamp(pos,height=2.8):
 x,y,z=pos;cyl('Lamp foot',(x,y,z+.12),.18,.24);cyl('Lamp mast',(x,y,z+height/2),.055,height)
 box('Lamp hood',(x,y,z+height),(.36,.36,.11),'metal');cyl('Lamp diffuser',(x,y,z+height-.24),.10,.32,'amber');P.area('Warm lamp',(x,y,z+height-.16),(x,y,z),65,(1,.46,.15),.6)

def tree(x,y,z=0,scale=1):
 rng=random.Random(int((x+y)*137));box('Terrace planter',(x,y,z+.36),(2.6*scale,2.3*scale,.72),'concrete',.08,solid=True);box('Planter earth',(x,y,z+.75),(2.3*scale,2*scale,.04),'earth',.0)
 rod('Tree trunk',(x,y,z+.75),(x+.14*scale,y,z+4.4*scale),.1*scale,'wood')
 for i in range(9):
  ang=i*2.4;rr=scale*(.4+rng.random());start=(x,y,z+(2.1+i*.19)*scale);end=(x+math.cos(ang)*rr,y+math.sin(ang)*rr,z+(3.0+i*.19)*scale);rod('Tree branch',start,end,.035*scale,'wood')
  # Many small angular leaf clusters avoid an unconvincing solid topiary ball.
  for j in range(8):
   p=Vector(end)+Vector((rng.uniform(-.65,.65),rng.uniform(-.65,.65),rng.uniform(-.35,.5)))*scale
   verts=[];faces=[]
   for k in range(12):
    c=p+Vector((rng.uniform(-.25,.25),rng.uniform(-.25,.25),rng.uniform(-.13,.13)))*scale;rr=rng.uniform(.095,.235)*scale;a=rng.random()*math.tau;u=Vector((math.cos(a)*rr,math.sin(a)*rr,rr*.35));v=Vector((-math.sin(a)*rr*.5,math.cos(a)*rr*.5,rr*.05));n=len(verts);verts.extend([c-u,c+v,c+u,c-v]);faces.append((n,n+1,n+2,n+3))
   mesh('Red canopy leaves',verts,faces,'leaf-gold' if j%5==0 else 'leaf',group='foliage')


def banner(x,y,z,h=4):
 box('Canvas standard',(x,y,z),(1.25,.055,h),'red');sigil((x,y-.035,z+.2),.75)
 rod('Banner standard mast',(x-.75,y,BASE),(x-.75,y,z+h/2+.35),.045)
 rod('Banner suspension',(x-.75,y,z+h/2+.15),(x+.75,y,z+h/2+.15),.06)

def canopy(x,y,z,w=6,d=5,base=None):
 if base is None:base=BASE
 for dx in [-w/2,w/2]:
  for dy in [-d/2,d/2]:rod('Shelter mast',(x+dx,y+dy,base),(x+dx,y+dy,z+.3),.06)
 # Sagged original canvas panels, opaque by design.
 verts=[(x-w/2,y-d/2,z+.2),(x+w/2,y-d/2,z+.2),(x-w/2,y,z-.12),(x+w/2,y,z-.12),(x-w/2,y+d/2,z+.2),(x+w/2,y+d/2,z+.2)]
 mesh('Canvas canopy',verts,[(0,1,3,2),(2,3,5,4)],'canvas')
 for dx in [-w/2,w/2]:rod('Shelter beam',(x+dx,y-d/2,z+.2),(x+dx,y+d/2,z+.2),.065)


def globe(pos,r=1.8):
 x,y,z=pos;cyl('Globe plinth',(x,y,z+.25),r*.75,.5,'concrete');cyl('Globe pedestal',(x,y,z+.8),.28,1.0,'metal')
 center=(x,y,z+1.9+r*.6)
 bpy.ops.mesh.primitive_ico_sphere_add(subdivisions=2,radius=r*.9,location=center);o=bpy.context.object;P.add(o,'Instrument globe','black',G)
 edges=set()
 for face in o.data.polygons:
  ids=list(face.vertices)
  for a,b in zip(ids,ids[1:]+ids[:1]):edges.add(tuple(sorted((a,b))))
 for a,b in edges:rod('Globe network',o.matrix_world@o.data.vertices[a].co,o.matrix_world@o.data.vertices[b].co,.012,'cyan')
 for i,rot in enumerate([(0,.45,0),(.8,0,.5),(1.2,.35,0)]):torus('Armillary orbit',center,r*(1.05+i*.07),.035,'ivory',rot)
 data('globe',center)


def set_area(i,bounds,spawn,free,area_id=None,title=None,slot=None):
 global AREA,G,BASE
 AREA=i;G=area_id or NAMES[i];BASE=spawn[2];slot=slot or f'{i+1:02d}'
 assert not any(a['id']==G or a['workspaceSlot']==slot for a in AREAS),'home IDs and slots must be unique'
 AREAS.append({'id':G,'name':title or TITLES[i].title(),'workspaceSlot':slot,'theme':NAMES[i],'primaryAnchor':None,'toolAnchors':[],'dataAnchors':[],'bounds':{'min':up((bounds[0],bounds[3],bounds[4])),'max':up((bounds[1],bounds[2],bounds[5]))},'spawn':spawn,'freePlacementZones':[{'id':G+'-open-work','bounds':{'min':up((free[0],free[3],free[4])),'max':up((free[1],free[2],free[5]))},'windowSizes':[[1.6,.9],[3.2,1.8]],'clearance':.15}]})


def court():
 set_area(0,(-36,26,-16,26,-.4,18),(-8,-12,0),(-2,7,-8,0,.15,4.8))
 slab('Court paving',-24,26,-16,26,0)
 # Facade is a structure with a real central entrance under its giant wall.
 for x,w in [(-4,8),(19,10)]:box('Facade pier',(x,24,3),(w,1.5,6),'concrete',.045,solid=True)
 box('Facade lintel',(8,24,11),(32,1.5,10),'concrete',.045,solid=True)
 screen('facade-wall',(8,23.17,10.1),(18.8,9.3),'mounted-workspace',style='workspace')
 label('01 SUN COURT',(8,22.92,15.65),.46)
 label('ARRAY HALL',(8,23.12,3.35),.35)
 for x in [2.8,13.2]:
  # Supported jamb from paving to canopy, with the lens seated into its backplate.
  box('Entry fixture jamb',(x,23.25,2.2),(.24,.30,4.4),'metal',.015,solid=True)
  box('Entry light backplate',(x,23.085,1.55),(.15,.08,2.85),'metal',.008)
  box('Entry light',(x,23.038,1.55),(.075,.03,2.7),'amber',.004)
 # Layered facade ribs, worn service panels and warm physical entry detailing.
 for x in [-5.6,-3.6,20.8,23.0]:
  for z in [6.5,9.5,12.5]:
   box('Facade maintenance plate',(x,23.145,z),(1.45,.22,2.25),'concrete',.025)
   for dx in [-.58,.58]:
    for dz in [-.9,.9]:box('Plate captive fixing',(x+dx,23.008,z+dz),(.055,.06,.055),'metal',0)
  box('Facade service drain',(x,22.96,1.0),(.15,.12,1.5),'metal')

 for x in [-7,-5,-3,21,24]:
  box('Facade vertical rib',(x,23.12,9.2),(.16,.26,13.1),'concrete',.015)
  box('Rib metal foot',(x,22.93,.5),(.38,.25,1),'metal')
 for z in [5.3,15.4]:box('Facade horizontal seam',(8,22.99,z),(29,.09,.055),'metal',0)
 for x in [0.4,15.6]:
  box('Entry pier',(x,22.83,2.45),(.64,.65,4.9),'concrete',solid=True)
  box('Entry pier practical',(x,22.47,2.2),(.10,.08,3.1),'amber')
 box('Entry canopy',(8,22.0,4.6),(16,3,.36),'metal',.04,solid=True)
 box('Entry ceiling light',(8,22.0,4.39),(13,.16,.035),'amber')
 slab('Entry vestibule',0,16,26,32,0,'stone')
 for x in [0,16]:box('Vestibule side',(x,28,2.2),(.35,8,4.4),'concrete',solid=True)
 box('Vestibule ceiling',(8,28,4.5),(16,8,.22),'concrete')
 P.area('Entry warm pool',(8,27,4.1),(8,27,0),650,(1,.62,.27),7)
 # Upper roof is reached by the western terrace ramp, then bridge.
 slab('Facade rooftop',-7,25,22,27,16,'concrete');rail((-7,22,16),(25,22,16));canopy(17,24.4,19.2,8,4,base=16)
 # Globe terrace and winding rails sit off the command wall's clear approach.
 slab('Instrument terrace',-13,-2,6,15,1.2,'concrete');ramp('Globe approach',-8,-4,0,6,0,1.2,8)
 globe((-7,10,1.2));tree(-12,12,1.2,.8);lamp((-3,14,1.2))
 # Real west terrace to roof: walkable switchback ramps, stairs beside each.
 slab('West lookout',-24,-16,6,20,4,'concrete');ramp('Lookout ascent',-23,-20,-10,6,0,4,20)
 slab('Upper landing',-24,-16,20,24,4,'concrete');ramp('Roof ascent lower',-23,-20,24,40,4,8,20)
 slab('Roof landing',-24,-16,40,44,8,'concrete');ramp('Roof ascent upper',-18,-15,40,24,8,12,20)
 slab('Roof upper landing',-20,-7.3,20,24,12,'concrete');ramp('Roof final approach',-13.2,-10.2,20,36,12,16,20)
 slab('Rooftop bridge',-13.2,-3,36,37.5,16,'concrete');slab('Rooftop bridge run',-7,-3,22,36,16,'concrete');rail((-7,22,16),(-7,35.5,16))
 slab('Cascade expansion bridge',-34,-24,12,16,4,'concrete');rail((-34,12,4),(-24,12,4));rail((-34,16,4),(-24,16,4))
 box('Cascade route gate',(-34,14,5),( .18,4,2),'metal',solid=True);box('Bridge route plaque',(-32,12.0,4.96),(1.2,.10,1.1),'metal',.008);sigil((-32,11.935,4.8),.7);label('UPPER CASCADE',(-28,11.93,5.25),.23)
 rail((-24,6,4),(-24,12,4));rail((-24,16,4),(-24,24,4));banner(-19,9,7,3.5);tree(-20,17,4,.8)
 # Raised annex has substantial supports, so its walkable route reads as architecture.
 for x,y,z in [(-23,10,4),(-23,25,4),(-23,39,8),(-16,23,12),(-20.2,33,16)]:
  box('Annex pier',(x,y,z/2-.3),(.75,.85,z+.6),'concrete',.04,solid=True)
 for y in [8,13,18]:box('Lookout light',(-23.85,y,4.15),(.06,.55,.08),'amber')
 # Field shelter foreground deliberately crops into the arrival composition.
 canopy(-16,-5,5.0,10,10)
 box('Field workbench',(-15,-7.7,1),(4,1.2,.17),'wood',.05,solid=True)
 for x in [-16.5,-13.5]:box('Workbench leg',(x,-7.7,.5),(.1,.8,1),'metal',solid=True)
 screen('operator-desk',(-15,-7.5,1.95),(2.6,1.45),tilt=.20)
 canopy(22,-8,4.4,6,6)
 box('Service bench',(22,-8,1),(3.8,1,.16),'wood',.04,solid=True)
 screen('operator-desk',(22,-7.9,1.95),(2.5,1.4),tilt=.20)
 # Higher rig is at the back of the shelter, leaving 4m approach clear.
 for x in [-16.5,-13.3]:
  rod('Rig upright',(x,0,0),(x,0,3.9),.065);screen('field-rig',(x,-.04,2.9),(2.4,1.35),tilt=.04)
 rod('Rig crossbar',(-17.8,0,3.8),(-11.8,0,3.8),.07)
 for p in [(-19,-2,0),(-19,-2,.85),(-21,-6,0),(-21,-4.8,0),(-22,1,0),(23,14,0)]:crate(p)
 for x,y in [(19,-6),(21,3),(19,16),(-23,-14),(-2,19)]:tree(x,y,0,.85)
 for x,y in [(-13,3),(13,-3),(22,9),(-1,17),(22,20)]:lamp((x,y,0))
 box('Kiosk base',(17,5,.6),(1.8,1.0,1.2),'concrete',.09,solid=True);screen('kiosk-pillar',(17,4.8,2.2),(1.6,2.0),tilt=.08)
 banner(24,20,10,6);banner(-4,24,10,6)
 slab('Lookout seat terrace',-16,-13,16,20,4,'concrete')
 # Seats and perimeter ledges give the court scale while preserving work pockets.
 for x,y in [(20,12),(-16,17)]:
  box('Court seat',(x,y,.53 if x>0 else 4.53),(3.4,.8,.16),'wood',.04,solid=True)
  for dx in [-1.35,1.35]:box('Seat support',(x+dx,y,.25 if x>0 else 4.25),(.25,.7,.5),'metal',solid=True)
 rail((-24,-16,0),(26,-16,0));rail((26,-16,0),(26,22,0))
 # Original bent paving rails. Travel route stays on generous open floor.
 for offset in [-.52,.52]:
  pts=[(7+offset,-16,.015),(7+offset,-2,.015),(5+offset,3,.015),(1+offset,7,.015),(-1+offset,15,.015),(6+offset,20,.015),(8+offset,24,.015)]
  for a,b in zip(pts,pts[1:]):rod('Inset route rail',a,b,.023,'metal');rod('Rail warm edge',(a[0]+.045,a[1],.018),(b[0]+.045,b[1],.018),.008,'amber')
 for y in [-12,-8,-4,1,5,18,21]:box('Paving expansion seam',(3,y,.01),(37,.025,.012),'metal',0)
 point('arrival',(-8,-12,0));point('court-junction',(1,2,0),'arrival');point('court-wall',(8,12,0),'court-junction');point('hall-entry',(8,25,0),'court-wall')
 point('globe-road',(1,-2,0),'court-junction');point('globe-approach',(-6,-2,0),'globe-road');point('globe-ramp',(-6,0,0),'globe-approach');point('globe-terrace',(-6,6,1.2),'globe-ramp');point('globe-platform',(-6,7,1.2),'globe-terrace')
 point('lookout-south',(-8,-14.5,0),'arrival');point('lookout-west',(-21.5,-14.5,0),'lookout-south');point('lookout-base',(-21.5,-10,0),'lookout-west');point('lookout',(-21.5,6,4),'lookout-base');point('cascade-turn',(-21.5,14,4),'lookout');point('cascade-bridge',(-31,14,4),'cascade-turn');point('roof-lower',(-21.5,24,4),'lookout');point('roof-switchback',(-21.5,40,8),'roof-lower');point('roof-turn',(-16.5,42,8),'roof-switchback');point('roof-return',(-16.5,40,8),'roof-turn');point('roof-upper',(-16.5,24,12),'roof-return');point('roof-start-west',(-16.5,20,12),'roof-upper');point('roof-start',(-11.7,20,12),'roof-start-west');point('roof-final',(-11.7,36,16),'roof-start');point('roof-bridge',(-5,36,16),'roof-final');point('rooftop',(-5,24,16),'roof-bridge')
 VIEWS.extend([{'id':'01-sun-court','position':[-13,-13,1.9],'target':[4,23,7]},{'id':'01-sun-court-terrace','position':[-21,15,5.7],'target':[4,12,8]}])


def hall():
 set_area(1,(-13,27,32,62,-.4,23),(8,34,0),(3,12,34,40,.15,4.8))
 slab('Atrium stone floor',-6,24,32,60,0)
 slab('Service threshold',24,33,48,52,0,'metal')
 # Tall ribs and a heavy roof ring frame a generous, daylight-filled volume.
 for x in [-6,24]:
  for y in [33,44,58]:
   box('Atrium column',(x,y,10.5),(1.0,1.15,21),'concrete',.04,solid=True)
   box('Column inset',(x+( .56 if x<0 else -.56),y,8),(.06,.4,15),'metal')
   box('Column light',(x+( .60 if x<0 else -.60),y-.24,8),(.055,.10,14),'amber')
 for y in [32,60]:box('Roof transverse beam',(9,y,21),(31,1.1,1.2),'concrete',solid=True)
 for x in [-6,24]:box('Roof edge beam',(x,46,21),(1.1,28,1.2),'concrete',solid=True)
 for x in [-4,4,12,20]:box('Skylight mullion',(x,46,21.35),(.18,28,.18),'metal')
 torus('Atrium suspended light ring',(8,46,19.8),8.5,.065,'amber')
 for x in [-3,19]:rod('Light ring hanger',(x,46,20),(x,46,21.4),.025)
 # Opaque window panes only at the small upper skylight. The rear is an open vista.
 for x in [-.0,8,16]:box('Skylight pane',(x,46,21.50),(7.7,27,.08),'glass')
 for x in [-6,24]:
  spans=[(42,56)] if x<0 else [(32,48),(56,60)]
  for ya,yb in spans:box('Service wall',(x,(ya+yb)/2,9.5),(.5,yb-ya,19),'concrete',solid=True)
 # Balcony portal remains open at both ground and first floor.
 box('West portal sill',(-6,58,1.3),(.4,4,2.6),'concrete',solid=True)
 box('West portal crown',(-6,58,13),(.4,4,12),'concrete',solid=True)
 for x in [-6,-2,2,6,10,14,18,22,24]:rod('Panorama mullion',(x,60,0),(x,60,20.6),.06)
 box('Panorama parapet',(9,60,.5),(30,.35,1),'concrete',solid=True)
 # The main wall hangs above the travel floor, rather than turning the hall into a corridor.
 screen('hanging-wall',(8,48,10),(16,8),'mounted-workspace',style='workspace')
 for x in [.6,15.4]:rod('Workspace suspension',(x,48.3,14.17),(x,48.3,20.8),.09)
 label('02 ARRAY HALL',(8,47.67,15.2),.42)
 banner(-3,43.65,11,3.5)
 for x in [-1,18]:
  cyl('Lectern base',(x,40,.14),.55,.28,'metal')
  box('Lectern stem',(x,40,.62),(.32,.36,1.2),'metal',solid=True)
  screen('lectern',(x,39.85,1.95),(1.8,1.1),tilt=.38)
 screen('banner',(-8,38,6.6),(1.55,4.2),style='banner')
 screen('banner',(21,44,6.6),(1.55,4.2),style='banner')
 for x,y in [(-8,38),(21,44)]:rod('Banner mast',(x,y+.2,0),(x,y+.2,9.4),.055)
 for x in [-2,8,18]:
  box('Rear operator bench',(x,52.8,1),(3.8,1.1,.18),'wood',solid=True)
  for dx in [-1.5,1.5]:box('Rear bench leg',(x+dx,52.8,.5),(.12,.8,1),'metal',solid=True)
  screen('operator-desk',(x,53,1.95),(2.55,1.4),tilt=.20,yaw=math.pi)
 # Rack bays are recessed behind the piers, with amber local task pools.
 for x in [-5.45,23.45]:
  for y in [44,47,57]:
   box('Archive rack',(x,y,2.5),(.5,1.7,5),'metal',solid=True)
   for z in [.7,1.4,2.1,2.8,3.5,4.2]:
    box('Rack cooling slot',(x+( .28 if x<0 else -.28),y,z),(.03,1.5,.13),'black')
    box('Rack status strip',(x+( .30 if x<0 else -.30),y-.55,z+.18),(.03,.22,.055),'cyan')
 for x in [-4,22]:
  for ya,yb in [(33,46),(49,59)]:box('Floor guide strip',(x,(ya+yb)/2,.025),(.10,yb-ya,.035),'amber',0)
 for x in [-3,19]:crate((x,59,0))
 # A proper exterior stair/ramp annex leads into the overlooking balconies.
 slab('Hall ramp annex',-13,-6,32,60,0,'concrete')
 ramp('Hall balcony ascent',-12,-9,40,56,0,4,20)
 slab('Hall balcony landing',-13,-2,56,60,4,'concrete')
 slab('Hall first balcony',-6,-2,48,60,4,'concrete')
 ramp('Hall upper ascent',-5,-2,56,40,4,8,20)
 slab('Hall upper balcony',-6,0,32,40,8,'concrete')
 # Upper landing stops at the ramp crest; no slab crosses its rising clearance.
 rail((-.2,32,8),(-.2,39,8));rail((-2,57,4),(-2,60,4))
 for y in [32.5,58]:box('Hall balcony support',(-11,y,1.8),(.8,.8,3.6),'concrete',solid=True)
 P.area('Hall warm skylight',(4,42,19),(8,46,0),9000,(1,.63,.30),12)
 P.area('Hall warm window',(12,59,14),(8,45,3),6500,(1,.73,.43),9)
 for x in [-4,22]:P.area('Hall service pool',(x,45,8),(x,45,0),650,(1,.40,.13),3)
 label('RIME VAULT',(23.7,49,4),.24)
 point('hall-arrival',(8,33,0),'hall-entry');point('hall-center',(8,46,0),'hall-arrival');point('hall-exit',(20,50,0),'hall-center');point('service-entry',(30,50,0),'hall-exit')
 point('hall-annex-entry',(-10.5,36,0),'hall-arrival');point('hall-ramp-base',(-10.5,40,0),'hall-annex-entry');point('hall-balcony',(-10.5,56,4),'hall-ramp-base');point('hall-balcony-turn',(-10.5,59.2,4),'hall-balcony');point('hall-upper-door',(-3.5,59.2,4),'hall-balcony-turn');point('hall-upper-base',(-3.5,56,4),'hall-upper-door');point('hall-upper',(-3.5,40,8),'hall-upper-base')
 for off in [-.5,.5]:
  pts=[(8+off,32,.015),(8+off,46,.015),(20+off,50,.015),(27+off,52,.015)]
  for a,b in zip(pts,pts[1:]):rod('Hall inset route rail',a,b,.022,'metal')


def steam(pos,scale=1):
 # Original generated alpha art, supported by core M2. Two crossed vent cards.
 x,y,z=pos;w=1.4*scale;h=2.2*scale
 for angle in [0,math.pi/2]:
  dx=math.cos(angle)*w/2;dy=math.sin(angle)*w/2
  o=mesh('Soft vent steam',[(x-dx,y-dy,z),(x+dx,y+dy,z),(x+dx,y+dy,z+h),(x-dx,y-dy,z+h)],[(0,1,2,3)],'steam-card',group='vista')
  for i,v in enumerate([(0,0),(1,0),(1,1),(0,1)]):o.data.uv_layers[0].data[i].uv=v


def vault():
 set_area(2,(26,55,52,103,-6.4,5),(38,79,-6),(36,42,77,83,-5.85,-1.2))
 ramp('Service descent',27,33,52,74,0,-6,30,'grating')
 # Enclosed passage is for travel; its lower door opens onto a broad work floor.
 for x in [26.5,35.1]:box('Descent side',(x,63,-.5),(.5,22,13),'metal',solid=True)
 mesh('Sloping service roof',[(26.3,52,5),(35.4,52,5),(35.4,74,-1),(26.3,74,-1)],[(0,1,2,3)],'metal',True)
 for y in range(54,77,4):
  z=-(y-52)/4
  box('Descent red edge',(26.85,min(y,73.85),z+1),(.06,.45,.12),'red-light')
  box('Descent amber edge',(34.8,min(y,73.7),z+.3),(.06,.5,.13),'amber')
  rod('Service conduit',(34.7,y-1,z+3.7),(34.7,y+1,z+3.2),.09,'frost')
 P.area('Descent lower pool',(30,72,.7),(30,76,-6),320,(.32,.55,1),3)
 slab('Vault lower floor',26,50,74,102,-6,'metal')
 slab('Vault exit sill',50,56,96,103,-6,'grating')
 box('Lower passage east shell',(56,99.5,-2.5),(.4,7,7),'metal',solid=True)
 box('Lower passage south shell',(53,96,-2.5),(6,.4,7),'metal',solid=True)
 box('Lower passage roof',(53,99.5,1.2),(6,7,.3),'metal',solid=True)
 if BUILD_AREAS<4:box('Next home temporary gate',(53,103,-2.5),(6,.4,7),'metal',solid=True)
 for x in [26,50]:
  spans=[(76,102)] if x<30 else [(76,96)]
  for ya,yb in spans:box('Vault side shell',(x,(ya+yb)/2,-1),(.6,yb-ya,10),'metal',solid=True)
 box('Vault exit crown',(50,99,2.1),(.6,6,4.2),'metal',solid=True)
 box('Vault rear shell',(38,102,-1),(24,.65,10),'metal',solid=True)
 box('Vault ceiling',(38,89,4.2),(24,26,.45),'metal',solid=True)
 for x in [26.5,49.5]:
  for y in [78,87,96,101]:
   box('Vault frost rib',(x,y,-1),(.55,.4,9.5),'frost',solid=True)
   box('Vault red practical',(x+( .30 if x<30 else -.30),y,-2.4),(.04,.14,1.4),'red-light')
 for x in [29,33,43,47]:
  rod('Ceiling coolant pipe',(x,77,3.65),(x,101,3.65),.19,'frost')
  for y in [80,86,92,98]:cyl('Coolant flange',(x,y,3.65),.25,.12,'metal').rotation_euler=(math.pi/2,0,0)
 for y in [80,86,92,98]:
  rod('Vault cable tray',(27,y,3.55),(49,y,3.55),.055)
  box('Ceiling amber bar',(38,y,3.9),(5,.12,.05),'amber')
 # Main console is visibly recessed into a heavy service frame.
 box('Console backing',(39,100,-.5),(16,1.1,8.7),'frost',solid=True)
 screen('wall-inset-console',(39,99.37,-.1),(13.8,6.3),'mounted-workspace',style='workspace')
 label('03 RIME VAULT',(39,99.03,3.45),.32)
 for x in [31,47]:box('Console amber side',(x,99.20,-.8),(.08,.06,6.9),'amber')
 for x,y in [(33.6,81),(45,82)]:
  box('Vault instrument desk',(x,y,-5),(3.8,1.15,.17),'metal',solid=True)
  for dx in [-1.5,1.5]:box('Vault desk support',(x+dx,y,-5.5),(.16,.85,1),'frost',solid=True)
  screen('operator-desk',(x,y-.12,-4.02),(2.55,1.4),tilt=.20)
 screen('wall-inset-console',(49.35,94,-1.4),(3.0,2.0),yaw=-math.pi/2)
 ramp('Vault maintenance ascent',27,30,76,92,-6,-2,20,'grating')
 slab('Vault maintenance platform',26.4,32,92,98,-2,'grating')
 rail((32,93,-2),(32,98,-2));rail((26.5,92,-2),(26.5,98,-2))
 box('Maintenance terminal plinth',(28.5,96,-1.0),(3.6,1,.16),'metal',solid=True)
 screen('terminal-bench',(28.5,95.85,-.02),(2.3,1.3),tilt=.22)
 # Separate sealed continuation hints at a larger settlement.
 box('Sealed lower gate',(28,100,-3),(3,.65,6),'frost',solid=True)
 box('Gate center split',(28,99.63,-3),(.06,.06,5.4),'black')
 label('SEALED',(28,99.58,-1.8),.25);label('CONTINUATION',(28,99.58,-2.3),.16)
 for x in [26.8,29.2]:box('Gate red edge',(x,99.62,-3),(.04,.045,4),'red-light')
 for x,y in [(47,80),(47,100),(34,96)]:crate((x,y,-6))
 box('Steam vent',(47,91,-5.5),(1,.6,.5),'frost',solid=True);steam((47,91,-5.2),1.3)
 for x in [32.5,43.5]:box('Vault floor strip',(x,88,-5.97),(.08,22,.035),'amber',0)
 P.area('Vault cold ceiling',(38,83,3.4),(38,88,-5),750,(.18,.38,.7),8)
 P.area('Vault red service',(27,94,1),(32,93,-4),430,(1,.045,.018),4)
 P.area('Vault amber console',(38,97,3.4),(38,94,-5),600,(1,.33,.07),7)
 point('descent-top',(30,52,0),'service-entry');point('descent-bottom',(30,74,-6),'descent-top');point('vault-door',(32,74,-6),'descent-bottom');point('vault-arrival',(38,79,-6),'vault-door');point('vault-center',(38,89,-6),'vault-arrival');point('vault-exit',(48,98,-6),'vault-center');point('rise-entry',(54,100,-6),'vault-exit')
 point('vault-maintenance-base',(28.5,76,-6),'vault-door');point('vault-maintenance',(28.5,92,-2),'vault-maintenance-base');point('vault-platform',(28.5,94,-2),'vault-maintenance')
 for off in [-.45,.45]:
  for a,b in zip([(38+off,78,-5.975),(38+off,89,-5.975),(48+off,98,-5.975)],[(38+off,89,-5.975),(48+off,98,-5.975),(54+off,100,-5.975)]):rod('Vault inset route rail',a,b,.018,'metal')


def dish(pos,r=5):
 x,y,z=pos;q=Matrix.Rotation(1.15,4,'X').to_3x3();verts=[Vector(pos)];faces=[]
 for ring in range(1,13):
  rr=r*ring/12
  for j in range(48):
   ang=j*math.tau/48;verts.append(Vector(pos)+q@Vector((rr*math.cos(ang),rr*math.sin(ang),.11*rr*rr)))
 for j in range(48):faces.append((0,1+j,1+(j+1)%48))
 for ring in range(1,12):
  a=1+(ring-1)*48;b=1+ring*48
  for j in range(48):k=(j+1)%48;faces.append((a+j,b+j,b+k,a+k))
 mesh('Parabolic link dish',verts,faces,'concrete')
 for j in range(16):
  ang=j*math.tau/16;points=[]
  for k in range(1,9):
   rr=r*k/8;points.append(Vector(pos)+q@Vector((rr*math.cos(ang),rr*math.sin(ang),.11*rr*rr+.045)))
  for a,b in zip(points,points[1:]):rod('Reflector panel seam',a,b,.027,'metal')
 rim=[]
 for j in range(48):
  ang=j*math.tau/48;rim.append(Vector(pos)+q@Vector((r*math.cos(ang),r*math.sin(ang),.11*r*r)))
 for a,b in zip(rim,rim[1:]+rim[:1]):rod('Dish rim',a,b,.06,'metal')
 for j in range(16):
  ang=j*math.tau/16;points=[]
  for k in range(9):
   rr=r*k/8;points.append(Vector(pos)+q@Vector((rr*math.cos(ang),rr*math.sin(ang),.11*rr*rr-.12)))
  for a,b in zip(points,points[1:]):rod('Reflector radial back rib',a,b,.075,'metal')
 # Concentric stiffening hoops are visibly separated from the reflective skin.
 for rr in [r*.42,r*.72]:
  points=[Vector(pos)+q@Vector((rr*math.cos(j*math.tau/48),rr*math.sin(j*math.tau/48),.11*rr*rr-.16)) for j in range(48)]
  for a,b in zip(points,points[1:]+points[:1]):rod('Reflector hoop rib',a,b,.055,'metal')
 focus=Vector(pos)+q@Vector((0,0,3.6))
 for j in [4,20,36]:rod('Dish receiver support',rim[j],focus,.045)
 bpy.ops.mesh.primitive_cone_add(vertices=16,radius1=.36,radius2=.14,depth=.7,location=focus);feed=bpy.context.object;feed.rotation_euler=q.to_euler();P.add(feed,'Link feed horn','ivory',G)
 rod('Feed throat',focus,focus+q@Vector((0,0,.5)),.13,'metal')
 for side in [-1,1]:rod('Dish trunnion',(x+side*1.5,y,z-3.5),(x+side*1.5,y,z-.2),.15,'metal')
 rod('Dish pivot',(x,y,z-4),(x,y,z),.32,'metal')
 data('radar-dish',pos)

def night_vista():
 import any_angle
 any_angle.night(sys.modules[__name__])


def rise():
 set_area(3,(29,85,100,160,-6.4,28),(54,125,0),(52,62,125,130,.15,4.8))
 ramp('Snow service ascent',51,57,100,124,-6,0,30,'grating')
 for x in [50.7,59]:box('Snow ascent shell',(x,112,-1.8),(.5,24,12),'metal',solid=True)
 mesh('Snow ascent ceiling',[(50.4,100,-1),(59.3,100,-1),(59.3,124,5),(50.4,124,5)],[(0,1,2,3)],'metal',True)
 for y in range(102,125,4):
  z=-6+(y-100)*.25
  for x in [51.1,58.5]:box('Ascent amber practical',(x,y,z+1),(.04,.6,.15),'amber')
 P.area('Snow ascent pool',(54,119,2.5),(54,121,-.8),260,(.22,.40,1),3)
 # Preserve an actual hole in the yard paving above the rising tunnel.
 slab('Left snowy terrace',29,50,112,160,0,'snow');slab('Right snowy terrace',60,85,112,160,0,'snow');slab('Central snowy landing',50,60,124,160,0,'snow')
 slab('Landing ring pavement',50,64,125,139,.01,'grating');torus('Arrival landing ring',(57,132,.055),4.8,.025,'amber')
 for ang in [i*math.tau/12 for i in range(12)]:
  x=57+5.3*math.cos(ang);y=132+5.3*math.sin(ang);box('Ring direction tick',(x,y,.06),(.32,.14,.035),'ivory',0)
 # Massive gate facade; entrance is under the mounted workspace wall.
 for x,w in [(54,10),(73.5,13)]:box('Signal fortress pier',(x,148,2.5),(w,1.5,5),'concrete',.07,solid=True)
 box('Fortress gate crown',(64.5,148,12.5),(31,1.5,15),'concrete',solid=True)
 for x in [49,52,74,79]:
  box('Fortress armor rib',(x,146.95,11),(.5,.45,19),'metal',solid=True)
  box('Fortress amber edge',(x+.28,146.65,10),(.07,.06,18),'amber')
 screen('blast-door-screen',(63,147.15,10.7),(18.5,10.4),'mounted-workspace',style='workspace')
 label('04 SIGNAL RISE',(63,146.82,17),.45);box('Fortress identity plate',(78,147.075,18.2),(1.2,.35,1.2),'metal',.004);sigil((78,146.90,18),.7)
 # Outer facility layers are beyond every work floor and walking destination.
 for x,y,w,h in [(36,168,12,24),(85,171,12,30),(91,158,9,15)]:
  box('Signal background service tower',(x,y,h/2),(w,7,h),'concrete',.06)
  for dx in [-w/2+.5,w/2-.5]:
   box('Tower vertical armor',(x+dx,y-3.65,h/2),(.55,.35,h-1),'metal')
   box('Tower amber seam',(x+dx+.30,y-3.85,h/2),(.055,.04,h-2),'amber',0)
  for z in range(3,h,4):
   box('Tower service ledge',(x,y-3.9,z),(w-1,1,.4),'metal')
   box('Tower snow ledge',(x,y-3.9,z+.27),(w-.8,1.1,.14),'snow')
  box('Tower snow crown',(x,y,h+.12),(w+.25,7.3,.24),'snow')
  rod('Tower warning mast',(x,y,h),(x,y,h+3),.055)
  cyl('Tower warning practical',(x,y,h+3),.09,.17,'red-light')
 # Deep segmented service bays, original grille motif and accumulated snow.
 for x in [50.5,76.5]:
  box('Warning grille recess',(x,146.91,12.4),(1.05,.22,7.4),'black')
  for z in [9.2+i*.48 for i in range(14)]:
   box('Warning grille fin',(x,146.74,z),(.86,.16,.11),'metal')
   box('Warning grille light',(x,146.64,z),(.68,.035,.035),'red-light',0)
  for z in [2,6.7,17.4,19.6]:
   box('Service bay armor',(x,147.02,z),(3.0,.30,.56),'metal')
   box('Armor accumulated snow',(x,146.96,z+.36),(3.0,.42,.15),'snow')
 for x in [54,58,68,72]:
  box('Crown plate',(x,147.05,18.5),(3.6,.28,2.0),'metal')
  box('Crown snowy cap',(x,146.99,19.65),(3.6,.44,.16),'snow')
 for x in [57.5,68.5]:
  box('Gate lower armor',(x,146.94,3.4),(2.5,.35,1.6),'metal')
  box('Gate lower snowy cap',(x,146.89,4.28),(2.5,.5,.15),'snow')

 slab('Signal operator room',54,80,146,158,2.4,'grating')
 ramp('Fortress gate approach',60,66,136,146,0,2.4,12,'concrete')
 box('Fortress room roof',(64.5,153,20.2),(31,12,.5),'metal',solid=True)
 box('Fortress rear wall',(64.5,158,10),(31,.6,20),'frost',solid=True)
 for x in [59.2,67.3]:box('Open gate amber jamb',(x,147.0,3.4),(.08,.12,2),'amber')
 # Foreground waist-high angled bench plus a distinct side-menu mount.
 box('Signal terminal bench',(41,123,1),(4.8,1.35,.17),'metal',solid=True)
 for x in [39,43]:box('Terminal bench pedestal',(x,123,.5),(.35,1.1,1),'frost',solid=True)
 screen('terminal-bench',(41,122.85,1.95),(3.7,1.55),tilt=.42,style='map')
 box('Bench side menu pillar',(45.3,123,.65),(.8,.6,1.3),'frost',solid=True)
 screen('kiosk-pillar',(45.3,122.9,2.25),(1.0,1.9),tilt=.14)
 screen('wall-inset-console',(76,146.9,4.9),(3.0,2.0))
 ramp('Diagnostics platform ascent',75,78,130,142,0,2.4,12,'concrete')
 slab('Diagnostics platform',72,80,142,148,2.4,'concrete')
 rail((72,142,2.4),(72,148,2.4))
 box('Field operator bench',(38,136,1),(3.8,1,.17),'metal',solid=True)
 screen('operator-desk',(38,135.85,1.95),(2.5,1.4),tilt=.20)
 # Stairs and broad ramps reach both the dish deck and the cable gantry.
 ramp('Dish service ascent',30,33,128,144,0,4,20,'concrete')
 slab('Dish service platform',29,41,144,154,4,'concrete')
 rail((29,144,4),(29,154,4));rail((29,154,4),(41,154,4))
 cyl('Dish mounting base',(35,149,4.5),2.0,1,'metal');dish((35,149,8.5),5)
 ramp('East gantry ascent',79,82,114,138,0,6,30,'grating')
 slab('Cable gantry bridge',42,84,150.5,153.5,6,'grating')
 slab('Gantry east landing',79,84,138,153.5,6,'grating')
 rail((84,138,6),(84,153.5,6));rail((79,138,6),(79,146,6))
 rail((42,150.5,6),(79,150.5,6));rail((42,153.5,6),(84,153.5,6))
 for x in [43,75]:box('Gantry pier',(x,152,2.8),(.6,.6,5.6),'metal',solid=True)
 for off in [0,.13,.26]:rod('Gantry cable run',(42,153.0+off,6.3),(83,153.0+off,6.3),.05,'black')
 for x,y,h in [(46,153,23),(82,151,26),(31,116,15)]:
  for dx,dy in [(-.5,-.4),(.5,-.4),(0,.5)]:rod('Link mast',(x+dx,y+dy,0),(x,y,h),.06)
  for z in range(3,h,3):rod('Mast brace',(x-.4,y,z),(x+.4,y,z+2),.035)
  cyl('Mast warning beacon',(x,y,h+.12),.13,.26,'red-light');box('Antenna blade',(x,y,h-3),(.3,.2,3),'metal')
 for x,y in [(32,121),(48,151),(82,143),(46,132),(47.5,133),(70,139),(71.5,139),(34,140)]:
  crate((x,y,0));box('Case snow cap',(x,y,.85),(1.4,1,.12),'snow')
 for x,y in [(67,126),(68,132),(68,138),(45,127),(46,138)]:
  box('Thawed service pavement',(x,y,.018),(4.5,3.2,.025),'stone',0)
  for dx in [-2,2]:box('Pavement edge bolt',(x+dx,y,.039),(.12,.12,.012),'metal',0)

 box('Signal steam vent',(48,143,.3),(1,.7,.6),'frost',solid=True);steam((48,143,.6),1.8)
 for x,y in [(31,126),(47,141),(73,131)]:lamp((x,y,0),2.6)
 for x in [49,77]:box('Terrace amber strip',(x,132,.035),(.08,25,.05),'amber',0)
 for x in [50,78]:box('Fortress snow ledge',(x,147.5,20.5),(2.6,2.3,.3),'snow')
 P.area('Signal blue moonlight',(42,133,28),(57,139,0),4200,(.14,.28,1),20)
 P.area('Signal amber gate',(63,143,14),(63,137,0),1150,(1,.38,.08),9)
 P.area('Signal red warning',(82,150,18),(72,146,4),180,(1,.04,.012),4)
 night_vista()
 point('rise-ramp-top',(54,124,0),'rise-entry');point('rise-arrival',(54,125,0),'rise-ramp-top');point('rise-ring',(57,132,0),'rise-arrival');point('rise-wall',(63,136,0),'rise-ring');point('fortress-ramp-top',(63,146,2.4),'rise-wall');point('fortress-room',(63,152,2.4),'fortress-ramp-top')
 point('diagnostics-road',(74,128,0),'rise-ring');point('diagnostics-base',(76.5,130,0),'diagnostics-road');point('diagnostics-platform',(76.5,142,2.4),'diagnostics-base')
 point('dish-road',(37,126,0),'rise-arrival');point('dish-ramp-base',(31.5,128,0),'dish-road');point('dish-platform',(31.5,144,4),'dish-ramp-base')
 point('gantry-road',(63,124,0),'rise-arrival');point('gantry-south',(76,113,0),'gantry-road');point('gantry-base',(80.5,114,0),'gantry-south');point('gantry-top',(80.5,138,6),'gantry-base');point('gantry-east',(80.5,152,6),'gantry-top');point('gantry-west',(44,152,6),'gantry-east')
 for off in [-.5,.5]:
  for a,b in zip([(54+off,124,.03),(57+off,132,.03),(63+off,136,.03)],[(57+off,132,.03),(63+off,136,.03),(63+off,146,2.43)]):rod('Snow inset route rail',a,b,.020,'metal')


def vista():
 import any_angle
 any_angle.vista(sys.modules[__name__])


def load_ui():
 for i,name in enumerate(NAMES):
  for style in ['workspace','instrument','banner','map']:
   m=mat('ui-'+name+'-'+style,(1,1,1),unlit=True);tree=m.node_tree;n=tree.nodes.new('ShaderNodeTexImage');n.image=bpy.data.images.load(str(HERE/'materials/tiles'/f'ui-{name}-{style}.png'));n.extension='EXTEND';u=tree.nodes.new('ShaderNodeUVMap');u.uv_map='UV0';tree.links.new(u.outputs['UV'],n.inputs['Vector']);em=next(n for n in tree.nodes if n.type=='EMISSION');tree.links.new(n.outputs['Color'],em.inputs['Color'])


def spatial():
 # Collision uses exact walkable slopes, plus substantial prop/wall bounds.
 cols=[]
 for i,o in enumerate(WALK):
  data=o.data.copy()
  if o.name=='Rooftop bridge':
   # A top-only walking sheet joins the final slope without a false slab riser.
   lo=[min(v.co[k] for v in data.vertices) for k in range(3)];hi=[max(v.co[k] for v in data.vertices) for k in range(3)]
   # The visual bevel must not open a collision crack at the ramp/landing edge.
   verts=[(lo[0],lo[1],hi[2]),(hi[0],lo[1],hi[2]),(hi[0],hi[1],hi[2]),(lo[0],hi[1],hi[2])]
   data=bpy.data.meshes.new('Continuous rooftop landing');data.from_pydata(verts,[],[(0,1,2,3)]);data.update()
  c=bpy.data.objects.new('CollisionWalk-'+str(i),data);c.matrix_world=o.matrix_world.copy();bpy.context.collection.objects.link(c);cols.append(c)
 for i,(name,lo,hi) in enumerate(P.COLL):
  bpy.ops.mesh.primitive_cube_add(size=1,location=[(a+b)/2 for a,b in zip(lo,hi)]);c=bpy.context.object;c.name='CollisionProp-'+str(i);c.dimensions=[b-a for a,b in zip(lo,hi)];bpy.ops.object.transform_apply(location=False,rotation=False,scale=True);cols.append(c)
 # Path-following triangular ribbons include elevations and connect the actual ramps.
 lookup={p['id']:p['position'] for p in ROUTES};verts=[];faces=[]
 for e in EDGES:
  a,b=lookup[e['from']],lookup[e['to']];aa=Vector((a[0],-a[2],a[1]));bb=Vector((b[0],-b[2],b[1]));v=bb-aa;cross=Vector((-v.y,v.x,0));cross.normalize();cross*=max(.6,e['width']/2-.35);q=len(verts);verts.extend([aa-cross,aa+cross,bb+cross,bb-cross]);faces.extend([(q,q+1,q+2),(q,q+2,q+3)])
 for stair in STAIR_ROUTES:
  a,b=stair['from'],stair['to'];aa=Vector((a[0],-a[2],a[1]));bb=Vector((b[0],-b[2],b[1]));side=Vector((.6,0,0));q=len(verts);verts.extend([aa-side,aa+side,bb+side,bb-side]);faces.extend([(q,q+1,q+2),(q,q+2,q+3)])
 me=bpy.data.meshes.new('Walking centerline ribbons');me.from_pydata(verts,[],faces);nav=bpy.data.objects.new('Navigation',me);bpy.context.collection.objects.link(nav)
 for o in cols+[nav]:o.hide_render=True
 return cols,nav


def manifest(g,lm,nodes,cols,count):
 for area in AREAS:
  area['primaryAnchor']=next(r['anchorId'] for r in MOUNT_ROWS if r['areaId']==area['id'] and r['role']=='mounted-workspace');area['toolAnchors']=[r['anchorId'] for r in MOUNT_ROWS if r['areaId']==area['id'] and r['role']=='tool'];area['dataAnchors']=[r['id'] for r in OBJECTS if r['areaId']==area['id']]
 spawns=[{'id':'arrival','pose':{'position':up(AREAS[0]['spawn']),'rotation':[0,0,0,1]}}]+[{'id':a['id'],'pose':{'position':up(a['spawn']),'rotation':[0,0,0,1]}} for a in AREAS]
 m={'formatVersion':'0.2','id':'com.hyprune.lumen-reach','version':('0.7.1' if count==4 else f'0.{count}.1'),'name':'Lumen Reach','description':f'{count} connected workspace homes on a mountain watershed. Original architecture, instruments and paths.','license':'CC-BY-4.0','scene':'scene.gltf','preview':'preview.png','defaultSpawn':'arrival','spawns':spawns,'anchors':ANCHORS,'zones':[{'id':a['id'],'name':a['name'],'bounds':a['bounds']} for a in AREAS],'navigation':{'kind':'mesh','node':nodes['Navigation'],'agentRadius':.3,'agentHeight':1.8},'collision':[{'node':nodes[o.name],'shape':'mesh','layer':'static'} for o in cols],'lightmaps':lm,'attribution':[{'path':'.','author':'Hyprune contributors','license':'CC-BY-4.0','source':'https://github.com/hyprune/worlds'}],'extensions':{'com.hyprune.lumen-reach.mounts':{'version':1,'areas':[{**{k:v for k,v in a.items() if k not in ['spawn','bounds','name','freePlacementZones']},'spawnId':a['id'],'freePlacementZones':[z['id'] for z in a['freePlacementZones']]} for a in AREAS],'mounts':MOUNT_ROWS,'objects':OBJECTS},'com.hyprune.lumen-reach.routes':{'version':1,'nodes':ROUTES,'edges':EDGES,'semantics':'bidirectional walking centerlines, feet positions in meters'},'com.hyprune.lumen-reach.stairs':{'version':1,'paths':STAIR_ROUTES,'semantics':'visible treads over continuous collision beds; alternate walkable flights'},'com.hyprune.lumen-reach.placement':{'version':1,'zones':[z for a in AREAS for z in a['freePlacementZones']]},'com.hyprune.map':{'version':'0.1','path':'map.svg','projection':'xz','north':[0,0,-1],'bounds':[-36,-162,86,16],'worldToMap':[4/520,0,0,4/780,160/520,690/780]}},'requiredExtensions':[]}
 for name in ['fixture-audit.json','decal-audit.json','playable-boundary-report.json']:shutil.copy2(ART/name,OUT/name)
 if count==4:
  from world_visibility import annotate
  annotate(m,g)
  import any_angle
  any_angle.finish_export(sys.modules[__name__],g,m)
 (OUT/'world.json').write_text(json.dumps(m,indent=2)+'\n')
 rows=[];masters=json.loads((HERE/'materials/generation.json').read_text());byname={r['name']:r for r in masters}
 for p in sorted((OUT/'textures').glob('*.png')):
  asset=next((k for k in sorted(byname,key=len,reverse=True) if p.name==k+'.png' or p.name.startswith(k+'-')),None);r=None if p.name.startswith('night-sky-v7') else byname.get(asset);recipe='Original procedural color, signage or screen placeholder from materials/prepare.py and build.py.'
  if p.name.startswith('lightmap-'):recipe='Cycles diffuse DIRECT+INDIRECT without COLOR; OIDN RTLightmap; peak normalized linear irradiance, sRGB encoding, UV1.'
  if r:recipe='Original imagegen master, toroidal seam healing, periodic edge collar and wrap-safe PBR derivatives.'
  if asset=='night-vista':recipe='Original generated night panorama, 1600px bounded derivative, smooth upper-sky fade to shared zenith paint for opaque basin closure.'
  if asset=='sky-v7':recipe='Spherical panorama from original imagegen master; low-frequency longitude seam join (no mirrored or blended detail), full latitude range, uniform pole caps; materials/sky.py.'
  if p.name.startswith('night-sky-v7'):recipe='Original procedural band-limited night gradient with soft periodic ridge bands, uniform pole caps; materials/sky.py.'
  if asset=='steam':recipe='Original generated RGBA plume, bounded 512x768 derivative, clamp sampled BLEND crossed cards; core M2 alpha.'
  if p.name.startswith('reach-trim'):recipe='Original generated material masters composed into eight trim bands with 8px gutters; strip band mapped explicitly. Masters/prompts in source materials/generation.json.'
  rows.append({'path':p.relative_to(OUT).as_posix(),'author':'Hyprune contributors','license':'CC-BY-4.0','recipe':recipe,**({'masterSHA256':r['masterSHA256'],'prompt':r['prompt']} if r else {}),**({'derivedFrom':[{k:byname[name][k] for k in ['name','masterSHA256','prompt']} for name in ['concrete','metal','canvas','wood','frost','glass','strips','grating']]} if p.name.startswith('reach-trim') else {})})
 (OUT/'texture-provenance.json').write_text(json.dumps(rows,indent=2)+'\n');shutil.copy2(ROOT/'LICENSE',OUT/'LICENSE');shutil.copy2(HERE/'IDENTITY.md',OUT/'IDENTITY.md');shutil.copy2(HERE/'ATTRIBUTION.md',OUT/'ATTRIBUTION.md')
 svg=['<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 520 780"><rect width="520" height="780" fill="#10212d"/>']
 look={p['id']:p['position'] for p in ROUTES}
 def xy(p):return (p[0]*4+160,p[2]*4+690)
 for e in EDGES:
  a,b=xy(look[e['from']]),xy(look[e['to']]);svg.append(f'<path d="M {a[0]} {a[1]} L {b[0]} {b[1]}" stroke="#d6aa61" stroke-width="3" fill="none"/>')
 for area in AREAS:
  x,y=xy(up(area['spawn']));svg.append(f'<circle cx="{x}" cy="{y}" r="8" fill="#9ccaca"/><text x="{x+12}" y="{y}" fill="#eee0c7" font-size="12">{area["name"]}</text>')
 svg.append('</svg>');(OUT/'map.svg').write_text('\n'.join(svg))
 (ART/'views.json').write_text(json.dumps({'verticalFovDegrees':60,'views':VIEWS},indent=2)+'\n')


def stills():
 s=bpy.context.scene;s.cycles.samples=32
 for v in VIEWS:
  c=s.camera;c.location=v['position'];c.rotation_euler=(Vector(v['target'])-c.location).to_track_quat('-Z','Y').to_euler();s.render.filepath=str(ART/(v['id']+'.png'));bpy.ops.render.render(write_still=True)
 shutil.copy2(ART/'01-sun-court.png',OUT/'preview.png')

if __name__=='__main__':
 import argparse
 p=argparse.ArgumentParser();p.add_argument('--areas',type=int,choices=[1,2,3,4],default=4);p.add_argument('--samples',type=int,default=64);p.add_argument('--preview',action='store_true');p.add_argument('--stills',action='store_true');a=p.parse_args(sys.argv[sys.argv.index('--')+1:])
 BUILD_AREAS=a.areas
 if a.stills:
  bpy.ops.wm.open_mainfile(filepath=str(ART/'lumen-reach.blend'));P.gpu();VIEWS=[v for v in json.loads((HERE/'views.json').read_text())['views'] if v['areaCount']<=a.areas];(ART/'views.json').write_text(json.dumps({'verticalFovDegrees':60,'views':VIEWS},indent=2)+'\n');stills();sys.exit(0)
 sys.path.insert(0,str(HERE));import polish
 init();import any_angle;any_angle.materials(sys.modules[__name__]);load_ui();court();polish.apply(0,sys.modules[__name__]);P.log('Sun Court geometry ready')
 if a.areas>=2:hall();polish.apply(1,sys.modules[__name__]);P.log('Array Hall geometry ready')
 if a.areas>=3:
  vault();polish.apply(2,sys.modules[__name__]);import rime_v3;rime_v3.apply(sys.modules[__name__]);P.log('Rime Vault geometry ready')
 if a.areas>=4:rise();polish.apply(3,sys.modules[__name__]);P.log('Signal Rise geometry ready')
 vista();any_angle.architecture(sys.modules[__name__]);any_angle.boundaries(sys.modules[__name__]);VIEWS=[v for v in json.loads((HERE/'views.json').read_text())['views'] if v['areaCount']<=a.areas]
 if a.preview:stills()
 else:
  # Shared pipeline keeps tiling UV0 distinct from atlas UV1 throughout bake/export.
  for name,n in zip(NAMES[:a.areas],[2048,1536,2048,2048]):P.RESOLUTIONS[name]=n
  P.RESOLUTIONS['foliage']=1024
  P.MARGINS.update({'sun-court':4,'array-hall':4,'rime-vault':4,'signal-rise':4,'foliage':2})
  audit_fixtures()
  # Connector geometry owns compact atlases and independent glTF scene nodes.
  for chunk,prefixes in [('connector-descent',('Service descent','Descent','Sloping service roof','Service conduit')),('connector-ascent',('Snow service ascent','Snow ascent','Ascent amber'))]:
   moved=[]
   for group,objects in list(P.GROUPS.items()):
    selected=[o for o in objects if o.name.startswith(prefixes)]
    moved.extend(selected);P.GROUPS[group]=[o for o in objects if o not in selected]
   if moved:P.GROUPS[chunk]=moved;P.RESOLUTIONS[chunk]=768;P.MARGINS[chunk]=4
  cols,nav=spatial();P.join_groups()
  # A dense detail kit can exhaust pack margins and collapse all lightmap islands.
  # Geometry/overlap validity alone does not catch the resulting nearly black bake.
  density=[]
  for name,objects in P.GROUPS.items():
   if name in {'vista','atmosphere'}:continue
   me=objects[0].data;uv=me.uv_layers['UV1'];area=0
   for face in me.polygons:
    pts=[uv.data[i].uv for i in face.loop_indices];a0,b0,c0=pts
    area+=abs((b0.x-a0.x)*(c0.y-a0.y)-(b0.y-a0.y)*(c0.x-a0.x))*.5
   density.append({'group':name,'uv1Area':area,'triangles':len(me.polygons),'resolution':P.RESOLUTIONS[name]})
  (ART/'uv-density-report.json').write_text(json.dumps(density,indent=2)+'\n')
  for row in density:
   if row['group']=='rime-vault':assert row['uv1Area']>=.03,('rime-vault','collapsed lightmap packing',row['uv1Area'])
  P.bake(a.samples);g,lm,nodes=P.export(cols,nav);manifest(g,lm,nodes,cols,a.areas);bpy.ops.wm.save_as_mainfile(filepath=str(ART/'lumen-reach.blend'));stills()
