# SPDX-License-Identifier: MIT
"""Flagship terminal architecture, all original procedural geometry.
An earlier private prototype's original warm bays, bronze detailing and folded botanical leaves
are a technique reference. No geometry/art file is imported.
"""
import math,random
import bpy
from mathutils import Vector
RNG=random.Random(731904)

def construct(k):
 box=k.box;cyl=k.cylinder;label=k.text;add=k.add
 def mesh(name,verts,faces,mat,group='vault'):
  me=bpy.data.meshes.new(name);me.from_pydata(verts,[],faces);me.update();o=bpy.data.objects.new(name,me);bpy.context.collection.objects.link(o);add(o,name,mat,group)
  if mat=='sky':
   for loop in o.data.loops:o.data.uv_layers['UV0'].data[loop.index].uv=[(0,0),(1,0),(1,1),(0,1)][loop.vertex_index]
  return o
 def pipe(name,points,r,mat='brass',group='vault',sides=8):
  vs=[];fs=[]
  for i,p in enumerate(points):
   p=Vector(p);t=Vector(points[min(i+1,len(points)-1)])-Vector(points[max(0,i-1)])
   t.normalize();ref=Vector((0,0,1)) if abs(t.z)<.9 else Vector((1,0,0));u=t.cross(ref).normalized();v=t.cross(u).normalized()
   for j in range(sides):vs.append(p+r*(math.cos(j*math.tau/sides)*u+math.sin(j*math.tau/sides)*v))
  for i in range(len(points)-1):
   for j in range(sides):fs.append((i*sides+j,i*sides+(j+1)%sides,(i+1)*sides+(j+1)%sides,(i+1)*sides+j))
  fs.append(tuple(reversed(range(sides))));fs.append(tuple((len(points)-1)*sides+j for j in range(sides)))
  o=mesh(name,vs,fs,mat,group)
  for p in o.data.polygons:p.use_smooth=True
  return o
 def ring(name,c,r,t,mat='brass',group='concourse',vertical=False,segments=64,start=0,end=math.tau):
  pts=[]
  for i in range(segments+1):
   a=start+(end-start)*i/segments;pts.append((c[0]+r*math.cos(a),c[1]+(0 if vertical else r*math.sin(a)),c[2]+(r*math.sin(a) if vertical else 0)))
  return pipe(name,pts,t,mat,group)
 def sphere(name,pos,scale,mat='leaf',group='plants'):
  bpy.ops.mesh.primitive_uv_sphere_add(segments=16,ring_count=8,radius=1,location=pos);o=bpy.context.object;o.scale=scale;bpy.ops.object.transform_apply(location=False,rotation=False,scale=True)
  for p in o.data.polygons:p.use_smooth=True
  return add(o,name,mat,group)
 def plant(x,y,z=0,height=2.5,group='plants',radius=.48):
  cyl('Ceramic botanical urn',(x,y,z+.34),radius,.68,'ivory',group,32,True)
  ring('Urn bronze lip',(x,y,z+.7),radius*.92,.028,'brass',group)
  cyl('Plant soil',(x,y,z+.71),radius*.86,.055,'soil',group,24)
  verts=[];faces=[]
  for stalk in range(9):
   a=stalk*math.tau/9+RNG.uniform(-.18,.18);reach=radius*RNG.uniform(.3,1.4);top=z+height*RNG.uniform(.75,1.08)
   pipe('Botanical stem',[(x+math.cos(a)*radius*.30,y+math.sin(a)*radius*.30,z+.69),(x+math.cos(a)*reach*.25,y+math.sin(a)*reach*.25,z+(top-z)*.6),(x+math.cos(a)*reach,y+math.sin(a)*reach,top)],.013,'leaf-dark',group,5)
   for j in range(5):
    side=a+(j%2-.5)*1.3;ll=height*.29*RNG.uniform(.75,1.05);root=Vector((x+math.cos(a)*reach*.6,y+math.sin(a)*reach*.6,z+(top-z)*(.44+j*.12)));tip=root+Vector((math.cos(side)*ll,math.sin(side)*ll,ll*.14));mid=(root+tip)/2+Vector((0,0,ll*.12));cross=Vector((-math.sin(side),math.cos(side),0))*ll*.18;i=len(verts)
    verts.extend([root,mid+cross,tip,mid-cross,mid+Vector((0,0,.045))]);faces.extend([(i,i+4,i+1),(i+1,i+4,i+2),(i+2,i+4,i+3),(i+3,i+4,i)])
  mesh('Folded leaves',verts,faces,'leaf',group)
 def bolt(x,y,z,group='vault'):
  o=cyl('Hex fastener',(x,y,z),.042,.026,'brass',group,6);o.rotation_euler.x=math.pi/2
 def rail(x1,x2,y,z=1.0,group='hall'):
  lo=[x1,y-.06,0];hi=[x2,y+.06,z+.05];k.COLL.append(('Safety balustrade',lo,hi));k.BLOCKS.append((lo,hi))
  pipe('Handrail',[(x1,y,z),(x2,y,z)],.034,'brass',group)
  pipe('Lower rail',[(x1,y,z-.56),(x2,y,z-.56)],.020,'metal',group)
  for x in [x1,x2,(x1+x2)/2]:box('Balustrade upright',(x,y,z*.5),(.065,.065,z),'metal',group,.018,True)
 def lounge(x,y,group,color='cloth'):
  box('Walnut seating plinth',(x,y,.22),(2.8,.95,.3),'wood',group,.11,True)
  box('Upholstered back',(x,y+.31,.78),(2.8,.25,.83),color,group,.12)
  for dx in [-1.24,1.24]:box('Soft arm',(x+dx,y,.61),(.3,.96,.62),color,group,.12)
  for i in range(3):
   dx=(i-1)*.77;box('Seat cushion',(x+dx,y-.07,.49),(.73,.7,.22),color,group,.09)
   o=box('Back cushion',(x+dx,y+.19,.81),(.67,.20,.43),'cloth',group,.09);o.rotation_euler.x=.13
  # A thin stitched inset is an actual strip, separated from fabric face.
  pipe('Seat bronze seam',[(x-1.13,y-.475,.39),(x+1.13,y-.475,.39)],.010,'brass',group)
 def cargo(x,y,number,color,group,stack=False):
  box('Cargo skid',(x,y,.1),(1.35,.82,.16),'rubber',group,.035,True)
  box('Case shell',(x,y,.72),(1.25,.74,1.08),'metal',group,.09,True)
  box('Case front inset',(x,y-.384,.72),(1.09,.042,.90),'ivory',group,.035)
  for dx in [-.55,.55]:
   box('Cargo edge guard',(x+dx,y-.422,.72),(.085,.05,1.02),'brass',group,.016)
   for z in [.34,1.10]:bolt(x+dx,y-.45,z,group)
  box('Recessed carry grip',(x,y-.425,1.00),(.28,.05,.095),'rubber',group,.02)
  box('Cargo identity plate',(x,y-.434,.67),(.55,.025,.24),'metal',group,.014)
  label(number,(x,y-.457,.68),.115,'letter',group)
  box('Cargo route band',(x,y-.436,.42),(.96,.022,.055),color,group,.008)
  # Original barcode geometry with explicit front-face separation.
  for i in range(12):box('Cargo barcode',(x-.24+i*.035,y-.458,.25),(.012 if i%3 else .021,.008,.07),'metal',group,0)
  for dy in [-.27,.27]:box('Case reinforcing rib',(x,y+dy,1.295),(1.15,.075,.045),'brass',group,.015)
  if stack:
   box('Pinned file parcel',(x+.1,y,1.48),(.85,.56,.32),'wood',group,.045)
   box('Parcel strap',(x+.1,y,1.652),(.055,.58,.017),color,group,.004)
 # A single level walk surface, with an elevated industrial edge and inset routes.
 box('Terminal foundation',(0,9,-.55),(42,44,1.08),'metal','hall',.15)
 box('Continuous concourse floor',(0,9,-.12),(40,42,.24),'stone','hall',.025)
 for x in [-12,0,12]:
  # Contrasting paths are narrow inset overlays, kept clear of props.
  box('Rubber route runner',(x-2.68,12,.010),(2.2,34,.016),'rubber','hall',.009)
  for dx in [-2.95,-2.42]:box('Route brass channel',(x+dx,12,.031),(.09,34,.030),'brass','hall',.012)
  color={-12:'cyan',0:'amber',12:'coral'}[x]
  for dx in [-2.95,-2.42]:box('Route luminous inlay',(x+dx,12,.055),(.024,33.8,.012),color+'-glow','hall',.004)
  for y in [-1,13,26]:
   pipe('Route arrow',[(x-2.87,y-.20,.069),(x-2.69,y,.069),(x-2.51,y-.20,.069)],.012,color+'-glow','hall',5)
  box('Branch light',(x-1.35,-4.5,.050),(2.7,.032,.018),color+'-glow','hall',.006)
 # Hairline expansion joints and bronze survey ticks keep the floor legible.
 for xx in range(-16,20,4):
  for yy in range(-12,30,4):
   box('Stone expansion joint',(xx,yy+1.99,.003),(.008,3.97,.004),'metal','hall',0)
 for yy in range(-8,30,4):
  box('Stone transverse joint',(0,yy,.003),(39.8,.008,.004),'metal','hall',0)
 # The concourse compass is an original architectural inlay, no live status.
 ring('Concourse compass',(0,-.7,.012),3.0,.009,'brass','hall',segments=96)
 for i in range(24):
  a=i*math.tau/24;pipe('Compass survey tick',[(math.cos(a)*3.13,-.7+math.sin(a)*3.13,.016),(math.cos(a)*3.28,-.7+math.sin(a)*3.28,.016)],.011,'brass','hall',5)
 # Front/side safety, solid collision at chest rail and actual uprights.
 rail(-19.7,19.7,-11.7)
 for x in [-20,20]:
  box('Terminal edge parapet',(x,10,.48),(.22,40,.96),'stone','hall',.035,True)
  box('Parapet cap',(x,10,.99),(.3,40,.06),'brass','hall',.015)
  for y in [-8,-1,8,17,26]:
   box('Vertical perimeter pylon',(x,y,4.2),(.4,.4,8.8),'metal','vault',.04,True)
   box('Pylon stone footing',(x,y,.41),(.68,.68,.9),'stone','hall',.06)
   for z in [1.35,3.2,5.6]:box('Pylon collar',(x,y,z),(.47,.47,.13),'brass','vault',.018)
   box('Pylon practical',(x-.24 if x>0 else x+.24,y,5.7),(.09,.48,1.15),'warm','vault',.028)
 # Grand elliptical vault: double ribs, lattice webs and longitudinal stringers.
 def arch(y,r=20.7,base=8.6,height=11.2):return [(r*math.cos(t),y,base+height*math.sin(t)) for t in [math.pi*i/64 for i in range(65)]]
 for y in [-10,-2,7,16,25,31]:
  for dy in [-.27,.27]:pipe('Vault principal rib',arch(y+dy),.18,'brass','vault',10)
  pts=arch(y)
  for i in range(0,64,2):
   p,q=pts[i],pts[min(i+2,64)];pipe('Rib diagonal web',[(p[0],y-.27,p[2]),(q[0],y+.27,q[2])],.043,'metal','vault',6)
  for i in [0,8,16,24,32,40,48,56,64]:
   p=pts[i];box('Rib bolted gusset',(p[0],y-.33,p[2]),(.48,.08,.48),'metal','vault',.024)
   for dx in [-.15,.15]:bolt(p[0]+dx,y-.389,p[2], 'vault')
  # Lower soffit ribbon traces the whole silhouette.
  pipe('Vault warm cove',[(p[0],p[1]-.36,p[2]-.20) for p in pts],.045,'warm','vault',8)
  for x in [-20.7,20.7]:box('Vault pier',(x,y,4.2),(.38,.65,8.8),'metal','vault',.035,True)
 for a in [math.pi*i/12 for i in range(1,12)]:
  x=20.7*math.cos(a);z=8.6+11.2*math.sin(a)
  pipe('Longitudinal vault purlin',[(x,-10,z),(x,31,z)],.07,'metal','vault')
  if a in [math.pi*3/12,math.pi*6/12,math.pi*9/12]:pipe('Sky vault cool trace',[(x,-9,z-.10),(x,30,z-.10)],.025,'cyan-glow','vault')
 # Open opaque slats: alpha-free clerestory fallback for the M1 profile.
 # Narrow gaps preserve the sky aperture in both Cycles and the engine.
 for side in [-1,1]:
  for t in [i*.015+.35 for i in range(16)]:
   a=t if side>0 else math.pi-t;b=a+.004
   x1,z1=20.65*math.cos(a),8.57+11.15*math.sin(a);x2,z2=20.65*math.cos(b),8.57+11.15*math.sin(b)
   mesh('Open clerestory ceramic slat',[(x1,-9,z1),(x2,-9,z2),(x2,30,z2),(x1,30,z1)],[(0,1,2,3)],'ivory','vault')
 # Large station-name gantry, suspended within the first vault opening.
 for x in [-6.6,6.6]:pipe('Arrival suspension',[(x,4,8.2),(x,4,18)],.038,'brass','concourse')
 box('Grand arrival sign',(0,4,8.2),(14.8,.30,1.65),'metal','concourse',.1)
 for z in [7.41,8.99]:box('Arrival bronze frame',(0,3.80,z),(14.7,.09,.08),'trim','concourse',.015)
 label('SWITCHYARD',(0,3.82,8.51),.68,'letter','concourse')
 label('CONCOURSE / SIX PERMANENT DOCKS',(0,3.82,7.82),.18,'warm','concourse')
 # Offset, smaller exhibit keeps all project headers clear and the route walkable.
 ex,ey=-4.4,-.7
 cyl('Routing table walnut plinth',(ex,ey,.36),1.10,.72,'wood','concourse',64,True)
 cyl('Routing table bronze rim',(ex,ey,.77),1.12,.10,'brass','concourse',64)
 cyl('Routing table map glass',(ex,ey,.835),1.02,.026,'panel','concourse',64)
 for r in [.37,.74,1.0]:ring('Map orbit',(ex,ey,.87),r,.014,'cyan-glow','concourse')
 for j,(r,z) in enumerate([(.91,1.75),(1.085,1.90),(1.295,2.05)]):
  for title,radius,thick,mat in [('Signal armature',r,.04,'brass'),('Signal ribbon',r-.07,.024,['cyan-glow','amber-glow','coral-glow'][j])]:
   tilt=(j-1)*.42;pts=[(ex+radius*math.cos(a)*math.cos(tilt),ey+radius*math.cos(a)*math.sin(tilt)-(0.055 if title=='Signal ribbon' else 0),z+radius*math.sin(a)) for a in [i*math.tau/96 for i in range(97)]]
   pipe(title,pts,thick,mat,'concourse')
 for i in range(6):
  a=i*math.tau/6;px,py=ex+.74*math.cos(a),ey+.74*math.sin(a)
  cyl('Map station dot',(px,py,.895),.045,.045,['cyan-glow','amber-glow','coral-glow'][i%3],'concourse',16)
 for x in [-6.4,6.4]:
  lounge(x,-7.7,'concourse');plant(x+(-2.2 if x<0 else 2.2),-7.4,group='concourse',height=2.65)
  cyl('Lounge table',(x,-5.9,.5),.68,.09,'wood','concourse',48,True)
  cyl('Table pedestal',(x,-5.9,.245),.20,.4,'brass','concourse',24)
  cyl('Table lantern',(x+.15,-5.9,.7),.075,.31,'warm','concourse',16)
 # Six detailed dock pavilions, each a little place to return to.
 for st in k.SPEC['stations']:
  x,y,c,g=st['x'],st['y'],st['color'],st['id']
  # Station back wall with walnut fins, angled outer returns and warm edge coves.
  box('Dock architectural wall',(x+1.25,y+1.25,2.24),(6.9,.32,4.56),'metal',g,.065,True)
  box('Walnut inset wall',(x+1.25,y+1.065,2.33),(6.55,.10,4.32),'wood',g,.04)
  for dx in [-3.14,3.14]:
   box('Dock stone pier',(x+1.25+dx,y+.85,2.26),(.33,.56,4.6),'stone',g,.07,True)
   box('Pier gold inlay',(x+1.25+dx,y+.548,2.45),(.028,.035,3.95),'warm',g,.006)
  for dx in [-2.6,-2.38,2.38,2.6]:box('Walnut screen fin',(x+1.3+dx,y+.91,2.3),(.075,.17,3.6),'wood',g,.018)
  box('Dock bezel',(x+1.3,y+.94,2.25),(4.44,.20,2.60),'metal',g,.065,True)
  box('Idle pane',(x+1.3,y+.828,2.25),(4.2,.028,2.36),'panel',g,.023)
  for dx in [-2.15,2.15]:box('Dock luminous hairline',(x+1.3+dx,y+.787,2.25),(.028,.045,2.32),c+'-glow',g,.007)
  # Typography stays on the header, leaving the application area clear.
  box('Station header',(x+.5,y+.78,4.56),(8.0,.22,.90),'metal',g,.07)
  label(st['number']+' / '+st['name'],(x+.5,y+.646,4.58),.34,'letter',g)
  label('APPLICATION DOCK',(x+1.3,y+.802,1.23),.11,c+'-glow',g)
  # A static route schematic sits behind the application interaction plane.
  for row in range(4):
   yy=y+.802;zz=1.65+row*.32;pipe('Idle dock route',[(x-.10,yy,zz),(x+.6,yy,zz),(x+.9,yy,zz+.14),(x+2.65,yy,zz+.14)],.007,c,g,5)
   for dx in [.05,1.25,2.45]:box('Idle route stop',(x+dx,yy-.003,zz+.14),(.026,.008,.035),c,g,0)
  label(st['number'],(x+1.3,y+.802,3.08),.13,c+'-glow',g)
  box('Screen ledge',(x+1.3,y+.56,.94),(5.8,.62,.16),'wood',g,.055,True)
  # Arched station canopy, ribs, coffer louvers, end caps and light strips.
  for dy in [-2.35,2.15]:
   for dx in [-4.50,4.50]:box('Pavilion column',(x+dx,y+dy,2.62),(.24,.24,5.38),'brass',g,.04,True)
   curve=[(x-4.5+i*9/32,y+dy,5.38+1.55*math.sin(i*math.pi/32)) for i in range(33)]
   pipe('Pavilion arch',curve,.11,'brass',g,8)
   pipe('Pavilion arch cove',[(a,b-.13,z-.12) for a,b,z in curve],.025,'warm',g,6)
  for i in range(13):
   dx=-4.35+i*.725;z=5.38+1.52*math.sin((dx+4.5)*math.pi/9)
   box('Canopy timber louver',(x+dx,y-.05,z),(.16,4.45,.13),'wood',g,.03)
   if i%3==0:box('Canopy practical',(x+dx,y-.05,z-.11),(.045,3.9,.035),'warm',g,.007)
  # Weathered rail-side cargo and a travel bench, safely beside the aisle.
  for j in range(3):cargo(x+3.45,y-4+j*.94,st['number']+'-'+str(j+1),c,g,stack=j==2)
  lounge(x+.80,y-3.1,g)
  # Rich planting lives beyond the dock wall, framing the return vista.
  plant(x+3.65,y+4.0,height=2.85,group=g,radius=.55)
  plant(x-.45,y+4.1,height=1.7,group=g,radius=.34)
  # Service pedestal and a twin-lens route signal, static identity rather than status.
  box('Signal cabinet',(x-3.80,y+1,.43),(.46,.46,.94),'metal',g,.055,True)
  cyl('Signal mast',(x-3.8,y+1,1.83),.075,2.85,'brass',g,16,True)
  box('Signal head',(x-3.8,y+.97,3.15),(.48,.29,1.13),'metal',g,.065)
  for z in [2.85,3.22,3.59]:
   o=cyl('Signal lens hood',(x-3.8,y+.79,z),.14,.10,'brass',g,24);o.rotation_euler.x=math.pi/2
   o=cyl('Signal identity diffuser',(x-3.8,y+.73,z),.10,.027,'diffuser' if z==3.22 else 'panel',g,24);o.rotation_euler.x=math.pi/2
  label(st['number'],(x-3.8,y+.808,2.51),.11,'letter',g)
  # Cable runs follow the side of the dock, clear of standing circulation.
  for off in [0,.07,.14]:pipe('Dock service cable',[(x+4.75,y-2,.20+off),(x+4.75,y+1.7,.20+off),(x+4.7,y+2.0,1.0+off),(x+3.9,y+2.0,1.0+off)],.02,'rubber',g,6)
  for yy in [y-1.5,y-.5,y+.5]:box('Cable saddle',(x+4.75,yy,.34),(.25,.05,.04),'brass',g,.01)
  k.area('Pavilion warm pool '+g,(x+1,y-1.0,5.4),(x+1,y+1,1.0),450,(1,.56,.24),4.0)
  k.area('Dock grazing wash '+g,(x-1,y-1,3.8),(x+1,y+1,2.0),180,(1,.68,.40),3.0)
 # Side mechanical gantries and outer rails make the hall feel like a real yard.
 for x in [-18.8,18.8]:
  pipe('Industrial utility run',[(x,-9,6.8),(x,30,6.8)],.11,'metal','vault',12)
  for j in range(0,40,2):
   yy=-9+j;box('Cable tray rung',(x,yy,7.08),(.82,.075,.10),'brass','vault',.01)
  for dx in [-.27,.27]:pipe('Copper power bus',[(x+dx,-9,7.11),(x+dx,30,7.11)],.035,'brass','vault',8)
 # A rear colonnade opens onto a huge original city and elevated rail panorama.
 for x in [-18,-9,0,9,18]:
  box('Rear vista pier',(x,29.2,5.2),(.55,.5,10.5),'metal','vault',.05,True)
  for z in [1.0,7.3]:box('Rear pier ring',(x,29.2,z),(.68,.62,.18),'brass','vault',.025)
 rail(-19.7,19.7,29.55,group='hall')
 from skyline import construct as skyline
 skyline(k,mesh,pipe,sphere)
 return {'pipe':pipe,'ring':ring}
