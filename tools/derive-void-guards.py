#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Void guards: every walkable floor edge with nothing under it.

A walker who steps off a floor edge lands on whatever floor lies below. Where
no collision floor lies anywhere below (down to the playable backstopBottom),
the fall never ends: a pit inside the playable union (under a bridge, a strip
behind paving), or a fly-only roof at the world's edge, whose perimeter
backstop only rises above walk-reachable tops. tools/check-fall-through.py
finds these with core's walker; this tool lists the edges to guard.

The floor is the physical Recast navmesh of the package's collision (core's
support limit, tools/navmesh_io.py), every island of MIN_ISLAND m2 or more.
Along each open navmesh edge, every STEP metres:
- the true floor edge lies past the eroded navmesh edge: walk outward until no
  floor is under the feet within a step (0.35 m, so a ramp foot is no edge);
- a wall or rail beside the edge (collision at knee or chest height within
  0.7 m) already stops a walker: no guard;
- a floor below (down to backstopBottom) at every distance a walker carries
  off the edge (BEYOND: 0.35 to 3 m out, a 10 m/s run off a 1 m step) makes it
  a drop, not a void: no guard (check-navmesh gates big drops). A narrow ledge
  below with a void past it is still a void; a wall on the way ends the carry.
Consecutive void samples become one guard run along the true edge, extended by
EXTEND at both ends so guards meet at corners.

With --sweep (a check-fall-through.py report), every gated failure also guards
the floor edge where its capsule left the floor (SWEEP_HALF metres either
side): a walker who walks off a high roof can sail over a low perimeter
backstop and land outside the world even where a floor lies just below the
edge, which the geometric test above accepts as a drop. Guards on one line
merge. A failure off a surface that is no navmesh edge (a thin wall top)
guards the floor edge along the capsule's heading. --merge keeps an earlier
list (a package built with guards sees them as walls: only new ones derive).
No guard stands where a walker can: each is trimmed to keep CLEAR from the
walkable navmesh at its level and LANE past the half width of every authored
route edge and stair lane. Output (world coordinates, Y
up): {"guards": [{"a": [x,y,z], "b": [x,y,z], "floor": y}], ...}; the Lumen
build turns each into a collision-only void_guard from floor-0.6 to
floor+walkClearance. Review the list, keep it committed, re-derive when floors
change (the fall-through gate fails otherwise).
"""
import argparse,json,math,sys
from pathlib import Path
import numpy as np
sys.path.insert(0,str(Path(__file__).parent))
import gltf_io,navmesh_io
from raycast import Triangles

PHYSICAL_SLOPE=math.degrees(math.acos(.65))
MIN_ISLAND=4.0   # m2, as check-fall-through.py
STEP=.25         # m between edge samples
EXTEND=.4        # m a run reaches past its end samples (eroded corners)
REACH=.7         # m from the navmesh edge to look for a wall or rail
BEYOND=(.35,1.,2.,3.)  # m past the true floor edge that need a floor below
SWEEP_HALF=1.0   # m guarded either side of a sweep failure's exit point
CORNER=1.6       # m a run may follow its floor past the end sample
CLEAR=.15        # m every guard keeps from the walkable navmesh at its level
LANE=.35         # m every guard keeps past a route edge's or stair lane's half width

def rnd(v,n=3):return [round(float(x),n) for x in v]

def main():
 ap=argparse.ArgumentParser(description=__doc__,formatter_class=argparse.RawDescriptionHelpFormatter)
 ap.add_argument('package',type=Path);ap.add_argument('--output',type=Path,required=True)
 ap.add_argument('--sweep',type=Path,help='check-fall-through.py report: guard where gated failures left the floor')
 ap.add_argument('--merge',type=Path,help='an earlier guard list: keep its guards, add the new ones')
 ap.add_argument('--clear',type=float,default=CLEAR,help='distance every guard keeps from the walkable navmesh (m)')
 ap.add_argument('--bottom',type=float,default=-20,help='backstopBottom (playable-volumes.json)')
 ap.add_argument('--exclude',type=float,nargs=6,action='append',default=[],metavar=('X0','X1','Y0','Y1','Z0','Z1'),
                 help='skip edges and sweep failures inside this box (a floor fix is pending there)')
 a=ap.parse_args()
 s=gltf_io.load(a.package);m=s.manifest;navmesh_io.require_helper()
 tri=navmesh_io.collision_triangles(s)
 C=object.__new__(Triangles);C._set(tri,np.array(['collision']*len(tri)),np.ones(len(tri),bool))
 nav=navmesh_io.build(tri,PHYSICAL_SLOPE)
 area={}
 for q in nav['polys']:area[q['island']]=area.get(q['island'],0)+q['area']
 islands={i for i,x in area.items() if x>=MIN_ISLAND}
 def floor_at(p,up=.1,down=.35):
  return C.first_hit(p+[0,up,0],p-[0,down,0]) is not None
 def landing(edge,o):
  # Something to land on at every distance a walker carries; a wall on the way
  # stops the carry (nothing past it counts).
  for d in BEYOND:
   x=edge+o*d
   if any(C.first_hit(edge+[0,h,0],x+[0,h,0]) for h in (.5,1.2)):return True
   if C.first_hit(x+[0,.35,0],[x[0],a.bottom-1,x[2]]) is None:return False
  return True
 def true_edge(p,o):
  # The collision floor edge past the eroded navmesh edge: outward until no floor.
  for d in np.arange(.02,REACH+1e-6,.02):
   if not floor_at(p+o*d):return p+o*d
  return None
 def reach(p,d,y):
  # A run ends where its floor does along the edge (Recast rounds corners
  # inward): follow the floor 0.2 m inside the guard line, at least EXTEND,
  # at most EXTEND+CORNER past the end sample.
  inward=np.cross([0,1,0],d);u=EXTEND
  for k in np.arange(EXTEND,EXTEND+CORNER+1e-6,.05):
   q=np.array([p[0],y,p[2]])+d*k
   if not any(floor_at(q+side*.27) for side in (inward,-inward)):break
   u=k
  return p+d*(u+.1)
 guards=[];samples=0;voids=0
 for q in nav['polys']:
  if q['island'] not in islands:continue
  v=q['v'];c=v.mean(0);n=len(v)
  for j in range(n):
   if not q['open'][j]:continue
   A,B=v[j],v[(j+1)%n];e=B-A;L=math.hypot(e[0],e[2])
   if L<1e-3:continue
   o=np.array([e[2],0,-e[0]])/L
   if np.dot(o,(A+B)/2-c)<0:o=-o
   k=max(1,int(math.ceil(L/STEP)));run=[]
   def flush():
    if run:
     d=e/max(np.linalg.norm(e),1e-9);d[1]=0;d/=np.linalg.norm(d)
     ga=reach(run[0][0],-d,run[0][1]);gb=reach(run[-1][0],d,run[-1][1]);y=min(r[1] for r in run)
     guards.append({'a':rnd([ga[0],y,ga[2]]),'b':rnd([gb[0],y,gb[2]]),'floor':round(y,3),'outward':rnd(o),'samples':len(run)})
     run.clear()
   for t in [(i+.5)/k for i in range(k)]:
    p=A+e*t;samples+=1
    if any(x0<=p[0]<=x1 and y0<=p[1]<=y1 and z0<=p[2]<=z1 for x0,x1,y0,y1,z0,z1 in a.exclude):flush();continue
    # The collision floor under the navmesh point (Recast heights are coarse).
    hit=C.first_hit(p+[0,.5,0],p-[0,.6,0])
    if hit is None:flush();continue
    p=np.array(hit['point'])
    # A wall or rail beside the edge already stops a walker.
    if any(C.first_hit(p+[0,h,0],p+[0,h,0]+o*REACH) for h in (.5,1.2)):flush();continue
    # The true floor edge: outward until no floor under the feet.
    edge=true_edge(p,o)
    if edge is None:flush();continue
    # Anything to land on below, just past the edge?
    if landing(edge,o):flush();continue
    voids+=1;run.append((edge+o*.07,float(p[1])))
   flush()
 swept=0
 if a.sweep:
  # Open navmesh edges of the islands, for the nearest edge to each exit point.
  segs=[]
  for q in nav['polys']:
   if q['island'] not in islands:continue
   v=q['v'];c=v.mean(0);n=len(v)
   for j in range(n):
    if not q['open'][j]:continue
    A,B=v[j],v[(j+1)%n];e=B-A;L=math.hypot(e[0],e[2])
    if L<1e-3:continue
    o=np.array([e[2],0,-e[0]])/L
    if np.dot(o,(A+B)/2-c)<0:o=-o
    segs.append((A,B,o))
  report=json.loads(a.sweep.read_text())
  for cl in report['clusters']:
   if ':' in cl['kind']:continue
   x=np.array(cl['leftFloorAt'],float);best=None
   if any(x0<=x[0]<=x1 and y0<=x[1]<=y1 and z0<=x[2]<=z1 for x0,x1,y0,y1,z0,z1 in a.exclude):continue
   for A,B,o in segs:
    e=B-A;t=float(np.clip(np.dot((x-A)[[0,2]],e[[0,2]])/max(np.dot(e[[0,2]],e[[0,2]]),1e-9),0,1));q=A+e*t
    dh=math.hypot(*(x-q)[[0,2]]);dy=abs(x[1]-q[1])
    if dh<=1.0 and dy<=.6 and (best is None or dh<best[0]):best=(dh,A,B,o,t)
   if best is None:
    # Not a navmesh edge (a thin wall top, a sill): the floor edge the capsule
    # slid off, along its heading, and the edge line from two neighbours.
    w=cl['worst']['probe'];d=np.array(cl['worst']['end'],float)-np.array(w['from'],float);d[1]=0
    if np.linalg.norm(d)<1e-6:continue
    d/=np.linalg.norm(d);side=np.cross([0,1,0],d);pts=[]
    for off in (-.25,0,.25):
     q=x+side*off
     for k in np.arange(0,1.5,.02):
      if not floor_at(q+d*k):pts.append(q+d*k);break
    if len(pts)<2:continue
    e=pts[-1]-pts[0];e[1]=0;e/=max(np.linalg.norm(e),1e-9);o=np.cross(e,[0,1,0])
    if np.dot(o,d)<0:o=-o
    mid=pts[len(pts)//2] if len(pts)==3 else (pts[0]+pts[1])/2;y=float(x[1])
    ga=mid-e*SWEEP_HALF+o*.07;gb=mid+e*SWEEP_HALF+o*.07
    guards.append({'a':rnd([ga[0],y,ga[2]]),'b':rnd([gb[0],y,gb[2]]),'floor':round(y,3),'outward':rnd(o),'samples':0,'sweep':cl['leftFloorAt']});swept+=1
    continue
   _,A,B,o,t=best;e=B-A;L=math.hypot(e[0],e[2]);d=np.array([e[0],0,e[2]])/L
   lo=max(-EXTEND,t*L-SWEEP_HALF);hi=min(L+EXTEND,t*L+SWEEP_HALF);ends=[]
   for u in (lo,hi):
    p=A+d*u;hit=C.first_hit(p+[0,.5,0],p-[0,.6,0])
    p=np.array(hit['point']) if hit else np.array([p[0],x[1],p[2]])
    edge=true_edge(p,o);ends.append((edge if edge is not None else p+o*.3)+o*.07)
   y=float(x[1]);guards.append({'a':rnd([ends[0][0],y,ends[0][2]]),'b':rnd([ends[1][0],y,ends[1][2]]),'floor':round(y,3),'outward':rnd(o),'samples':0,'sweep':cl['leftFloorAt']});swept+=1
 if a.merge:guards=json.loads(a.merge.read_text())['guards']+guards
 # Merge guards on one line (same outward normal and floor, collinear, overlapping).
 merged=[]
 for g in sorted(guards,key=lambda g:(g['outward'],g['floor'],g['a'])):
  for h in merged:
   o=np.array(h['outward']);A=np.array(h['a']);B=np.array(h['b']);P=np.array(g['a']);Q=np.array(g['b'])
   if g['outward']!=h['outward'] or abs(g['floor']-h['floor'])>.15:continue
   if abs(np.dot(P-A,o))>.08 or abs(np.dot(Q-A,o))>.08:continue
   d=(B-A)/max(np.linalg.norm(B-A),1e-9);ts=[0,np.dot(B-A,d),np.dot(P-A,d),np.dot(Q-A,d)]
   if min(ts[2],ts[3])>max(ts[0],ts[1])+.05 or max(ts[2],ts[3])<min(ts[0],ts[1])-.05:continue
   lo,hi=min(ts),max(ts);h['a']=rnd(A+d*lo);h['b']=rnd(A+d*hi);h['floor']=min(h['floor'],g['floor']);h['samples']+=g['samples']
   if 'sweep' in g:h.setdefault('sweeps',[]).append(g['sweep'])
   break
  else:
   g=dict(g)
   if 'sweep' in g:g['sweeps']=[g.pop('sweep')]
   merged.append(g)
 guards=merged
 # Never where a walker stands: trim every guard to stay CLEAR from the walkable
 # floor (navmesh polygons, any island) at its level; a sweep guard's span can
 # otherwise reach past its landing edge into a stair lane beside it.
 # Nor on an authored walk: route edges (their width) and stair lanes keep a
 # walker's clearance (RADIUS+LANE) round their centreline.
 ext=m.get('extensions',{});ns=lambda suffix:next((v for k,v in ext.items() if k.endswith(suffix)),{})
 routes=ns('.routes');nodes={n['id']:np.array(n['position'],float) for n in routes.get('nodes',[])}
 lanes=[(nodes[e['from']],nodes[e['to']],e.get('width',.6)/2+LANE) for e in routes.get('edges',[])]
 lanes+=[(np.array(f['from'],float),np.array(f['to'],float),f.get('width',1.2)/2+LANE) for f in ns('.stairs').get('paths',[])]
 def on_lane(q):
  for P,Q,w in lanes:
   d=Q-P;t=float(np.clip(np.dot((q-P)[[0,2]],d[[0,2]])/max(np.dot(d[[0,2]],d[[0,2]]),1e-9),0,1));c=P+d*t
   if math.hypot(*(q-c)[[0,2]])<w and -2.4<c[1]-q[1]<2.5:return True
  return False
 floor=navmesh_io.Floor(nav['polys']);kept=[];trimmed=0
 for g in guards:
  A=np.array(g['a'],float);B=np.array(g['b'],float);L=math.hypot(*(B-A)[[0,2]]);n=max(2,int(math.ceil(L/.05))+1)
  ok=[floor.find(A+(B-A)*k/(n-1)+[0,.9,0],a.clear,1.6) is None and not on_lane(A+(B-A)*k/(n-1)) for k in range(n)]
  trimmed+=ok.count(False);k=0
  while k<n:
   if not ok[k]:k+=1;continue
   e=k
   while e+1<n and ok[e+1]:e+=1
   if (e-k)*L/(n-1)>=.2:kept.append({**g,'a':rnd(A+(B-A)*k/(n-1)),'b':rnd(A+(B-A)*e/(n-1))})
   k=e+1
 guards=kept
 report={'method':__doc__.strip().split('\n\n')[0],'package':m['id']+' '+m.get('version',''),'edgeSamples':samples,'voidSamples':voids,
  'excluded':a.exclude,'sweepFailuresGuarded':swept,'trimmedSamples':trimmed,'guards':sorted(guards,key=lambda g:(g['floor'],g['a']))}
 a.output.write_text(json.dumps(report,indent=1)+'\n')
 print(json.dumps({k:report[k] for k in ['edgeSamples','voidSamples','sweepFailuresGuarded','trimmedSamples']}|{'guards':len(guards)}))

if __name__=='__main__':main()
