# SPDX-License-Identifier: MIT
"""Original rail-city kit: layered setbacks, lanterns, forked crowns and spires.
Palette-based distance layering works without transparent fog or external HDRIs.
"""
import math,random
import bpy

def construct(k,mesh,pipe,sphere):
 rng=random.Random(830711);box=k.box;label=k.text
 # Continuous original sky sphere removes the old backdrop's visible upper edge.
 bpy.ops.mesh.primitive_uv_sphere_add(segments=64,ring_count=32,radius=220,location=(0,0,0))
 sky=k.add(bpy.context.object,'Original gradient sky sphere','sky','vista')
 sky.visible_diffuse=False;sky.visible_shadow=False
 for loop in sky.data.loops:
  z=sky.data.vertices[loop.vertex_index].co.z
  sky.data.uv_layers['UV0'].data[loop.index].uv=(.5,min(1,max(0,(z+40)/160)))

 # Haze is encoded in the architecture palette. Every layer is opaque/unlit.
 for layer,(y,tone) in enumerate([(150,'sky-far'),(130,'sky-mid'),(110,'sky-near')]):
  for i in range(46):
   x=-145+i*6.4;h=rng.uniform(5,18);w=rng.uniform(4,6.2)
   box('Layer %d low city block'%layer,(x,y,h/2-8),(w,4,h),tone,'vista',0)
   if i%4==0:box('Layer skyline setback',(x,y,h-7.1),(w*.6,3,1.8),tone,'vista',0)
 # Foreground and middle-distance buildings share physical modules, not copies
 # of a uniform cube. Dark side ribs read at oblique arrival/vault viewpoints.
 for i in range(37):
  x=-93+i*5.3;y=rng.uniform(61,97);h=rng.uniform(14,34);w=rng.uniform(3.1,4.8);d=rng.uniform(3,5)
  # Reserve clear footprints around the three original landmarks.
  if any(abs(x-lx)<rx+w/2 and abs(y-ly)<ry+d/2 for lx,ly,rx,ry in [(-24,72,4.8,3.8),(9,88,4.5,3),(39,79,4.3,3.2)]):continue
  tone='sky-near' if y<75 else 'sky-mid';lit='sky-window-near' if y<75 else 'sky-window-far'
  z0=-7;typ=i%5
  heights=[h*.62,h*.24,h*.14] if typ in [0,3] else [h*.84,h*.16]
  zz=z0
  for j,dh in enumerate(heights):
   ww=w*(1-.20*j);dd=d*(1-.18*j)
   box('Setback city shaft',(x,y,zz+dh/2),(ww,dd,dh),tone,'vista',.035)
   box('Terrace roof rim',(x,y,zz+dh+.06),(ww+.17,dd+.17,.12),'sky-crown','vista',.02)
   if j==0:
    # Vertical facade blades and occupied ribbon windows, with restrained gaps.
    for dx in [-.32,.32]:box('Facade vertical fin',(x+dx*ww,y-dd/2-.035,zz+dh/2),(.075,.10,dh-.35),'sky-crown','vista',0)
    for row in range(1,int(dh/1.55)):
     z=zz+row*1.55
     for col in range(4):
      if rng.random()<.43:
       box('Occupied facade window',(x+(col-1.5)*ww*.21,y-dd/2-.06,z),(ww*.13,.028,.29),lit,'vista',0)
     if row%4==0 and typ==2:box('Lit belt course',(x,y-dd/2-.065,z+.5),(ww*.87,.024,.06),'sky-cyan','vista',0)
    for row in range(2,int(dh/1.8),3):
     box('Side ribbon glazing',(x+ww/2+.028,y,zz+row*1.8),(.04,dd*.72,.18),lit,'vista',0)
   zz+=dh+.24
  if typ==1:
   # Twin fork crown, cross-braced mast and aviation light.
   for dx in [-w*.28,w*.28]:box('Fork crown blade',(x+dx,y,zz+1.8),(.25,d*.7,3.6),tone,'vista',.02)
   pipe('Crown cross brace',[(x-w*.28,y-.1,zz+.2),(x+w*.28,y-.1,zz+3.5)],.065,'sky-crown','vista')
  elif typ==2:
   pipe('Needle antenna',[(x,y,zz),(x,y,zz+4.0)],.05,'sky-crown','vista')
   box('Aviation marker',(x,y,zz+4.15),(.14,.14,.18),'sky-red','vista',0)
  elif typ==4:
   # Sloping sculpted crown rather than another cuboid.
   mesh('Angled skyline crown',[(x-w*.3,y-d*.3,zz),(x+w*.3,y-d*.3,zz),(x+w*.3,y+d*.3,zz),(x-w*.3,y+d*.3,zz),(x-w*.12,y,zz+3.8)],[(0,1,4),(1,2,4),(2,3,4),(3,0,4)],tone,'vista')
  if i in [8,17,27]:
   name=['NORTH','RAIL','HYPRUNE'][[8,17,27].index(i)]
   box('City illuminated sign tray',(x,y-d/2-.14,z0+h*.65),(w*.91,.13,1.0),tone,'vista',.025)
   label(name,(x,y-d/2-.22,z0+h*.65),.48,'sky-cyan','vista')
 # Three original landmarks create a memorable silhouette beyond the concourse.
 # Meridian tower: terraced monolith with an open, warm-lit lantern crown.
 x,y=-24,72
 for z,w,d,h in [(4,8,6,22),(20.30,6.1,5,10),(29.60,4.5,4,8),(40.90,3.6,3.2,14)]:
  box('Meridian tower tier',(x,y,z),(w,d,h),'sky-near','vista',.08)
  box('Meridian terrace',(x,y,z+h/2+.10),(w+.24,d+.24,.2),'sky-crown','vista',.04)
  for dx in [-w*.35,w*.35]:box('Meridian vertical light',(x+dx,y-d/2-.04,z),(.06,.04,h-.7),'sky-amber','vista',0)
 for dx in [-1.8,1.8]:
  for dy in [-1.6,1.6]:box('Lantern crown post',(x+dx,y+dy,49.2),(.19,.19,4.4),'sky-crown','vista',0)
 box('Lantern glowing core',(x,y,49.2),(2.3,2.3,3.0),'sky-window-near','vista',.05)
 box('Lantern crown roof',(x,y,51.5),(4.4,4.1,.27),'sky-crown','vista',.07)
 pipe('Meridian spire',[(x,y,51.5),(x,y,57.5)],.065,'sky-crown','vista')
 box('Meridian aviation beacon',(x,y,57.7),(.20,.20,.25),'sky-red','vista',0)
 # Twin relay: two slender prongs connected by a luminous sky bridge.
 x,y=9,88
 for dx,h in [(-2.15,63),(2.15,69)]:
  box('Relay landmark shaft',(x+dx,y,h/2-7),(2.9,4.4,h),'sky-mid','vista',.12)
  box('Relay chamfered crown',(x+dx,y,h-6.1),(2.1,3.2,1.8),'sky-crown','vista',.08)
  box('Relay vertical illuminated edge',(x+dx+1.40,y-2.23,h/2-7),(.045,.04,h-.7),'sky-cyan','vista',0)
  for j in range(2,int(h/1.8),2):box('Relay occupied ribbon',(x+dx,y-2.24,j*1.8-7),(1.9,.035,.15),'sky-window-far','vista',0)
 box('Relay sky bridge',(x,y,28),(4.7,2.6,.7),'sky-crown','vista',.05)
 box('Relay bridge light',(x,y-1.33,28),(4.5,.03,.13),'sky-cyan','vista',0)
 # Horizon observatory: tapering stepped shoulder and large rooftop halo.
 x,y=39,79
 for j in range(5):box('Observatory taper',(x,y,2+j*5),(7.0-j*.95,5.5-j*.6,5.05),'sky-near','vista',.06)
 for dx in [-2,2]:box('Observatory halo support',(x+dx,y,27),(.25,.25,6),'sky-crown','vista',0)
 points=[(x+3.2*math.cos(a),y,29.2+3.2*math.sin(a)) for a in [j*math.tau/80 for j in range(81)]]
 pipe('Observatory rooftop halo',points,.12,'sky-crown','vista')
 pipe('Observatory halo edge',[(px,py-.14,pz) for px,py,pz in points],.035,'sky-amber','vista')
 # Rail departure vista, grounded in a long lit viaduct.
 for x in [-9,9]:
  box('Vista viaduct',(x,67,-2.0),(4.8,66,.65),'sky-near','vista',.08)
  for dx in [-1.3,1.3]:pipe('Distant rail luminous seam',[(x+dx,34,-1.6),(x+dx,96,-1.6)],.035,'sky-cyan','vista')
  for yy in [40,54,68,82]:box('Viaduct pier',(x,yy,-6.6),(.8,.8,9),'sky-near','vista',.05)
 sphere('Rail city moon',(12,126,38),(4.0,.3,4.0),'moon','vista')
