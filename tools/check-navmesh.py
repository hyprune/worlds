#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Recast/Detour navmesh audit of a world package's exported collision.

Builds two navmeshes from the collision triangles (recast-navigation-js,
tools/navmesh/): a *design* mesh with the RFC-0004 route slope (0.4) that the
gates use, and a *physical* mesh with core's walker support limit
(normal.y > 0.65) that only reveals steep ground the walker can still climb.
Agent: radius 0.3, height 1.8, eye 1.7, climb 0.35 (core player.step_height).

Gates (all against the default spawn's navmesh island):
- every spawn and route node stands on the navmesh;
- every route edge and every stair lane is a straight, unobstructed walk on
  the navmesh surface (Detour raycast), endpoint to endpoint;
- every screen anchor has a reachable approach floor in front of it within
  its declared clearance, from which the eye sees it at <= 60 deg elevation;
- clear width along routes >= DOOR (1.2 m) at every sample;
- islands a player can enter on foot must be declared: roofs/ledges of
  PROP_AREA or more reachable by a jump, and any pit a walker can drop into
  but not jump out of (a trap). Smaller jump-up tops (desks, benches) and
  islands reachable only by flying are reported, not gated;
- reachable floor whose eye point lies outside every visibility area (core
  then draws everything) must be declared;
- unguarded drops: along every boundary edge of the reachable navmesh on a
  deck at least DECK_GATE high, a drop of DROP_GATE or more just beyond the
  edge needs a guard: collision at 0.5 or 0.9 m that is not an invisible
  playable backstop (rails carry Guard collision; walls are visible).
  'backstop-only' (a fall stopped by an invisible wall) fails like
  'unguarded'. Lower decks and drops of DROP_REPORT..DROP_GATE are reported.
Steep ground the walker still climbs (0.4 < slope, normal.y > 0.65) is
reported. Stair lanes sit 2 cells inside the flight's capsule limit so voxel
rounding of the side walls does not read as a block.

Collision only: render-only geometry (the 0.7.0 capped stair) is invisible
here by construction; tools/check-route-clearance.py covers that.
"""
import argparse,json,math,sys,time
from pathlib import Path
import numpy as np
sys.path.insert(0,str(Path(__file__).parent))
from gltf_io import Scene
from raycast import Triangles
import navmesh_io

RADIUS,HEIGHT,EYE,CLIMB=.3,1.8,1.7,.35   # RFC-0004 capsule; core Camera.hpp, Config.cpp step_height
DESIGN_SLOPE=math.degrees(math.atan(.4))  # RFC-0004 / check-walking route slope
PHYSICAL_SLOPE=math.degrees(math.acos(.65))  # core Camera.cpp grounded contact
JUMP=5**2/(2*9.81)                        # core jumpSpeed 5 m/s: apex 1.27 m
JUMP_REACH=1.5                            # horizontal gap a jump clears safely
DOOR=1.2                                  # proposed door clear width (research doc §C)
PROP_AREA=4.0                             # m2; smaller jump-up tops are furniture
DROP_GATE=7.5;DECK_GATE=6.0;DROP_REPORT=2.0  # m: gated drops from raised decks (nominal 8 m+ measures ~7.9) / reported drops
MAX_ELEVATION=60                          # deg from eye to screen centre
CELL=.1;STEP=.05;SAMPLE=.5
TOL=(.15,.5,.15)                          # point-on-mesh search half extents

p=argparse.ArgumentParser(description=__doc__,formatter_class=argparse.RawDescriptionHelpFormatter)
p.add_argument('package',type=Path);p.add_argument('--allow',type=Path,help='reviewed allow-list JSON')
p.add_argument('--output',type=Path);p.add_argument('--svg',type=Path);a=p.parse_args()
s=Scene(a.package);m=s.manifest;ext=m.get('extensions',{})
def namespace(suffix):return next((v for k,v in ext.items() if k.endswith(suffix)),{})
allow=json.loads(a.allow.read_text()) if a.allow else {}
navmesh_io.require_helper()

tri=navmesh_io.collision_triangles(s)
C=object.__new__(Triangles);C._set(tri,np.array(['collision']*len(tri)),np.ones(len(tri),bool))
# Guards: collision other than the invisible playable backstops (vertical
# pieces down to playable-volumes.json's backstopBottom, -20 m). Every rail
# carries its own Guard collision box; walls are visible by construction.
backstop=(tri[:,:,1].min(axis=1)<=-19.99)&(np.abs(np.cross(tri[:,1]-tri[:,0],tri[:,2]-tri[:,0])[:,1])<1e-6)
G=object.__new__(Triangles);G._set(tri[~backstop],np.array(['guard']*int((~backstop).sum())),np.ones(int((~backstop).sum()),bool))

def build(slope,points=(),rays=(),widths=()):return navmesh_io.build(tri,slope,points,rays,widths)

def rnd(v,n=2):return [round(float(x),n) for x in v]
def yaw_normal(q):
 x,y,z,w=q;n=np.array([2*(x*z+y*w),2*(y*z-x*w),1-2*(x*x+y*y)]);return n

# ---- intent from the manifest -------------------------------------------
spawns={sp['id']:np.array(sp['pose']['position'],float) for sp in m['spawns']}
default=m.get('defaultSpawn',m['spawns'][0]['id'])
routes=namespace('.routes');nodes={n['id']:np.array(n['position'],float) for n in routes.get('nodes',[])}
edges=[(e['from'],e['to'],e.get('width',.6)) for e in routes.get('edges',[])]
stairs=namespace('.stairs').get('paths',[])
from world_contract import homes
mounts={r['anchorId']:r for r in homes(m)[1]}
anchors=[]
for an in m['anchors']:
 r=mounts.get(an['id'],{});n=yaw_normal(an['pose']['rotation']);h=np.array([n[0],0,n[2]])
 if np.linalg.norm(h)<.3:continue   # ceiling/floor screens have no floor approach
 depth=r.get('clearanceMeters',16 if r.get('role')=='mounted-workspace' else 4)
 anchors.append(dict(id=an['id'],role=r.get('role','window'),pos=np.array(an['pose']['position'],float),size=an['size'],normal=h/np.linalg.norm(h),depth=depth))

points=[{'id':'spawn:'+k,'p':v.tolist(),'h':TOL} for k,v in spawns.items()]+[{'id':'node:'+k,'p':v.tolist(),'h':TOL} for k,v in nodes.items()]
rays=[{'id':f'edge:{f}>{t}','a':nodes[f].tolist(),'b':nodes[t].tolist(),'h':TOL} for f,t,_ in edges]
for st in stairs:
 fa,fb=np.array(st['from'],float),np.array(st['to'],float);d=fb-fa;side=np.array([-d[2],0,d[0]]);side/=np.linalg.norm(side)
 off=max(0.,st['width']/2-RADIUS-2*CELL)
 for lane in sorted({-off,0.,off}):rays.append({'id':f'stair:{st["id"]}@{lane:+.2f}','a':(fa+side*lane).tolist(),'b':(fb+side*lane).tolist(),'h':TOL})
for an in anchors:
 bottom=an['pos'][1]-an['size'][1]/2
 for d in np.arange(SAMPLE,an['depth']+1e-6,SAMPLE):
  q=an['pos']+an['normal']*d;points.append({'id':f'approach:{an["id"]}@{d:.2f}','p':[q[0],bottom,q[2]],'h':[.15,6.,.15]})
widths=[]
for f,t,_ in edges:
 A,B=nodes[f],nodes[t];d=B-A;L=np.hypot(d[0],d[2])
 if L<1e-6:continue
 side=np.array([-d[2],0,d[0]])/L
 for k in range(1,max(2,int(L/SAMPLE))):
  u=k/max(2,int(L/SAMPLE));widths.append({'id':f'{f}>{t}@{u:.3f}','p':(A+d*u).tolist(),'side':side.tolist(),'reach':10})

t0=time.time()
phys=build(PHYSICAL_SLOPE,points=[{'id':'default','p':spawns[default].tolist(),'h':TOL}])
pcent=[{'id':f'phys:{i}','p':q['v'].mean(axis=0).tolist(),'h':[.3,.4,.3]} for i,q in enumerate(phys['polys'])]
nav=build(DESIGN_SLOPE,points+pcent,rays,widths)
elapsed=time.time()-t0
P={q['id']:q['hit'] for q in nav['points']}
main=P['spawn:'+default]['island'] if P.get('spawn:'+default) else None
failures=[];accepted=[];info={}
def fail(kind,ident,**kw):
 # Allow-list entries pin exact ids; area findings also pin a maximum area,
 # so any growth or any new location still fails. Reported, not hidden.
 entry=next((e for e in allow.get('accept',[]) if f'{kind}:{ident}' in e['ids'] and kw.get('area',0)<=e.get('maxArea',math.inf)),None)
 if entry:entry.setdefault('_used',set()).add(f'{kind}:{ident}');accepted.append({'kind':kind,'id':ident,**kw,'reason':entry['reason']})
 else:failures.append({'kind':kind,'id':ident,**kw})

def on_main(hit,want):
 if hit is None:return 'off navmesh (none within %.2f m across, %.1f m vertically)'%(TOL[0],TOL[1])
 if hit['island']!=main:return f'island {hit["island"]} (not the default spawn island)'
 return None

# ---- points ---------------------------------------------------------------
for k,v in spawns.items():
 e=on_main(P['spawn:'+k],v)
 if e:fail('spawn',k,position=rnd(v),error=e)
for k,v in nodes.items():
 e=on_main(P['node:'+k],v)
 if e:fail('node',k,position=rnd(v),error=e)

# ---- edges and stair lanes: straight walk on the surface -----------------
rayrows=[]
for r in nav['rays']:
 kind,ident=r['id'].split(':',1);src=next(x for x in rays if x['id']==r['id'])
 start,end=r['start'],r['end'];row={'id':ident}
 if not start or not end or start['island']!=main or end['island']!=main:
  row['error']='endpoint off the main navmesh: '+', '.join(n for n,h in [('start',start),('end',end)] if not h or h['island']!=main)
 else:
  A=np.array(start['point']);B=np.array(end['point']);straight=float(np.linalg.norm(B-A))
  row.update(clear=round(r['t'],3),straight=round(straight,2),path=None if r['pathLength'] is None else round(r['pathLength'],2))
  if r['t']<1:row['error']='blocked';row['blockedAt']=rnd(A+(B-A)*r['t'])
 rayrows.append(row)
 if 'error' in row:fail(kind,ident,**{k:v for k,v in row.items() if k!='id'})

# ---- screen approaches ----------------------------------------------------
approach=[]
for an in anchors:
 reach=[]
 for d in np.arange(SAMPLE,an['depth']+1e-6,SAMPLE):
  h=P[f'approach:{an["id"]}@{d:.2f}']
  if h and h['island']==main:
   eye=np.array(h['point'])+[0,EYE,0];v=an['pos']-eye;elev=math.degrees(math.atan2(v[1],math.hypot(v[0],v[2])))
   reach.append((round(float(d),2),round(h['point'][1],2),round(elev,1)))
 ok=[r for r in reach if r[0]>=1 and abs(r[2])<=MAX_ELEVATION]
 row={'id':an['id'],'role':an['role'],'depth':an['depth'],'reachableSamples':len(reach),
  'approach':ok[0] if ok else None,'standback':ok[-1] if ok else None}
 approach.append(row)
 if not ok:fail('approach',an['id'],role=an['role'],depth=an['depth'],error='no reachable floor in front within its clearance at <= %d deg elevation'%MAX_ELEVATION,samples=reach[:6])

# ---- chokepoints ----------------------------------------------------------
# The eroded navmesh width is only good to ~2 cells (it moves with the voxel
# grid phase), so it nominates candidates; the gate is the exact clear width
# between collision faces, from horizontal rays across the route at five
# heights between step height and head height.
def clear_width(pt,side,reach=10):
 best=[reach,reach]
 for h in np.linspace(CLIMB+.05,HEIGHT-.05,5):
  o=np.array(pt)+[0,h,0]
  for k,sg in enumerate((1,-1)):
   hit=C.first_hit(o,o+np.array(side)*sg*reach)
   if hit:best[k]=min(best[k],hit['t']*reach)
 return sum(best)
narrow={}
for w,src in zip(nav['widths'],widths):
 if not w['hit'] or w['hit']['island']!=main:continue
 approx=w['left']+w['right']+2*RADIUS;edge,u=w['id'].rsplit('@',1)
 r=narrow.setdefault(edge,{'min':99.,'at':None,'samples':0,'below':0});r['samples']+=1
 width=clear_width(w['hit']['point'],src['side']) if approx<DOOR+4*CELL else approx
 if width<r['min']:r.update(min=round(width,2),at=rnd(w['hit']['point']))
 r['below']+=width<DOOR
for edge,r in narrow.items():
 if r['below']:fail('chokepoint',edge,minWidth=r['min'],at=r['at'],samplesBelow=r['below'],samples=r['samples'],metric=DOOR)

# ---- islands --------------------------------------------------------------
polys=nav['polys'];mainv=np.concatenate([q['v'] for q in polys if q['island']==main])
areas=[(np.array(z['bounds']['min']),np.array(z['bounds']['max'])) for z in (m.get('visibility',{}).get('areas') or m.get('zones',[]))]
def declared(pt):return any(np.all(pt>=lo) and np.all(pt<=hi) for lo,hi in areas)
def zone_of(pt):
 return next((z['id'] for z in m.get('zones',[]) if np.all(pt>=np.array(z['bounds']['min'])-1) and np.all(pt<=np.array(z['bounds']['max'])+1)),None)
islands=[]
for k in sorted({q['island'] for q in polys}-{main}):
 own=[q for q in polys if q['island']==k];v=np.concatenate([q['v'] for q in own]);area=sum(q['area'] for q in own)
 lo,hi=v.min(axis=0),v.max(axis=0)
 # Island vertex vs nearby main-mesh vertex: how a walker could get there.
 # A clear horizontal collision ray just above the higher floor (jump) or
 # at knee height from the main floor (walk off) makes the pair usable.
 dh=np.hypot(v[:,None,0]-mainv[None,:,0],v[:,None,2]-mainv[None,:,2]);dy=v[:,None,1]-mainv[None,:,1]
 near=dh<=JUMP_REACH;how='fly-only';at=None
 for i,j in zip(*np.nonzero(near&(dy>CLIMB)&(dy<=JUMP))):
  if not C.first_hit(np.array([mainv[j][0],v[i][1]+.3,mainv[j][2]]),v[i]+[0,.3,0]):how='jump-up';at=v[i];break
 if how=='fly-only':
  for i,j in sorted(zip(*np.nonzero(near&(dy<-CLIMB))),key=lambda ij:-dy[ij]):
   top=np.array([v[i][0],mainv[j][1]+.6,v[i][2]])
   # Walk off clear, and nothing between the fall and the landing (a closed
   # solid's interior floor is an island too, but nobody lands in it).
   if not C.first_hit(mainv[j]+[0,.6,0],top) and not C.first_hit(top,v[i]+[0,.05,0]):how='step-down' if dy[i,j]>=-JUMP else 'drop-in';at=v[i];break
 row={'island':int(k),'area':round(area,2),'min':rnd(lo,1),'max':rnd(hi,1),'reach':how,'zone':zone_of((lo+hi)/2)}
 if at is not None:row['at']=rnd(at)
 islands.append(row)
 if how=='drop-in' or (how=='jump-up' and area>=PROP_AREA):fail('island',f'{row["zone"] or "outside"}@{rnd((lo+hi)/2,0)}',**{k:row[k] for k in ('area','reach','at','min','max')})

# Unguarded drops along the reachable navmesh boundary.
samples=[]
for q in polys:
 if q['island']!=main:continue
 v=q['v'];c=v.mean(axis=0);n=len(v)
 for j in range(n):
  if not q['open'][j]:continue
  A,B=v[j],v[(j+1)%n];d=B-A;L=float(np.hypot(d[0],d[2]))
  if L<.05:continue
  out=np.array([d[2],0,-d[0]])/L
  if np.dot(out[[0,2]],((A+B)/2-c)[[0,2]])<0:out=-out
  for t in np.linspace(0,1,max(2,int(L/.5)+1)):
   pt=A+d*t;probe=pt+out*.8;hit=C.first_hit(np.array([probe[0],pt[1]+.3,probe[2]]),np.array([probe[0],pt[1]-60,probe[2]]))
   drop=60.0 if hit is None else pt[1]-hit['point'][1]
   if drop<DROP_REPORT:continue
   guard=any(G.first_hit(pt+[0,h,0],pt+[0,h,0]+out*1.1) for h in (.5,.9))
   wall=guard or any(C.first_hit(pt+[0,h,0],pt+[0,h,0]+out*1.1) for h in (.5,.9))
   kind='guarded' if guard else 'backstop-only' if wall else 'unguarded'
   samples.append((pt,out,drop,kind))
# Cluster unguarded samples into edge runs (same kind, same deck, within 1.2 m).
runs=[]
for pt,out,drop,kind in samples:
 if kind=='guarded':continue
 r=next((r for r in runs if r['kind']==kind and abs(r['deck']-pt[1])<.6 and min(np.hypot(*(np.array(x)-pt)[[0,2]]) for x in r['points'])<1.2),None)
 if r is None:r={'kind':kind,'deck':float(pt[1]),'points':[],'drops':[]};runs.append(r)
 r['points'].append(pt.round(2).tolist());r['drops'].append(round(float(drop),1))
drops=[]
for r in runs:
 RP=np.array(r['points']);row={'kind':r['kind'],'deck':round(r['deck'],2),'drop':[min(r['drops']),max(r['drops'])],'min':RP.min(axis=0).round(1).tolist(),'max':RP.max(axis=0).round(1).tolist(),'samples':len(RP),'zone':zone_of(RP.mean(axis=0))}
 drops.append(row)
 if r['deck']>=DECK_GATE and max(r['drops'])>=DROP_GATE:fail('unguarded-drop',f"{row['zone'] or 'outside'}@{rnd(RP.mean(axis=0),0)}",guard=row['kind'],**{k:row[k] for k in ('deck','drop','min','max','samples')})
info['unguardedDrops']=sorted(drops,key=lambda r:-r['drop'][1])
info['dropSamples']={k:sum(1 for *_,x in samples if x==k) for k in ('guarded','backstop-only','unguarded')}

# Reachable floor whose eye point is outside every visibility area.
outside=[q for q in polys if q['island']==main and not declared(q['v'].mean(axis=0)+[0,EYE,0])]
if outside:
 v=np.concatenate([q['v'] for q in outside])
 fail('undeclared-space','main',area=round(sum(q['area'] for q in outside),2),min=rnd(v.min(axis=0),1),max=rnd(v.max(axis=0),1),polys=len(outside),examples=[rnd(q['v'].mean(axis=0),1) for q in sorted(outside,key=lambda q:-q['area'])[:6]])

# Steep ground (0.4 < slope, normal.y > 0.65) the walker reaches from spawn.
pmain=P and next((q['hit']['island'] for q in phys['points'] if q['hit']),None)
steep=[i for i,q in enumerate(phys['polys']) if q['island']==pmain and not P.get(f'phys:{i}')]
info['steepReachable']={'polys':len(steep),'area':round(sum(phys['polys'][i]['area'] for i in steep),2),
 'examples':[rnd(phys['polys'][i]['v'].mean(axis=0),1) for i in sorted(steep,key=lambda i:-phys['polys'][i]['area'])[:8]]}

for e in allow.get('accept',[]):
 for ident in set(e['ids'])-e.get('_used',set()):failures.append({'kind':'stale-allow','id':ident,'error':'allow-list entry no longer matches a finding; remove it'})
mainarea=sum(q['area'] for q in polys if q['island']==main)
report={'status':'FAIL' if failures else 'PASS','package':str(a.package),'world':m['id'],'version':m.get('version'),
 'method':__doc__.strip(),'library':'recast-navigation-js 0.43.1 (Recast/Detour, zlib; wrapper MIT)',
 'agent':{'radius':RADIUS,'height':HEIGHT,'eye':EYE,'climb':CLIMB,'designSlopeDeg':round(DESIGN_SLOPE,2),'physicalSlopeDeg':round(PHYSICAL_SLOPE,2),'jumpApex':round(JUMP,2)},
 'voxel':{'cell':CELL,'step':STEP},'seconds':round(elapsed,1),
 'navmesh':{'polys':len(polys),'islands':nav['islands'],'mainArea':round(mainarea,1),'physicalPolys':len(phys['polys'])},
 'counts':{'spawns':len(spawns),'nodes':len(nodes),'edges':len(edges),'stairLanes':sum(r['id'].startswith('stair:') for r in rays),'anchors':len(anchors),'widthSamples':len(widths)},
 'failures':failures,'acceptedByAllowList':accepted,'islands':islands,'approaches':approach,
 'chokepoints':sorted([{'edge':k,**v} for k,v in narrow.items()],key=lambda r:r['min'])[:12],'walks':rayrows,**info}
def where(f):
 """World xz points that locate a finding on the map."""
 if f['kind'] in ('spawn','node'):return [f['position']]
 if f['kind'] in ('edge','stair'):
  if 'blockedAt' in f:return [f['blockedAt']]
  r=next(x for x in rays if x['id']==f['kind']+':'+f['id']);return [r['a'],r['b']]
 if f['kind']=='approach':return [next(an['pos'] for an in anchors if an['id']==f['id'])]
 if f['kind']=='chokepoint':return [f['at']]
 if f['kind']=='island':return [f.get('at') or [(f['min'][i]+f['max'][i])/2 for i in range(3)]]
 return f.get('examples',[])

def draw(path):
 """Top-down plan (x right, -z up): navmesh by height, islands, routes,
 stairs, spawns, screens with approach/standback, numbered findings."""
 allp=np.concatenate([q['v'] for q in polys]+[np.array(list(nodes.values()) or [[0,0,0]])]);lo=allp.min(axis=0)-4;hi=allp.max(axis=0)+4
 scale=min(1600/(hi[0]-lo[0]),1600/(hi[2]-lo[2]));W=(hi[0]-lo[0])*scale;H=(hi[2]-lo[2])*scale+170
 X=lambda v:f'{(v[0]-lo[0])*scale:.1f}';Z=lambda v:f'{(v[2]-lo[2])*scale+60:.1f}'
 ylo,yhi=min(q['v'][:,1].min() for q in polys),max(q['v'][:,1].max() for q in polys)
 def shade(y):t=(y-ylo)/max(yhi-ylo,1e-6);return f'hsl({200-150*t:.0f},45%,{30+40*t:.0f}%)'
 o=[f'<svg xmlns="http://www.w3.org/2000/svg" width="{W:.0f}" height="{H:.0f}" font-family="sans-serif" font-size="11">',
  f'<rect width="100%" height="100%" fill="#14171c"/>',
  f'<text x="8" y="20" fill="#eee" font-size="15">{m["id"]} {m.get("version","")} navmesh: {report["status"]}, {len(failures)} failing, {len(accepted)} allow-listed</text>',
  f'<text x="8" y="40" fill="#aaa">agent r{RADIUS} h{HEIGHT} climb {CLIMB} slope {DESIGN_SLOPE:.1f} deg; floor colour = height {ylo:.1f}..{yhi:.1f} m (blue low, yellow high)</text>',
  f'<text x="8" y="54" fill="#aaa">translucent grey = fly-only island (roofs); amber = jump-up top; red fill = gated island; purple = steep but climbable; dashed = visibility areas; white = routes; blue = stairs; cyan = screens + approach</text>']
 for lo2,hi2 in areas:o.append(f'<rect x="{X(lo2)}" y="{Z(lo2)}" width="{(hi2[0]-lo2[0])*scale:.1f}" height="{(hi2[2]-lo2[2])*scale:.1f}" fill="none" stroke="#556" stroke-dasharray="4 4"/>')
 steepset=set(steep)
 for i,q in enumerate(phys['polys']):
  if i in steepset:o.append('<polygon points="'+' '.join(f'{X(v)},{Z(v)}' for v in q['v'])+'" fill="#a050d0" opacity=".7"/>')
 kinds={r['island']:r['reach'] for r in islands}
 # Off-main islands (often roofs over walkable floor) stay translucent
 # underneath, so the reachable mesh is never hidden.
 for q in sorted(polys,key=lambda q:(q['island']==main,q['v'][:,1].mean())):
  k=kinds.get(q['island']);main_=q['island']==main
  fill=shade(q['v'][:,1].mean()) if main_ else ('#8a8f96' if k=='fly-only' else '#d9a030' if k in('jump-up','step-down') else '#e04040')
  o.append('<polygon points="'+' '.join(f'{X(v)},{Z(v)}' for v in q['v'])+f'" fill="{fill}" fill-opacity="{1 if main_ else .35}" stroke="{"#0004" if main_ else fill}" stroke-width=".6"/>')
 for st in stairs:
  fa,fb=st['from'],st['to'];o.append(f'<line x1="{X(fa)}" y1="{Z(fa)}" x2="{X(fb)}" y2="{Z(fb)}" stroke="#4aa8ff" stroke-width="{max(2,st["width"]*scale*.6):.1f}" opacity=".55"/>')
 bad={f['id'] for f in failures}
 for f,t,_ in edges:
  A,B=nodes[f],nodes[t];c='#ff3030' if f'{f}>{t}' in bad else '#ffffff';o.append(f'<line x1="{X(A)}" y1="{Z(A)}" x2="{X(B)}" y2="{Z(B)}" stroke="{c}" stroke-width="1.6"/>')
 for k,v in nodes.items():o.append(f'<circle cx="{X(v)}" cy="{Z(v)}" r="2.6" fill="{"#ff3030" if k in bad else "#fff"}"/>')
 for an,row in zip(anchors,approach):
  half=np.array([an['normal'][2],0,-an['normal'][0]])*an['size'][0]/2;a1,a2=an['pos']-half,an['pos']+half
  o.append(f'<line x1="{X(a1)}" y1="{Z(a1)}" x2="{X(a2)}" y2="{Z(a2)}" stroke="#30e0e0" stroke-width="3"/>')
  if row['standback']:
   sb=an['pos']+an['normal']*row['standback'][0];o.append(f'<line x1="{X(an["pos"])}" y1="{Z(an["pos"])}" x2="{X(sb)}" y2="{Z(sb)}" stroke="#30e0e0" stroke-dasharray="2 3"/><circle cx="{X(sb)}" cy="{Z(sb)}" r="2" fill="#30e0e0"/>')
 spots={}
 for k,v in spawns.items():spots.setdefault(tuple(np.round(v,1)),[]).append(k)
 for v,ks in spots.items():o.append(f'<circle cx="{X(v)}" cy="{Z(v)}" r="{6 if default in ks else 4}" fill="#40e070" stroke="#000"/><text x="{float(X(v))+7:.1f}" y="{Z(v)}" fill="#7f7">{" / ".join(ks)}</text>')
 for n,f in enumerate(failures+accepted,1):
  c='#ff3030' if n<=len(failures) else '#ffb030'
  for v in where(f):o.append(f'<circle cx="{X(v)}" cy="{Z(v)}" r="8" fill="none" stroke="{c}" stroke-width="2"/><text x="{float(X(v))+9:.1f}" y="{float(Z(v))-6:.1f}" fill="{c}" font-weight="bold">{n}</text>')
 y=H-110
 for n,f in enumerate(failures+accepted,1):
  if n>9:o.append(f'<text x="8" y="{y}" fill="#aaa">… {len(failures)+len(accepted)-9} more in the JSON report</text>');break
  label=f"{n}. {'FAIL' if n<=len(failures) else 'allowed'} {f['kind']} {f['id']}: {f.get('error') or f.get('reach') or ''}"
  o.append(f'<text x="8" y="{y}" fill="{"#ff6060" if n<=len(failures) else "#ffb030"}">{label.replace("&","&amp;").replace("<","&lt;")}</text>');y+=12
 o.append('</svg>');path.parent.mkdir(parents=True,exist_ok=True);path.write_text('\n'.join(o)+'\n')
if a.svg:draw(a.svg);report['svg']=str(a.svg)
text=json.dumps(report,indent=1)+'\n'
if a.output:a.output.parent.mkdir(parents=True,exist_ok=True);a.output.write_text(text)
print(json.dumps({k:report[k] for k in ['status','world','version','seconds','navmesh','counts']}|{'failures':[{k:f[k] for k in f if k in('kind','id','error','reach','area','minWidth')} for f in failures],'accepted':len(accepted),'steepReachable':info['steepReachable']['area']},indent=1))
sys.exit(1 if failures else 0)
