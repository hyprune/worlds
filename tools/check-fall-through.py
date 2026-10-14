#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Fall-through sweep: walk, run and autodrive capsules into every wall, divider,
railing and ledge edge of the walkable floor, with core's own walker.

The walkable floor is the physical Recast navmesh of the package's collision
(core's support limit normal.y > 0.65; tools/navmesh_io.py). Its open edges are
where something stops a walker (wall, rail, divider) or where the floor ends.
Every SPACING metres along those edges, and at every edge corner, a capsule
starts LEAD metres inside on the floor and heads for a point just past the edge
at several angles (square on to glancing), in several ways:
  walk 4 m/s and run 10 m/s at 60 fps, run 10 m/s at 20 fps (a 50 ms frame
  hitch), run 30 m/s (the run_speed ceiling) at 30 fps, and autodrive 3.5 m/s.
It keeps pushing for PUSH seconds after reaching the edge (sliding along the
wall into corners), then stands still until it has stood 0.2 s (SETTLE seconds at most). core's
`hyprune-walk-check` runs the probes (sim::Walk and Control's autodrive, the
code players use).

A probe fails when its capsule
- ends outside the playable volumes or below backstopBottom ('fell-out');
- is still falling after the settle ('falling': no floor under it; a 60 m
  drop lands within it);
- passes through a collision surface between two frames ('tunnelled': the
  capsule axis at knee or chest height crossed a triangle; the walker keeps it
  0.3 m clear of every surface).
Gated at walk, run and autodrive speeds up to GATE_SPEED (the default
run_speed, 10 m/s); the 30 m/s probes are reported only: at the run_speed
ceiling a run off a raised deck carries far over the low walking backstops,
which rise walkClearance above walk-reachable floors only.
Also reported, not gated: probes that end on a lower floor (legitimate drops;
check-navmesh gates unguarded drops) and probes that end standing more than
0.45 m from the navmesh ('off-navmesh': usually a corner pocket Recast erodes,
listed for review) and probes that crossed outside the playable volumes in
the air but landed inside again. Failures are clustered on a 1 m grid
with their worst probe, so one hole reads as one finding.

Needs node + tools/navmesh/node_modules (navmesh), tools/gltf/node_modules
for a world format 0.7 package, and core's hyprune-walk-check.
"""
import argparse,json,math,os,subprocess,sys,tempfile,time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
import numpy as np
sys.path.insert(0,str(Path(__file__).parent))
import gltf_io,navmesh_io
from raycast import Triangles

PHYSICAL_SLOPE=math.degrees(math.acos(.65))  # core Camera.cpp grounded contact
EYE=1.7
SPACING=1.0      # m between edge samples
LEAD=1.6         # m from the start to the edge
OVERSHOOT=1.0    # m the target lies past the edge
PUSH=1.0         # s of pushing on after the edge would be reached
SETTLE=3.5       # s at most standing still after the run (a 60 m fall lands)
ANGLES=(0,40,-40,70,-70)  # degrees off square-on
MODES=[('walk',4,1/60),('walk',10,1/60),('walk',10,.05),('walk',30,1/30),('autodrive',3.5,1/60)]
BACKSTOP_BOTTOM=-20
GATE_SPEED=10     # m/s: faster probes are reported, not gated
MIN_ISLAND=4.0   # m2: smaller islands are furniture tops (not walked from)

def rnd(v,n=2):return [round(float(x),n) for x in v]

class Floor:
 """Point-on-navmesh test over convex Recast polygons (any island)."""
 def __init__(self,polys,cell=2.0):
  self.polys=polys;self.cell=cell;self.grid={}
  for i,q in enumerate(polys):
   v=q['v'];lo=np.floor(v[:,[0,2]].min(0)/cell).astype(int);hi=np.floor(v[:,[0,2]].max(0)/cell).astype(int)
   for gx in range(lo[0],hi[0]+1):
    for gz in range(lo[1],hi[1]+1):self.grid.setdefault((gx,gz),[]).append(i)
 def find(self,p,reach=0.,dy=.4):
  """Index of a polygon whose surface is within `reach` horizontally and `dy`
  vertically of feet point p, else None."""
  key=(int(math.floor(p[0]/self.cell)),int(math.floor(p[2]/self.cell)));best=None
  for gx in range(key[0]-1,key[0]+2):
   for gz in range(key[1]-1,key[1]+2):
    for i in self.grid.get((gx,gz),()):
     v=self.polys[i]['v'];d=self.distance(v,p)
     if d<=reach and abs(self.height(v,p)-p[1])<=dy and (best is None or d<best[0]):best=(d,i)
  return None if best is None else best[1]
 @staticmethod
 def distance(v,p):
  # Horizontal distance from p to a convex polygon (0 inside).
  q=np.array([p[0],p[2]]);xz=v[:,[0,2]];n=len(xz);inside=True;best=1e9
  area=np.sum(xz[:,0]*np.roll(xz[:,1],-1)-np.roll(xz[:,0],-1)*xz[:,1])
  for j in range(n):
   a,b=xz[j],xz[(j+1)%n];e=b-a;cross=e[0]*(q[1]-a[1])-e[1]*(q[0]-a[0])
   if cross*area<0:inside=False
   t=np.clip(np.dot(q-a,e)/max(np.dot(e,e),1e-12),0,1);best=min(best,float(np.linalg.norm(a+e*t-q)))
  return 0. if inside else best
 @staticmethod
 def height(v,p):
  # Plane height of the polygon under p (Recast polygons are near planar).
  a,b,c=v[0],v[1],v[2];n=np.cross(b-a,c-a)
  if abs(n[1])<1e-9:return float(v[:,1].mean())
  return float(a[1]-(n[0]*(p[0]-a[0])+n[2]*(p[2]-a[2]))/n[1])

def samples(polys,islands):
 """Open-edge sample points with the outward horizontal normal, plus corners."""
 out={}
 for q in polys:
  if q['island'] not in islands:continue
  v=q['v'];c=v.mean(0);n=len(v)
  for j in range(n):
   if not q['open'][j]:continue
   a,b=v[j],v[(j+1)%n];e=b-a;L=math.hypot(e[0],e[2])
   if L<1e-3:continue
   o=np.array([e[2],0,-e[0]])/L
   if np.dot(o,(a+b)/2-c)<0:o=-o
   k=max(1,int(math.ceil(L/SPACING)))
   for t in [(i+.5)/k for i in range(k)]+[0.,1.]:
    p=a+e*t;key=(round(p[0]*4),round(p[1]*2),round(p[2]*4))
    if key in out:
     # A corner shared by two edges: aim along the bisector too.
     prev=out[key];m=prev['o']+o
     if np.linalg.norm(m)>1e-3 and not prev.get('corner'):out[key]={'p':p,'o':m/np.linalg.norm(m),'corner':True}
     continue
    out[key]={'p':p,'o':o,'corner':t in (0.,1.)}
 return list(out.values())

def main():
 ap=argparse.ArgumentParser(description=__doc__,formatter_class=argparse.RawDescriptionHelpFormatter)
 ap.add_argument('package',type=Path)
 ap.add_argument('--walk-check',type=Path,required=True,help="core's build/hyprune-walk-check")
 ap.add_argument('--output',type=Path)
 ap.add_argument('--allow',type=Path,help='reviewed allow-list: [{"near":[x,y,z],"radius":m,"why":...}]')
 ap.add_argument('--jobs',type=int,default=0,help='parallel walk-check processes (0: all cores)')
 ap.add_argument('--region',type=float,nargs=6,metavar=('X0','X1','Y0','Y1','Z0','Z1'),help='only edges inside this box')
 a=ap.parse_args()
 t0=time.time()
 s=gltf_io.load(a.package);m=s.manifest
 navmesh_io.require_helper()
 tri=navmesh_io.collision_triangles(s)
 spawn=next(sp for sp in m['spawns'] if sp['id']==m.get('defaultSpawn',m['spawns'][0]['id']))['pose']['position']
 nav=navmesh_io.build(tri,PHYSICAL_SLOPE,points=[{'id':'spawn','p':spawn,'h':[.15,.5,.15]}])
 polys=nav['polys'];main_island=nav['points'][0]['hit']['island'] if nav['points'][0]['hit'] else None
 area={}
 for q in polys:area[q['island']]=area.get(q['island'],0)+q['area']
 islands={i for i,x in area.items() if x>=MIN_ISLAND}|({main_island}-{None})
 floor=Floor(polys)
 C=object.__new__(Triangles);C._set(tri,np.array(['collision']*len(tri)),np.ones(len(tri),bool))
 def ground(p):
  # The collision floor under a navmesh point (Recast polygon heights are coarse).
  hit=C.first_hit(p+[0,.6,0],p-[0,1.0,0])
  return None if hit is None else np.array(hit['point'])
 edge=samples(polys,islands)
 if a.region:
  x0,x1,y0,y1,z0,z1=a.region;edge=[e for e in edge if x0<=e['p'][0]<=x1 and y0<=e['p'][1]<=y1 and z0<=e['p'][2]<=z1]
 probes=[];meta=[]
 for k,e in enumerate(edge):
  for ang in ANGLES if not e['corner'] else (0,25,-25):
   r=math.radians(ang);o=e['o'];d=np.array([o[0]*math.cos(r)-o[2]*math.sin(r),0,o[0]*math.sin(r)+o[2]*math.cos(r)])
   start=e['p']-d*LEAD;fi=floor.find(start,.05,.6)
   if fi is None or polys[fi]['island'] not in islands:continue
   start=ground(np.array([start[0],Floor.height(polys[fi]['v'],start),start[2]]))
   if start is None:continue
   target=e['p']+d*OVERSHOOT
   for mode,speed,dt in MODES:
    pid=len(probes)
    probes.append({'id':pid,'from':rnd(start+[0,EYE,0],3),'to':rnd(target+[0,EYE,0],3),'mode':mode,'speed':speed,'dt':dt,
                   'seconds':round((LEAD+OVERSHOOT)/speed+PUSH,3),'settle':SETTLE})
    meta.append({'edge':k,'angle':ang,'corner':bool(e['corner'])})
 jobs=a.jobs or os.cpu_count() or 4
 chunks=[probes[i::jobs] for i in range(jobs)]
 results={}
 with tempfile.TemporaryDirectory(prefix='hyprune-fall-') as tmp:
  def run(i):
   if not chunks[i]:return []
   f=Path(tmp)/f'probes-{i}.json';f.write_text(json.dumps(chunks[i]))
   out=subprocess.run([str(a.walk_check),str(a.package),str(f)],capture_output=True,text=True)
   if out.returncode:sys.exit(f'hyprune-walk-check failed: {out.stderr[-2000:]}')
   return [json.loads(l) for l in out.stdout.splitlines() if l.strip()]
  with ThreadPoolExecutor(jobs) as pool:
   for rows in pool.map(run,range(jobs)):
    for r in rows:results[r['id']]=r
 allow=json.loads(a.allow.read_text()) if a.allow else []
 failures=[];drops=0;unsupported=0;unsupported_examples=[];counts={}
 for p in probes:
  r=results[p['id']];
  if not r['startGrounded']:
   unsupported+=1
   if len(unsupported_examples)<20:unsupported_examples.append({'from':p['from'],'settled':rnd(r['start'])})
   continue
  end=np.array(r['end']);feet=end-[0,EYE,0];start_feet=np.array(r['start'])-[0,EYE,0]
  kind=None
  if not r['playable'] or feet[1]<BACKSTOP_BOTTOM:kind='fell-out'
  elif not r['grounded']:kind='falling'
  elif r.get('crossed'):kind='tunnelled'
  elif floor.find(feet,.45,.45) is None:kind='review:off-navmesh'
  elif r['leftPlayable']:kind='review:left-playable-in-air'
  elif feet[1]<start_feet[1]-1:drops+=1
  if not kind:continue
  if p['speed']>GATE_SPEED and ':' not in kind:kind='report:'+kind
  if ':' not in kind and any(np.linalg.norm(feet-np.array(x['near']))<=x['radius'] for x in allow):kind='allowed:'+kind
  counts[kind]=counts.get(kind,0)+1
  failures.append({'kind':kind,'probe':p,'end':rnd(end),'minY':round(r['minY'],2),'crossed':r.get('crossed'),'lastGrounded':r['lastGrounded'],**meta[p['id']]})
 # One finding per 1 m cell of the floor point the capsule last stood on (where it
 # left the floor: the hole or gap), worst probe kept, so one hole reads as one finding.
 clusters={}
 for f in failures:
  at=np.array(f['lastGrounded'])-[0,EYE,0];key=(f['kind'],*np.round(at).astype(int).tolist())
  c=clusters.setdefault(key,{'kind':f['kind'],'leftFloorAt':rnd(at,1),'probes':0,'modes':set(),'edges':set(),'worst':f})
  c['probes']+=1;c['modes'].add(f"{f['probe']['mode']} {f['probe']['speed']:g}");c['edges'].add(tuple(rnd(edge[f['edge']]['p'],1)))
  if f['minY']<c['worst']['minY']:c['worst']=f
 findings=sorted(({**c,'modes':sorted(c['modes']),'edges':sorted(c['edges'])[:6]} for c in clusters.values()),key=lambda c:(c['kind'],c['leftFloorAt']))
 gated=[c for c in findings if ':' not in c['kind']]
 report={'status':'FAIL' if gated else 'PASS','package':m['id']+' '+m.get('version',''),
  'method':__doc__.strip().split('\n\n')[0].replace('\n',' '),
  'navmesh':{'polys':len(polys),'islands':len(islands),'mainIsland':main_island,'slope':round(PHYSICAL_SLOPE,1)},
  'edgeSamples':len(edge),'probes':len(probes),'unsupportedStarts':unsupported,'unsupportedExamples':unsupported_examples,'legitimateDrops':drops,
  'modes':[f'{mo} {sp:g} m/s @ {1/dt:.0f} fps' for mo,sp,dt in MODES],'angles':list(ANGLES),
  'failedProbes':counts,'findings':len(gated),'clusters':findings,'seconds':round(time.time()-t0,1)}
 text=json.dumps(report,indent=1)
 if a.output:a.output.parent.mkdir(parents=True,exist_ok=True);a.output.write_text(text+'\n')
 print(json.dumps({k:report[k] for k in ['status','edgeSamples','probes','unsupportedStarts','legitimateDrops','failedProbes','findings','seconds']}))
 for c in gated[:40]:
  w=c['worst']['probe'];print(f"  {c['kind']:9s} left the floor at {c['leftFloorAt']} x{c['probes']} [{', '.join(c['modes'])}] e.g. {w['mode']} {w['speed']:g} from {w['from']} -> end {c['worst']['end']}",file=sys.stderr)
 sys.exit(1 if gated else 0)

if __name__=='__main__':main()
