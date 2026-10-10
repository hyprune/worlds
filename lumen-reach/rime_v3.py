# SPDX-License-Identifier: MIT
"""Rime Vault's cold-service kit. All coordinates are authored Blender meters.

Low console banks stay below the primary wall's swept rectangle; tall services
stay against the walls or above it. Existing anchors/routes remain authoritative.
"""
import math,random
import bpy
from mathutils import Vector,Matrix

def apply(B):
 from polish import snowbank
 box,rod,mesh=B.box,B.rod,B.mesh
 def plate(name,p,size,mat='vault-metal',solid=False):
  return box(name,p,size,mat,.012 if min(size)>.10 else 0,solid=solid)
 # Replace the Vault's mottled master, including the original structural kit.
 for o in list(B.P.GROUPS['rime-vault']):
  if o.name.startswith(('Inset service floor grate','Local hazard curb','Pipe ice pendant')):
   B.P.GROUPS['rime-vault'].remove(o);bpy.data.objects.remove(o,do_unlink=True);continue
  old=o.data.materials[0].name
  if old=='frost':o.data.materials[0]=B.P.MATS['vault-metal']
  if o.name.startswith('Pipe frost accumulation'):o.data.materials[0]=B.P.MATS['rime-crust']
  if o.name.startswith(('Vault frosted service panel','Console backing')):o.data.materials[0]=B.P.MATS['condensation']
  if o.name.startswith('Gate red edge'):o.location.y-=.13
  if o.name.startswith('Vault floor strip'):o.location.x=32.1 if o.location.x<38 else 42.6

 def ice_fringe(x,y,z,n=12,span=2.0,height=.65,axis='x'):
  rng=random.Random(round((x+y+z)*631))
  for i in range(n):
   t=(i+.3)/n-.5;cx=x+(span*t if axis=='x' else 0);cy=y+(span*t if axis=='y' else 0)
   h=rng.uniform(.16,height);r=rng.uniform(.025,.075);verts=[(cx+.04,cy-.03,z-h)]
   verts += [(cx+r*math.cos(j*math.tau/6),cy+r*math.sin(j*math.tau/6),z) for j in range(6)]
   faces=[(0,1+j,1+(j+1)%6) for j in range(6)]
   mesh('Icicle dense blue core',verts,faces[1:]+[tuple(range(1,7))],'ice-body')
   # A bright facing facet fakes scattered edge light without alpha sorting.
   mesh('Icicle luminous edge',verts,[faces[0]],'ice-rim')

 def crust(x,ya,yb,z,r):
  verts=[];steps=max(2,round((yb-ya)/.65));segs=8
  for i in range(steps+1):
   y=ya+(yb-ya)*i/steps
   for j in range(segs+1):
    a=.12+(math.pi-.24)*j/segs;rr=r+.017+.012*math.sin(i*2.13+j)
    verts.append((x+rr*math.cos(a),y,z+rr*math.sin(a)))
  faces=[]
  for i in range(steps):
   for j in range(segs):
    a=i*(segs+1)+j;b=a+segs+1;faces.append((a,a+1,b+1,b))
  mesh('Top-only rime pipe shell',verts,faces,'rime-crust')
  for y in range(math.ceil(ya+1),int(yb),3):ice_fringe(x+r*.70,y,z+.03,7,1.1,.42 if 32<x<46 else .60,axis='y')

 # Insulated overhead pipe racks create a continuous service corridor silhouette.
 for x,r,z in [(29.9,.31,2.25),(31.0,.22,2.48),(44.8,.30,3.60),(46.0,.22,3.62)]:
  rod('Service rack insulated pipe',(x,77,z),(x,99,z),r,'vault-metal');crust(x,77,99,z,r)
  for y in [78.5,83,87.5,92,96.5]:
   rod('Rack flange',(x,y-.11,z),(x,y+.11,z),r+.085,'metal')
   for j in range(6):
    a=j*math.tau/6
    bolt=B.cyl('Flange captive bolt',(x+(r+.05)*math.cos(a),y,z+(r+.05)*math.sin(a)),.025,.26,'ivory',vertices=6)
    bolt.rotation_euler=(math.pi/2,0,0)
 for y in [78.5,83,87.5,92,96.5]:
  for x in [30.4,45.4]:
   z=1.93 if x<32 else 3.20
   plate('Rack channel support',(x,y,z),(2.9,.16,.17),'metal')
   for dx in [-1.25,1.25]:rod('Rack threaded hanger',(x+dx,y,z),(x+dx,y,3.96),.036,'metal')
 for x,z,r in [(27.25,2.5,.42),(48.7,1.5,.44),(46.9,3.3,.30)]:crust(x,77,100,z,r)

 def static_screen(x,y,z,w,h,tilt=.22,yaw=0):
  q=Matrix.Rotation(yaw,4,'Z')@Matrix.Rotation(math.pi/2-tilt,4,'X');r=q.to_3x3();center=Vector((x,y,z))
  frame=plate('Fixed process instrument',center,(w+.13,h+.13,.12),'metal');frame.rotation_euler=q.to_euler()
  verts=[center+r@Vector(v) for v in [(-w/2,-h/2,.067),(w/2,-h/2,.067),(w/2,h/2,.067),(-w/2,h/2,.067)]]
  o=mesh('Fixed service schematic',verts,[(0,1,2,3)],'ui-rime-vault-instrument',group='vista')
  for i,uv in enumerate([(0,0),(1,0),(1,1),(0,1)]):o.data.uv_layers[0].data[i].uv=uv

 # Five waist-height stations occupy floor pockets below the giant screen sweep.
 # They are fixed machinery; the existing interactive mounts keep their IDs.
 for x,y in [(33.8,85.6),(33.8,89.0),(33.8,92.4),(44.5,85.6),(44.5,89.0)]:
  plate('Process console pedestal',(x,y,-5.36),(2.35,1.18,1.28),'vault-metal',True)
  plate('Console toe plinth',(x,y,-5.88),(2.55,1.3,.21),'metal')
  plate('Console work lip',(x,y-.17,-4.68),(2.65,1.24,.13),'metal')
  static_screen(x,y+.22,-4.15,2.12,.86,.35)
  plate('Console keyboard bed',(x,y-.49,-4.59),(1.36,.43,.06),'black')
  for j in range(14):plate('Service keyboard key',(x-.60+j*.09,y-.50,-4.55),(.06,.24,.018),'ivory')
  for dx in [-1.10,1.10]:
   plate('Console indicator housing',(x+dx,y-.61,-4.68),(.13,.09,.17),'metal')
   plate('Console warning lens',(x+dx,y-.665,-4.67),(.055,.03,.07),'red-light')
  plate('Console foot light housing',(x,y-.63,-5.69),(1.9,.12,.18),'metal')
  plate('Console foot light',(x,y-.705,-5.68),(1.65,.035,.055),'amber')
  B.P.area('Console amber grazing',(x,y-.86,-5.45),(x,y-2,-5.97),95,(1,.25,.045),1.5)
  plate('Console Reach badge backing',(x,y-.615,-5.10),(.72,.07,.44),'metal')
  B.sigil((x,y-.659,-5.15),.38)
  for dx in [-.9,.9]:rod('Console power elbow',(x+dx,y+.59,-4.85),(x+dx,y+.72,-5.95),.055,'black')

 # Long wall console bank, outside both the main wall and side-mount approaches.
 for y in [84.5,87.0,89.5]:
  plate('Wall service bank',(48.4,y,-4.55),(1.55,2.35,2.9),'vault-metal',True)
  static_screen(47.60,y,-2.2,2.08,1.35,.05,-math.pi/2)
  for z in [-5.3,-4.8,-4.3]:plate('Wall bank vent',(47.61,y,z),(.10,1.9,.14),'metal')
  B.P.area('Wall bank amber task',(47.0,y,-.8),(47.5,y,-4),145,(1,.28,.045),1.2)

 # Recessed visual cable trenches are closed by real metal crossbars at floor level.
 # The original collision floor remains continuous beneath these shallow grates.
 for x in [35.5,41.1]:
  for ya,yb in [(83.4,88.0),(89.8,94.0),(95.5,98.0)]:
   plate('Cable trench dark recess',(x,(ya+yb)/2,-5.978),(.65,yb-ya,.022),'black')
   for dx in [-.21,0,.21]:rod('Trench visible cable',(x+dx,ya,-5.958),(x+dx,yb,-5.958),.020,'metal')
   for dx in [-.37,.37]:plate('Trench steel angle',(x+dx,(ya+yb)/2,-5.945),(.055,yb-ya,.055),'metal')
   for j in range(math.ceil((yb-ya)/.22)):
    y=ya+(j+.5)*(yb-ya)/math.ceil((yb-ya)/.22)
    plate('Trench cross grate',(x,y,-5.936),(.7,.06,.035),'metal')
   for side in [-1,1]:plate('Trench warning edge',(x+side*.45,(ya+yb)/2,-5.962),(.12,yb-ya,.025),'strip')

 for x,y,h in [(35.0,94.5,.85),(31.4,85.4,.70),(46.7,86.1,.80),(49.0,100.5,.65)]:
  B.crate((x,y,-6),(1.05,.76,h));snowbank(B,(x,y,-6+h+.095),(.53,.39,.10))
 # Soft snow stays in perimeter corners, never across the ramp or route centers.
 for x,y,s in [(49.0,77.0,(.7,1.0,.3)),(49.1,101,(.6,.5,.25)),(26.6,99,(.32,.75,.22)),(31.1,100.8,(.7,.6,.28))]:snowbank(B,(x,y,-5.98),s)

 # Frozen condensation gathers on the perimeter of the wall-inset console.
 for x in [32.4,45.6]:
  plate('Console condensation cheek',(x,99.31,-.7),(.30,.18,7.25),'condensation')
  ice_fringe(x,99.18,2.82,7,.32,.58)
 plate('Console upper rime sill',(39,99.16,3.85),(15.8,.38,.16),'rime-crust')
 # The fringe stops either side of the "03 RIME VAULT" sign (x 37.1..40.9).
 for x in [34.075,43.925]:ice_fringe(x,98.99,3.79,20,5.65,.58)
 for y in [80,86,92,98]:
  for x in [26.65,49.35]:ice_fringe(x,y,1.9,10,2.0,.65,axis='y')

 # Vent cluster with manifold, valves, chimney collars and staggered plumes.
 for x,y,h in [(46.7,90.5,.78),(47.8,91.1,1.05),(48.8,90.8,.65)]:
  plate('Purge vent foot',(x,y,-5.82),(.65,.65,.36),'metal',True)
  rod('Purge stack',(x,y,-5.65),(x,y,-6+h),.15,'vault-metal')
  B.cyl('Purge stack rim',(x,y,-6+h),.20,.12,'metal')
  B.steam((x,y,-5.94+h),.95)
  rod('Purge feed manifold',(x,y,-5.65),(48.95,y,-5.65),.07,'metal')
 B.P.area('Purge cold rim',(48.8,90.8,-2),(47.5,90.8,-5),120,(.26,.48,.72),1.3)

 # The sealed continuation is a layered pressure door with an amber light leak.
 for x in [26.35,29.65]:
  plate('Gate pressure jamb',(x,99.58,-3),(.30,.38,6.4),'metal',True)
  for z in [-5.5,-4.2,-2.9,-1.6,-.3]:plate('Gate interlock dog',(x,99.33,z),(.44,.26,.26),'metal')
 plate('Gate pressure lintel',(28,99.53,.22),(3.7,.45,.38),'metal')
 for name in ['Lettering SEALED','Lettering CONTINUATION','Sign plaque SEALED','Sign plaque CONTINUATION']:
  bpy.data.objects[name].location.y-=.26
 for z in [-1.8,-2.3]:plate('Gate plaque standoff',(28,99.585,z),(1.9,.23,.34),'metal')
 for x,sign in [(27.23,-1),(28.77,1)]:
  plate('Gate reinforced leaf',(x,99.57,-3),(.95,.14,5.55),'vault-metal')
  for z in [-4.8,-1.2]:rod('Gate diagonal reinforcement',(x-sign*.38,99.45,z-.32),(x+sign*.38,99.45,z+.32),.055,'metal')
 plate('Gate amber seam backing',(28,99.51,-3),(.09,.14,5.45),'metal')
 plate('Gate amber seam light',(28,99.422,-3),(.032,.03,5.30),'amber')
 for x in [26.4,29.6]:
  plate('Gate guide lamp housing',(x,99.20,-5.25),(.27,.28,.75),'metal')
  plate('Gate guide light',(x,99.045,-5.22),(.16,.04,.45),'amber')
  B.P.area('Gate beyond warm spill',(x,98.90,-4.85),(28,97,-5.9),180,(1,.23,.025),.7)
 B.P.area('Gate distant cold crown',(28,99,1.4),(28,98,-2),130,(.22,.42,.62),1.5)

 # Amber task light carries the composition; blue is a softer secondary fill.
 for name,factor in [('Vault usable blue fill',.65),('Vault cold ceiling',.70)]:
  for o in bpy.data.objects:
   if o.type=='LIGHT' and o.name.startswith(name):o.data.energy*=factor
 for y in [82.8,89.0,95.0]:
  plate('Vault overhead luminaire',(38,y,3.52),(1.2,.44,.26),'metal')
  plate('Vault overhead light',(38,y,3.367),(.97,.30,.045),'amber')
  B.P.area('Vault amber pool',(38,y,3.25),(38,y+1,-6),320,(1,.32,.08),2.0)

 # Cases added by the common kit also receive the directional Vault finish.
 for o in B.P.GROUPS['rime-vault']:
  if o.data.materials[0].name=='frost':o.data.materials[0]=B.P.MATS['vault-metal']
