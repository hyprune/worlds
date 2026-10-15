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
- ends below backstopBottom, or outside the playable volumes on a lower
  level or still in the air ('fell-out'; standing outside on its own level,
  a roof lip past the volume, is reported for review);
- is still falling after the settle ('falling': no floor under it; a 60 m
  drop lands within it);
- passes through a collision surface between two frames ('tunnelled': the
  capsule axis at knee or chest height crossed a triangle; the walker keeps it
  0.3 m clear of every surface).
Gated at every speed up to GATE_SPEED, the run_speed ceiling (30 m/s): core
eases a falling walker's horizontal speed down to 10 m/s off a real drop, and
the Lumen build raises backstops and guards to clear that fall arc from every
higher reachable top, so a run off a raised deck stays in the world at any
run speed.
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
GATE_SPEED=30     # m/s: every mode up to the run_speed ceiling is gated
MIN_ISLAND=4.0   # m2: smaller islands are furniture tops (not walked from)

def rnd(v,n=2):return [round(float(x),n) for x in v]

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
 floor=navmesh_io.Floor(polys)
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
   start=ground(np.array([start[0],navmesh_io.Floor.height(polys[fi]['v'],start),start[2]]))
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
  if feet[1]<BACKSTOP_BOTTOM or not r['playable'] and (not r['grounded'] or feet[1]<start_feet[1]-1):kind='fell-out'
  elif not r['playable']:kind='review:standing-outside-playable'
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
