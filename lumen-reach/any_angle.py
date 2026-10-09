# SPDX-License-Identifier: MIT
"""Closed skies, three-dimensional watershed and exposed architectural finishes."""
import math,json
from mathutils import Vector


def image_material(B,name,filename):
 m=B.mat(name,(1,1,1),unlit=True);nt=m.node_tree
 t=nt.nodes.new('ShaderNodeTexImage');t.image=B.bpy.data.images.load(str(B.HERE/'materials/tiles'/filename));t.extension='REPEAT'
 uv=nt.nodes.new('ShaderNodeUVMap');uv.uv_map='UV0';nt.links.new(uv.outputs['UV'],t.inputs['Vector'])
 em=next(n for n in nt.nodes if n.type=='EMISSION');nt.links.new(t.outputs['Color'],em.inputs['Color'])
 return m


def sphere(B,name,center,radii,material,inside=True,segments=128,rings=48,seam=-math.pi,power=2):
 # Explicit single-vertex poles and welded longitude closure: no degenerate
 # polar quads or open boundary. UV discontinuity lives on loops, not geometry.
 # `seam` is the azimuth (from +Y towards +X) of u=0. power>2 squares off the
 # horizontal section (superellipse) while UVs stay on the direction's
 # latitude/longitude, so the texture mapping is unchanged.
 verts=[(center[0],center[1],center[2]-radii[2])];uvs=[(.5,0)];faces=[]
 for k in range(1,rings):
  lat=-math.pi/2+k*math.pi/rings
  for j in range(segments):
   a=seam+j/segments*math.tau;n=(math.cos(lat)*math.sin(a),math.cos(lat)*math.cos(a),math.sin(lat))
   r=1/math.sqrt((abs(n[0])**power+abs(n[1])**power)**(2/power)+n[2]**2)
   verts.append(tuple(center[i]+radii[i]*n[i]*r for i in range(3)))
   uvs.append((j/segments,k/rings))
 top=len(verts);verts.append((center[0],center[1],center[2]+radii[2]));uvs.append((.5,1))
 for j in range(segments):
  nj=(j+1)%segments;faces.append((0,1+j,1+nj))
  for k in range(rings-2):
   q=1+k*segments;faces.append((q+j,q+segments+j,q+segments+nj,q+nj))
  q=1+(rings-2)*segments;faces.append((q+j,top,q+nj))
 # This longitude convention produces outward winding; sky faces inward.
 if inside:faces=[tuple(reversed(f)) for f in faces]
 o=B.mesh(name,verts,faces,material,group='vista')
 for p in o.data.polygons:
  vals=[uvs[i] for i in p.vertices];cross=any(u<.1 for u,v in vals) and any(u>.9 for u,v in vals)
  for li,vi in zip(p.loop_indices,p.vertices):
   u,v=uvs[vi]
   if cross and u<.1:u+=1
   if vi in [0,top]:
    neighbours=[uvs[i][0]+(1 if cross and uvs[i][0]<.1 else 0) for i in p.vertices if i not in [0,top]];u=sum(neighbours)/len(neighbours)
   o.data.uv_layers[0].data[li].uv=(u,v)
 return o


def shade(B,o,names):
 # Portable baked face lighting. Core does not consume vertex colors. Share
 # three textured material batches across the distant kit instead of fake PBR.
 for name in names[1:]:o.data.materials.append(B.P.MATS[name])
 for p in o.data.polygons:
  light=p.normal.dot(Vector((-.45,-.5,.74)))
  p.material_index=0 if light>.3 else 1 if light>-.25 else 2
 return o


def materials(B):
 for name,col in [('land-sun',(.56,.60,.57)),('land-mid',(.38,.46,.48)),('land-shade',(.23,.31,.34))]:
  B.mat(name,col,'rock',unlit=True,tint=True);B.P.TILE_METERS[name]=12
 for name,col in [('cascade-sun',(.65,.59,.45)),('cascade-mid',(.39,.41,.38)),('cascade-shade',(.20,.27,.29))]:
  B.mat(name,col,'concrete',unlit=True,tint=True);B.P.TILE_METERS[name]=2
 B.P.MATS['canvas']['lumenAlbedoTint']=[.55,.43,.31]
 B.mat('land-snow',(.55,.65,.72),'snow',unlit=True,tint=True);B.P.TILE_METERS['land-snow']=8
 B.mat('roofing',(.26,.30,.32),'paving',rough=.85,tint=True);B.P.TILE_METERS['roofing']=2
 B.mat('soffit',(.72,.76,.74),'concrete',rough=.85,tint=True);B.P.TILE_METERS['soffit']=2


# Signal Rise's closed sky. A plain ellipsoid's south wall met the yard rail
# only at x=57: the yard corners (29|85, 112) stood outside the basin, seeing
# past its culled back. A squared-off (power 4) section keeps every yard eye
# inside, with the south wall 0.4-0.8 m beyond the y=112 guard rail.
NIGHT_CENTER=(57,170,0);NIGHT_RADII=(70,58.8,76);NIGHT_POWER=4


def night(B):
 # The painted 40 m flat lid is replaced by a closed sky inside a textured
 # mountain shell. From the yard it is a cold basin; from above it is rock.
 image_material(B,'night-sky-v7','night-sky-v7-albedo.png')
 sphere(B,'Signal closed basin sky',NIGHT_CENTER,NIGHT_RADII,'night-sky-v7',segments=96,rings=32,power=NIGHT_POWER)
 o=sphere(B,'Signal mountain outer shell',NIGHT_CENTER,tuple(r+1.5 for r in NIGHT_RADII),'land-sun',inside=False,segments=96,rings=32,power=NIGHT_POWER)
 # Break the ellipsoid into broad crags while keeping the entire shell outside
 # its smooth inner surface; closed silhouette is intentional from every side.
 for v in o.data.vertices:
  p=v.co-Vector((57,170,0));r=math.atan2(p.x,p.y)
  scale=1+.09*(math.sin(r*7+p.z*.08)**2)+.035*math.sin(r*13)**2
  v.co=Vector((57,170,0))+p*scale
  # Crags never reach past the Vault's rear shell or the stair tunnel mouth.
  v.co.y=max(v.co.y,102.8)
 o.data.update()
 for p in o.data.polygons:
  axes=[a for a in range(3) if a!=max(range(3),key=lambda a:abs(p.normal[a]))]
  for li in p.loop_indices:
   v=o.data.vertices[o.data.loops[li].vertex_index].co;o.data.uv_layers[0].data[li].uv=(v[axes[0]]/12,v[axes[1]]/12)
 shade(B,o,['land-sun','land-mid','land-shade'])
 o.data.materials.append(B.P.MATS['land-snow'])
 for p in o.data.polygons:
  if p.center.z>48 and p.normal.z>.4:p.material_index=3


# The panorama's only seam (the painting's left/right edges) faces the Signal
# massif: from every walkable eye the massif hides its landscape band. 0.7.0
# put it due south, centred in the Sun Court's main outward view.
DAY_SEAM=math.atan2(57-20,170-65)


def vista(B):
 image_material(B,'sky-v7','sky-v7-albedo.png')
 sphere(B,'Watershed complete sky',(20,65,0),(310,310,310),'sky-v7',seam=DAY_SEAM)
 # Continuous terrain disk: deep valley under the settlement, then a bowl
 # that keeps falling outward. 0.7.0's outer shelves (r>=174 m) crested near
 # eye level and banded flat grey across the painted valley; beyond the
 # settlement the terrain now stays >=6 degrees below every walkable eye.
 segments=128;verts=[(20,65,-14)];faces=[]
 radii=[28,56,82,108,140,174,215,258,292]
 for k,r in enumerate(radii):
  for j in range(segments):
   a=j/segments*math.tau;wave=math.sin(a*7+k*.7)**2
   h=[-14,-15,-28,-62,-70,-76,-80,-84,-88][k]
   amp=[0,0,2,6,10,6,4,2,0][k]
   z=h+amp*wave+amp*.35*math.sin(a*13+k)
   verts.append((20+r*math.sin(a),65+r*.76*math.cos(a),z))
 for j in range(segments):faces.append((0,1+(j+1)%segments,1+j))
 for k in range(len(radii)-1):
  for j in range(segments):
   q=1+k*segments;n=(j+1)%segments;faces.extend([(q+j,q+n,q+segments+n),(q+j,q+segments+n,q+segments+j)])
 o=B.mesh('Watershed solid valley shelves',verts,faces,'land-sun',group='vista');shade(B,o,['land-sun','land-mid','land-shade'])
 # Settlement plinths end in rough sloping rock, not unsupported paper floors.
 for name,x0,x1,y0,y1,z in [('Court',-25,27,-17,27,-.38),('Hall',-14,28,31,63,-.38),('Vault',25,57,73,104,-6.4),('Rise',28,86,111,162,-.38)]:
  v=[(x0,y0,z),(x1,y0,z),(x1,y1,z),(x0,y1,z),(x0-4,y0-4,-17),(x1+5,y0-3,-19),(x1+3,y1+4,-18),(x0-5,y1+5,-16)]
  o=B.mesh(name+' cliff foundations',v,[(0,1,2,3),(0,4,5,1),(1,5,6,2),(2,6,7,3),(3,7,4,0),(7,6,5,4)],'land-sun',group='vista');shade(B,o,['land-sun','land-mid','land-shade'])
 # Solid voussoir arches with two faces, deep intrados, pier bases and cornices.
 for x in range(-87,-20,6):
  for z,w,d,h in [(-37.5,1.7,4,85),(4,1.25,3.4,2),(8.8,1.8,3.9,.5)]:
   o=B.box('Cascade dressed pier',(x,63,z),(w,d,h),'cascade-sun',.05,group='vista');shade(B,o,['cascade-sun','cascade-mid','cascade-shade'])
  if x==-21:continue
  for j in range(12):
   a=math.pi*j/12+.006;b=math.pi*(j+1)/12-.006;v=[]
   for y in [61.6,64.4]:
    for r,t in [(2.35,a),(2.35,b),(2.9,b),(2.9,a)]:v.append((x+3+r*math.cos(t),y,5+3/2.9*r*math.sin(t)))
   o=B.mesh('Cascade arch voussoir',v,[(0,3,2,1),(4,5,6,7),(0,1,5,4),(1,2,6,5),(2,3,7,6),(3,0,4,7)],'cascade-sun',group='vista');shade(B,o,['cascade-sun','cascade-mid','cascade-shade'])
   # Solid spandrel masonry fills the space from the arch extrados to deck.
   a=math.pi*j/12;b=math.pi*(j+1)/12;v=[]
   for y in [61.6,64.4]:
    v.extend([(x+3+2.9*math.cos(a),y,5+3*math.sin(a)),(x+3+2.9*math.cos(b),y,5+3*math.sin(b)),(x+3+2.9*math.cos(b),y,9.1),(x+3+2.9*math.cos(a),y,9.1)])
   o=B.mesh('Cascade spandrel',v,[(0,1,2,3),(7,6,5,4),(0,4,5,1),(1,5,6,2),(2,6,7,3),(3,7,4,0)],'cascade-mid',group='vista')

 for z,w,mat in [(9.05,3.8,'cascade-sun'),(9.42,3.6,'land-mid')]:
  o=B.box('Cascade stone deck',(-54,63,z),(66,w,.38),mat,.06,group='vista')
  if mat=='cascade-sun':shade(B,o,['cascade-sun','cascade-mid','cascade-shade'])
 for y in [61.35,64.65]:
  B.box('Cascade parapet',(-54,y,9.98),(66,.24,.95),'cascade-mid',.03,group='vista')
  for x in range(-86,-22,4):B.box('Cascade coping joints',(x,y,10.48),(.13,.4,.09),'cascade-shade',0,group='vista')
 for x,y,h,w in [(5,88,31,3.8),(12,94,43,4.6),(19,98,35,3.4),(-5,92,23,3)]:
  v=[(x+dx*w,y+dy*w,-2) for dx,dy in [(-.5,-.5),(.5,-.5),(.5,.5),(-.5,.5)]]
  v += [(x+dx*w*.48,y+dy*w*.48,h*.79) for dx,dy in [(-.5,-.5),(.5,-.5),(.5,.5),(-.5,.5)]];v += [(x-.16,y,h),(x+.16,y,h)]
  o=B.mesh('Spire stone tower',v,[(3,2,1,0),(0,1,5,4),(1,2,6,5),(2,3,7,6),(3,0,4,7),(4,5,9,8),(5,6,9),(6,7,8,9),(7,4,8)],'cascade-sun',group='vista');shade(B,o,['cascade-sun','cascade-mid','cascade-shade'])
  for z in [h*.25,h*.48,h*.68]:
   width=w*(1-.52*z/(h*.79))
   for yy in [-1,1]:B.box('Spire inset ribbon',(x,y+yy*(width/2+.03),z),(width*.85,.12,.5),'cascade-shade',0,group='vista')
  B.box('Spire foundation',(x,y,-8),(w+1.7,w+1.7,18),'land-mid',.12,group='vista')


def architecture(B):
 # Change the existing roof face material, without a coplanar overlay.
 for group,objects in list(B.P.GROUPS.items()):
  if group in ['vista','foliage']:continue
  for o in list(objects):
   if o.name.startswith(('Facade rooftop','Vestibule ceiling','Roof transverse beam','Roof edge beam','Fortress room roof','Sloping service roof','Snow ascent ceiling','West lookout','Upper landing','Roof landing','Roof upper landing','Rooftop bridge','Lookout seat terrace')):
    o.data.materials.append(B.P.MATS['roofing']);idx=len(o.data.materials)-1
    for p in o.data.polygons:
     if p.normal.z>.6:p.material_index=idx
   if 'ascent' in o.name.lower() or o.name.startswith(('Roof final approach','Globe approach')):
    o.data.materials.append(B.P.MATS['soffit']);idx=len(o.data.materials)-1
    for p in o.data.polygons:
     if p.normal.z<.4:p.material_index=idx
 # The alternate stair starts receive a short supported apron before the
 # perimeter backstop; its capsule must not straddle the outside boundary.
 B.slab('Service descent stair apron',33,35.4,51.4,52,0,'metal')
 B.slab('Snow service ascent stair apron',57,59.3,99.4,100,-6,'grating')
 # Roof-mounted service pods stay outside the established walking route.
 for group,spots in [('sun-court',[(0,25.5,16),(9,25.5,16)]),('array-hall',[(23.9,40,21.6),(23.9,52,21.6)]),('signal-rise',[(56,154,20.45),(73,155,20.45)])]:
  for x,y,z in spots:
   B.box('Roof vent curb',(x,y,z+.13),(1.25,1.2,.26),'metal',.02,group=group)
   B.box('Roof extraction housing',(x,y,z+.42),(1.05,1,.5),'metal',.04,group=group)
   for dy in [-.36,-.18,0,.18,.36]:B.box('Roof louvre',(x,y+dy,z+.70),(.90,.065,.06),'strip',0,group=group)
 # Copings give the accessible roof a readable edge. No added trip seams.
 for y in [22,27]:B.box('Roof metal coping',(9,y,16.025),(31.8,.14,.07),'metal',.01,group='sun-court')
 for x in [-5.6,24]:B.box('Hall roof flashing',(x,46,21.64),(.95,27.6,.06),'metal',.01,group='array-hall')
 # Grazing fill reaches the soffits that skylight cannot illuminate.
 for x,y,z in [(-20.8,10,1),(-21.5,32,2),(-16.5,32,5),(-11.7,28,8)]:
  B.P.area('Stair soffit bounce',(x,y,z),(x,y,z+6),650,(.65,.78,1),5)


def finish_export(B,g,m):
 # Dome interiors and mountain exteriors are deliberately single sided.
 for mat in g['materials']:
  if mat['name'].split('--')[-1] in ['sky-v7','night-sky-v7','land-sun','land-mid','land-shade']:
   mat['doubleSided']=False
 # Distant terrain is emission-textured PBR, so core's fog acts on it while
 # the actual skies retain KHR_materials_unlit and are excluded from fog.
 for mat in g['materials']:
  if mat['name'].split('--')[-1] not in ['land-sun','land-mid','land-shade','land-snow']:continue
  pbr=mat['pbrMetallicRoughness'];mat['emissiveTexture']=pbr.pop('baseColorTexture');mat['emissiveFactor']=pbr['baseColorFactor'][:3];pbr['baseColorFactor']=[0,0,0,1]
  mat.get('extensions',{}).pop('KHR_materials_unlit',None);mat['doubleSided']=False
 for t in g.get('textures',[]):
  im=g['images'][t['source']].get('uri','')
  if 'sky-v7' in im:
   sampler=dict(g['samplers'][t['sampler']]);sampler.update(wrapS=10497,wrapT=33071)
   t['sampler']=len(g['samplers']);g['samplers'].append(sampler)
 # Exponential distance fog for lit architecture; sky and distant terrain carry
 # their own haze, preserving the separate cold basin treatment.
 m['atmosphere']={'fog':{'color':[.12,.18,.24],'density':.003,'heightFalloff':.015,'baseHeight':-8,'excludeUnlit':True},'sky':{'zenith':[.18,.3,.52],'horizon':[.55,.61,.65],'ground':[.055,.07,.085],'sun':{'direction':[.3,1,.5],'color':[1,.83,.6],'intensity':3,'angularRadius':.025}},'exposure':1,'toneMapping':'aces','bloom':{'strength':.12,'threshold':1,'radius':3}}
 (B.OUT/'scene.gltf').write_text(json.dumps(g,indent=2)+'\n')


def boundaries(B):
 spec=json.loads((B.HERE/'playable-volumes.json').read_text());rects=[r for area in spec['areas'] for r in area['rects']]
 xs=sorted({r[i] for r in rects for i in [0,1]});ys=sorted({r[i] for r in rects for i in [2,3]});cells=set()
 for i in range(len(xs)-1):
  for j in range(len(ys)-1):
   x=(xs[i]+xs[i+1])/2;y=(ys[j]+ys[j+1])/2
   if any(x0<x<x1 and y0<y<y1 for x0,x1,y0,y1 in rects):cells.add((i,j))
 edges=[]
 for i,j in sorted(cells):
  for di,dj,a,b in [(-1,0,(xs[i],ys[j]),(xs[i],ys[j+1])),(1,0,(xs[i+1],ys[j+1]),(xs[i+1],ys[j])),(0,-1,(xs[i+1],ys[j]),(xs[i],ys[j])),(0,1,(xs[i],ys[j+1]),(xs[i+1],ys[j+1]))]:
   if (i+di,j+dj) not in cells:edges.append((a,b,(-di,-dj)))
 # Visible guards at the previously open ground-level external edges. Guard tops count as walkable below.
 old=B.G
 for group,runs in [('sun-court',[((-24,-16,0),(-24,6,0)),((26,22,0),(26,26,0))]),('array-hall',[((-13,32,0),(-13,60,0))]),('signal-rise',[((29,112,0),(50.4,112,0)),((59.3,112,0),(85,112,0)),((85,112,0),(85,160,0)),((29,112,0),(29,143,0))])]:
  B.G=group
  for a,b in runs:B.rail(a,b)
 B.G=old
 # Backstops stop walking only: each <=2m piece rises walkClearance above the
 # highest walkable top (collision faces and prop boxes) in an inward strip.
 # Core jump lifts feet 5^2/(2*9.81)=1.27m, so ordinary fly passes overhead.
 tops=[]
 for o in B.WALK:
  w=[o.matrix_world@v.co for v in o.data.vertices]
  for p in o.data.polygons:
   c=[w[i] for i in p.vertices];n=(c[1]-c[0]).cross(c[2]-c[0])
   if n.length>1e-9 and abs(n.z)/n.length>.65:tops.append((min(v.x for v in c),max(v.x for v in c),min(v.y for v in c),max(v.y for v in c),max(v.z for v in c)))
 tops+=[(lo[0],hi[0],lo[1],hi[1],hi[2]) for name,lo,hi in B.P.COLL]
 def highest(a,b,inward,depth):
  c=[a,b,[a[0]+inward[0]*depth,a[1]+inward[1]*depth],[b[0]+inward[0]*depth,b[1]+inward[1]*depth]]
  x0=min(v[0] for v in c)-.3;x1=max(v[0] for v in c)+.3;y0=min(v[1] for v in c)-.3;y1=max(v[1] for v in c)+.3
  return max((t[4] for t in tops if t[0]<=x1 and t[1]>=x0 and t[2]<=y1 and t[3]>=y0),default=None)
 vertices=[];faces=[];lo=spec['backstopBottom'];clear=spec['walkClearance'];pieces=[]
 for a,b,inward in edges:
  k=max(1,math.ceil(math.dist(a,b)/2))
  for t in range(k):
   p=[a[i]+(b[i]-a[i])*t/k for i in [0,1]];r=[a[i]+(b[i]-a[i])*(t+1)/k for i in [0,1]]
   top=highest(p,r,inward,3);top=highest(p,r,inward,8) if top is None else top;pieces.append([p,r,top])
 # A piece with no walkable surface inside follows pieces within 3m of it.
 for piece in pieces:
  if piece[2] is None:piece[2]=max((o[2] for o in pieces if o[2] is not None and min(math.dist(u,v) for u in piece[:2] for v in o[:2])<3),default=None)
 for p,r,top in pieces:
  hi=spec['backstopFallbackTop'] if top is None else top+clear
  q=len(vertices);vertices.extend([(p[0],p[1],lo),(r[0],r[1],lo),(r[0],r[1],hi),(p[0],p[1],hi)]);faces.append((q,q+1,q+2,q+3))
 pieces=[round(spec['backstopFallbackTop'] if top is None else top+clear,3) for p,r,top in pieces]
 me=B.bpy.data.meshes.new('Playable perimeter');me.from_pydata(vertices,[],faces);o=B.bpy.data.objects.new('Playable perimeter',me);B.bpy.context.collection.objects.link(o);o.hide_render=True;B.WALK.append(o)
 spec['collisionBoundarySegments']=len(edges);spec['collisionBackstopPieces']=len(pieces);spec['backstopTopRange']=[min(pieces),max(pieces)];(B.ART/'playable-boundary-report.json').write_text(json.dumps(spec,indent=2)+'\n')
