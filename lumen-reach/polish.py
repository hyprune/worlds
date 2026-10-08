# SPDX-License-Identifier: MIT
"""Original settlement detail kit. All dimensions in meters; edge/ceiling dressing.
Kept separate from the circulation plan so clearance sweeps stay authoritative.
Uses the existing ten generated PBR masters and Reach trim atlas, no new samplers.
"""
import math,random
from mathutils import Vector,Matrix
import bpy

def apply(area,B):
 box,rod,mesh=B.box,B.rod,B.mesh
 def plate(name,p,size,mat='metal'):
  return box(name,p,size,mat,0)
 def cable(name,points,r=.035,mat='black'):
  for a,b in zip(points,points[1:]):rod(name,a,b,r,mat)
 def vent(p,w=1.2,h=.7):
  x,y,z=p;plate('Vent housing',(x,y,z),(w+.16,.18,h+.14),'frost' if area>1 else 'metal')
  for i in range(7):plate('Vent angled louver',(x,y-.105,z-h/2+(i+.5)*h/7),(w,.08,h/12),'metal')
  for dx in [-w/2,w/2]:plate('Vent fixing',(x+dx,y-.16,z),(.065,.04,.065),'ivory')
 def icicles(x,y,z,count=9,span=2,maxh=.68):
  rng=random.Random(int((x+y+z)*371))
  for i in range(count):
   h=rng.uniform(.12,maxh);r=rng.uniform(.025,.065)
   cx=x-span/2+span*i/count;cy=y+rng.uniform(-.08,.08)
   verts=[(cx,cy,z-h)]+[(cx+r*math.cos(j*math.tau/6),cy+r*math.sin(j*math.tau/6),z) for j in range(6)]
   mesh('Pipe ice pendant',verts,[(0,1+(j+1)%6,1+j) for j in range(6)]+[tuple(range(1,7))],'ice')
 def pipe(x,ya,yb,z,r=.28):
  rod('Insulated coolant main',(x,ya,z),(x,yb,z),r,'frost')
  for y in range(math.ceil(ya),int(yb),3):
   rod('Coolant coupling',(x,y-.09,z),(x,y+.09,z),r+.065,'metal')
   plate('Pipe saddle',(x,y,z+.30),(.65,.15,.12),'metal')
   rod('Pipe suspension',(x,y,z+.32),(x,y,3.96),.035)
  # A separate upper frost crust, deliberately overlapping the cylinder volume.
  rod('Pipe frost accumulation',(x,ya+.03,z+r*.63),(x,yb-.03,z+r*.63),r*.64,'snow')
 def wall_light(x,y,z,w=1):
  plate('Service luminaire',(x,y,z),(w+.18,.30,.30),'metal')
  plate('Service luminaire lens',(x,y-.17,z),(w,.055,.11),'amber')
  B.P.area('Local amber service light',(x,y-.26,z),(x,y-2,z-2),100 if area==2 else 55,(1,.49,.19),1.0)
 if area==0:
  # Continuous facade courses and perimeter service details frame the open court.
  for x in [-6,-3.5,20.3,23]:
   for z in [5.7,8.8,11.9,14.8]:
    plate('Facade panel reveal',(x,23.13,z),(2.1,.20,.09))
   vent((x,22.98,4.8),1.6,.8)
  for x in [-5.8,22.5]:
   cable('Facade rainwater pipe',[(x,23.08,.25),(x,23.08,15.6),(x,24,16.1)],.075)
   for z in [2,5,8,11,14]:plate('Rainwater clamp',(x,23.11,z),(.26,.22,.085),'metal')
  # Grounded header plaques; the landing remains open beneath them.
  for x in [-5,21]:wall_light(x,22.95,3.8,1.4)
  for x,y,z in [(-16,-5,5),(22,-8,4.4),(17,24.4,19.2)]:
   w=10 if x==-16 else 6 if x==22 else 8;d=10 if x==-16 else 6 if x==22 else 4
   for dy in [-d/2,d/2]:
    rod('Shelter stitched hem',(x-w/2,y+dy,z+.18),(x+w/2,y+dy,z+.18),.034,'canvas')
   for dx in [-w/2,w/2]:
    cable('Shelter power cable',[(x+dx,y-d/2,z),(x+dx,y,z-.32),(x+dx,y+d/2,z)],.025)
    wall_light(x+dx,y,z-.44,.35)
   rod('Canopy diagonal brace',(x-w/2,y-d/2,z-.8),(x-w/2+1.2,y-d/2,z+.18),.035)
  for x,y in [(-18,-7),(-20,-1),(23,-6),(24,13)]:
   B.crate((x,y,0),(1.25,.9,.65))
   plate('Folded repair canvas',(x,y,.70),(1.03,.75,.10),'canvas')
  for x,y in [(-17,2),(22,10),(-4,18)]:
   plate('Court service hatch',(x,y,.021),(1.3,.75,.032),'grating')
   for dx in [-.72,.72]:plate('Hatch border',(x+dx,y,.022),(.06,.9,.04),'metal')
  # A small shelf of useful objects on the ends of the field benches.
  for x,y in [(-17.15,-7.7),(24.15,-8)]:
   plate('Instrument tool case',(x,y,1.19),(.45,.48,.18),'strip')
   B.cyl('Calibration spool',(x,y+.29,1.27),.13,.28,'metal',vertices=12)
  # Foreground repair station frames arrival, outside the work and route volumes.
  for pos,size in [((-12.2,-12,0),(1.6,1.2,1.0)),((-12.2,-12,1.08),(1.35,1.05,.62)),((-11,-10.3,0),(1.5,1.05,.85))]:B.crate(pos,size)
  plate('Repair station foldout',(-12.2,-10.4,1.02),(1.8,.9,.10),'wood')
  cable('Repair station coiled lead',[(-12.2,-10.5,.13),(-11.5,-10,.13),(-11.3,-9.3,.13),(-12,-8.9,.13),(-12.8,-9.4,.13),(-12.2,-10.5,.13)],.022)
  B.tree(13,-8,0,1.0)
  # More leaves at the perimeter, not in work pockets.
  B.tree(24,5,0,.85);B.tree(-18,19,4,.60)
 elif area==1:
  # Shadowed, layered architectural bays with collars and golden inset strips.
  for x in [-5.6,23.6]:
   side=1 if x<0 else -1
   for y in [33,44,58]:
    for dy in [-.7,.7]:plate('Atrium pier metal fillet',(x,y+dy,10),(.19,.16,19.5),'metal')
    for z in [1.1,4.5,8.5,16,19.3]:plate('Atrium pier collar',(x+side*.04,y,z),(.75,1.8,.17),'trim')
   for y in [45,48,55,57]:
    # Rack internals on the inside-facing plane; alternating drawers and vents.
    face=x+side*.52
    for z in [.55,1.15,1.75,2.35,2.95,3.55,4.15]:
     plate('Archive rack drawer',(face,y,z),(.14,1.30,.45),'frost')
     for dy in [-.43,.43]:plate('Drawer handle',(face+side*.085,y+dy,z),(.10,.13,.05),'metal')
     plate('Drawer indicator',(face+side*.13,y-.25,z+.12),(.025,.14,.035),'cyan')
    plate('Rack cable spine',(face,y+.82,2.5),(.15,.10,4.8),'black')
   for ya,yb in [(34,42),(49,57)]:
    for z in [6,12,17]:
     plate('Hall service lintel',(x,(ya+yb)/2,z),(.75,yb-ya,.24),'metal')
  for x in [-5.8,23.8]:
   for y in [36.8,41.5,50,54.8]:
    plate('Atrium secondary rib',(x,y,11.5),(.58,.30,17.5),'concrete')
    for z in [4.7,9.2,15.3]:plate('Pier inset collar',(x,y,z),(.66,.50,.13),'trim')
  # A visible housing, radial braces and properly hung ceiling ring.
  B.torus('Light ring structural rim',(8,46,19.93),8.5,.14,'metal')
  for j in range(12):
   a=j*math.tau/12
   rod('Ring suspension radial',(8+8.5*math.cos(a),46+8.5*math.sin(a),19.95),(8+6.6*math.cos(a),46+6.6*math.sin(a),21.4),.025)
  for y in [49.5,53,56.5]:
   plate('Balcony underside rib',(-5.3,y,3.7),(1.1,.2,.34),'metal')
  for x,y in [(-4.5,51),(23,38)]:
   plate('Atrium service cabinet',(x,y,1.1),(1.15,1.2,2.2),'frost')
   vent((x,y-.66,1.35),.9,.8)
   B.sigil((x,y-.614,.55),.4)
  B.banner(22.6,56.9,12,5);B.banner(-5.2,49,13.5,5)
  for x,y in [(-4.2,33.7),(22.5,57.5)]:B.tree(x,y,0,.60)
  for x,y in [(-2.2,59),(19.4,58.5)]:B.crate((x,y,0),(1.15,.85,.68))
  # Long channels make the floor feel serviced, without a lifeless tiled layout.
  for x in [-3.35,21.35]:
   for ya,yb in [(34,41),(45,48),(51,58)]:plate('Atrium drainage channel',(x,(ya+yb)/2,.018),(.38,yb-ya,.022),'grating')
 elif area==2:
  # Major coolant trunks are large enough to read from the arrival camera.
  for x,z,r in [(27.25,2.5,.42),(48.7,1.5,.44),(46.9,3.3,.30)]:pipe(x,77,100,z,r)
  for x in [30.4,31.0,44.5,45.1]:
   cable('Vault overhead cable bundle',[(x,76,3.4),(x,82,3.15),(x,89,3.25),(x,96,3.12),(x,101,3.4)],.065,'black')
  for y in [79,84.5,90,96]:
   for x in [30.7,44.8]:
    plate('Cable tray cradle',(x,y,3.30),(1.25,.14,.15),'metal')
    for dx in [-.58,.58]:rod('Tray hanger',(x+dx,y,3.30),(x+dx,y,3.97),.026)
   # Raised crossbeams and brackets, clear of the upper workspace rectangle.
   plate('Vault overhead crossbeam',(38,y,3.73),(23,.28,.34),'metal')
  for y in [78.5,84,89.5,95]:
   # Side cladding panel seams and coarse rivets; all outside screen approaches.
   for x,side in [(26.36,1),(49.64,-1)]:
    plate('Vault frosted service panel',(x,y,-1.1),(.12,4.7,7.6),'frost')
    for z in [-4.5,-1.5,1.5]:
     plate('Panel transverse reinforcement',(x+side*.1,y,z),(.16,4.55,.10),'metal')
     for dy in [-2,2]:plate('Vault panel fastener',(x+side*.20,y+dy,z),(.08,.08,.08),'ivory')
   # Visible ice fringes along side pipes; no approach-volume intrusion.
   icicles(48.7,y,1.2,10,1.2);icicles(27.25,y,2.2,8,1.0)
   wall_light(48.1,y,2.7,.65)
   B.P.area('Cool pipe rim fill',(47.5,y,2.8),(49,y,-2),180,(.34,.55,.78),2)
  for x in [29,33,43,47]:
   for y in [81,89,97]:icicles(x,y,3.45,6,.7,maxh=.26)
  for y in [79,86.5,94]:
   plate('Inset service floor grate',(38,y,-5.975),(4.0,3.5,.030),'grating')
   for x in [35.8,40.2]:plate('Local hazard curb',(x,y,-5.972),(.18,3.5,.032),'strip')
  # Side service hardware makes both side walls read as occupied work machinery.
  for x,y in [(48.65,85.5),(48.65,90),(26.9,88)]:
   plate('Pump cabinet',(x,y,-4.8),(.95,1.8,2.4),'frost')
   plate('Pump top cap',(x,y,-3.55),(1.05,1.85,.12),'snow')
   cable('Pump riser',[(x,y,-3.55),(x,y,-.8),(x-.25,y,1.3)],.10,'metal')
  for x,y in [(46.9,86),(46.8,88),(33.9,97)]:
   B.crate((x,y,-6),(1.25,.9,.75));icicles(x,y-.48,-5.2,8,1.2)
  for x in [31,47]:
   vent((x,98.85,2.6),1.1,.5)
   plate('Console lower service panel',(x,99.0,-4.8),(1.5,.6,1.3),'frost')
  # Desk keyboards are below the lower edges of the swept window rectangles.
  for x,y in [(33.6,81),(45,82)]:
   plate('Desk keyboard',(x,y-.27,-4.922),(1.2,.36,.030),'black')
   for j in range(12):plate('Keyboard worn keys',(x-.53+j*.095,y-.29,-4.896),(.057,.20,.012),'ivory')
  B.P.area('Vault usable blue fill',(37,80,1.0),(38,89,-3.5),900,(.28,.42,.62),7)
  B.P.area('Vault warm pipe rake',(31,95,2),(27,88,1.8),580,(1,.47,.20),4)
 elif area==3:
  # Frosted facade and tower edge details, seated behind all usable wall screens.
  for x in [50.4,76.5]:
   for z in [2,7,17.6]:
    vent((x,146.62,z),1.8,.65);icicles(x,146.48,z+.40,14,2.5)
  for x in [54,58,68,72]:icicles(x,146.80,19.68,16,3.6)
  for y in [116,121,126,132,139]:
   # Snow banks on outer edges shape the basin without changing any route bed.
   for x in [29.4,84.4]:snowbank(B,(x,y,.02),(1.05,2.9,.48+(y%3)*.12))
  for x,y,s in [(33,118,(2,1.3,.4)),(46,136,(1.3,.7,.22)),(72,140,(1.6,.7,.23)),(40,156,(2.8,1,.6))]:snowbank(B,(x,y,.01),s)
  for x,y in [(41,123),(38,136)]:
   plate('Snowy bench lower fascia',(x,y,.76),(3.65,.90,.36),'frost')
   plate('Bench front insulation',(x,y-.51,.61),(3.6,.14,.10),'strip')
   # Snow gathers behind the angled screens; front remains available for tools.
   snowbank(B,(x,y+.49,1.05),(1.9,.24,.13))
  for x in range(44,79,3):
   cable('Gantry hanging cable',[(x,153.2,5.8),(x+.5,153.2,4.7),(x+1.4,153.2,4.5),(x+2.2,153.2,4.8),(x+3,153.2,5.8)],.04)
   plate('Gantry cable clamp',(x,153.2,5.82),(.15,.45,.30),'metal')
  for x,y in [(31,119),(47.5,136),(70,140)]:
   B.crate((x,y,0),(1.4,1.0,1.15));snowbank(B,(x,y,1.17),(.72,.53,.12))
  # Physical near and middle ridges sit in front of the far painted skyline.
  for x,y,s in [(23,142,(4,10,9)),(26,160,(5,9,13)),(45,167,(5,4,7)),(91,135,(4,10,9)),(84,176,(7,3,12))]:
   snowbank(B,(x,y,-1),s,rock=True)
  B.P.area('Signal soft blue edge',(37,131,17),(35,149,9),2600,(.30,.48,1),12)
  B.P.area('Signal bench practical',(41,123.6,3.9),(41,123,0),110,(1,.54,.24),2)

def snowbank(B,pos,scale,rock=False):
 # Closed irregular rings: genuine silhouette and parallax, not a flat snow card.
 rng=random.Random(int(sum(pos)*141));x,y,z=pos;sx,sy,sz=scale;verts=[(x,y,z+sz)];faces=[];n=16
 for ring in range(1,5):
  t=ring/4
  for j in range(n):
   a=j*math.tau/n;noise=1+rng.uniform(-.13,.13);verts.append((x+math.cos(a)*sx*t*noise,y+math.sin(a)*sy*t*noise,z+sz*(1-t*t)*(1+rng.uniform(-.16,.16))))
 for j in range(n):faces.append((0,1+j,1+(j+1)%n))
 for ring in range(1,4):
  a=1+(ring-1)*n;b=1+ring*n
  for j in range(n):k=(j+1)%n;faces.append((a+j,b+j,b+k,a+k))
 faces.append(tuple(reversed(range(1+3*n,1+4*n))))
 B.mesh('Snow basin crag' if rock else 'Accumulated drift',verts,faces,'rock' if rock else 'snow')
 if rock:
  # Alternate snow shelves reveal dark rock beneath a broken upper snow line.
  B.mesh('Crag upper snow',[(px,py,pz+.05) for px,py,pz in verts[:33]],faces[:32],'snow')
