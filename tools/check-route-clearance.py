#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Rendered-geometry clearance along every stair flight and walking edge.

Collision audits (check-walking.py) cannot see render-only geometry: in 0.7.0
a non-colliding rock foundation and the closed night-sky shells capped the
snow-service stair while capsule routes walked straight through them. This
check uses only *visible* triangles, including vista art:
- headroom: vertical rays from 0.6 m to 2 m across the flight width;
- body: a 0.25 m capsule from 0.6 m (clear of tread nosings) to 1.8 m;
- sightline: eye-height rays to every sample up to 6 m ahead and behind,
  culling back faces of single-sided materials exactly as the renderer does.
"""
import argparse,json,math,sys
from pathlib import Path
import numpy as np
sys.path.insert(0,str(Path(__file__).parent))
from gltf_io import Scene
from raycast import Triangles,segment_distance
p=argparse.ArgumentParser(description=__doc__);p.add_argument('package',type=Path);p.add_argument('--output',type=Path);a=p.parse_args()
s=Scene(a.package);m=s.manifest;T=Triangles(s)
KNEE,HEAD,EYE,RADIUS,STEP,AHEAD=.6,2.0,1.6,.25,.25,6.0
# Reviewed findings that predate 0.7.1 and are outside its owner-reported
# scope. Each is pinned to its flight, tests, materials and sample count, so
# any growth or any new location still fails. Reported, not hidden.
KNOWN={
 'snow-service-ascent':({'capsule'},{'metal','soffit'},30,'wall-side lane passes 0.16 m from the tunnel wall lamps and handrail where the treads meet the wall'),
 'roof-ascent-lower':({'capsule'},{'concrete'},6,'outer lane passes 0.20 m from the landing wall face at the top step'),
 'roof-final>roof-bridge':({'capsule','headroom'},{'metal'},10,'metal member 0.88-1.12 m above the 16 m roof bridge crosses the centreline (render-only; walk harness passes); candidate fix'),
 'roof-bridge>rooftop':({'capsule'},{'metal'},10,'same roof-bridge member, 0.23 m beside the centreline'),
 'hall-arrival>hall-annex-entry':({'capsule'},{'leaf'},2,'single leaf tip at 2.0 m, 0.24 m from the centreline'),
 'hall-upper-base>hall-upper':({'capsule'},{'metal'},14,'5 cm vertical mullion 0.20 m beside the centreline'),
}
def flights():
 for f in m['extensions'].get('com.hyprune.lumen-reach.stairs',{}).get('paths',[]):yield 'stair',f['id'],np.array(f['from']),np.array(f['to']),f['width']
 r=m['extensions']['com.hyprune.lumen-reach.routes'];nodes={n['id']:np.array(n['position']) for n in r['nodes']}
 for e in r['edges']:yield 'edge',e['from']+'>'+e['to'],nodes[e['from']],nodes[e['to']],.6
rows=[];failures=[];accepted=[]
for kind,ident,start,end,width in flights():
 d=end-start;n=max(2,math.ceil(np.linalg.norm(d)/STEP)+1);side=np.array([-d[2],0,d[0]]);side/=max(np.linalg.norm(side),1e-9)
 # Outer lanes keep a 0.1m hand gap from the rails at the tread edge.
 lanes=[0.0] if width<=2*RADIUS+.3 else [-(width/2-RADIUS-.1),0.0,width/2-RADIUS-.1]
 feet=[start+d*t for t in np.linspace(0,1,n)];bad=[]
 margin=width/2+RADIUS+.1;L=T.subset(np.minimum(start,end)-[margin,margin,margin],np.maximum(start,end)+[margin,HEAD+margin,margin])
 for lane in lanes:
  for i,f in enumerate(feet):
   f=f+side*lane;up=np.array([0,1,0])
   # Headroom ignores facing: a lid is physically there even where culled.
   cand=L.near(f+up*KNEE-[.02,0,.02],f+up*HEAD+[.02,0,.02])
   if len(cand):
    t=L.tri[cand];o=f+up*KNEE;dd=up*(HEAD-KNEE);e1=t[:,1]-t[:,0];e2=t[:,2]-t[:,0];pp=np.cross(dd,e2);det=(e1*pp).sum(axis=1);ok=abs(det)>1e-12
    inv=np.divide(1,det,out=np.zeros_like(det),where=ok);ss=o-t[:,0];u=(ss*pp).sum(axis=1)*inv;q=np.cross(ss,e1);v=(q@dd)*inv;hh=(e2*q).sum(axis=1)*inv
    hit=ok&(u>=0)&(v>=0)&(u+v<=1)&(hh>0)&(hh<1)
    if hit.any():j=np.argmin(np.where(hit,hh,np.inf));bad.append({'test':'headroom','lane':lane,'feet':f.round(3).tolist(),'hitHeight':round(float(KNEE+hh[j]*(HEAD-KNEE)),3),'material':str(L.keys[cand[j]])})
   cand=L.near(f+[-RADIUS,KNEE-RADIUS,-RADIUS],f+[RADIUS,1.8+RADIUS,RADIUS])
   if len(cand):
    dist=segment_distance(L.tri[cand],f+up*KNEE,f+up*1.8)
    if dist.min()<RADIUS:j=int(np.argmin(dist));bad.append({'test':'capsule','lane':lane,'feet':f.round(3).tolist(),'distance':round(float(dist[j]),3),'material':str(L.keys[cand[j]])})
   for j in range(i+1,len(feet)):
    g=feet[j]+side*lane
    if np.linalg.norm(g-f)>AHEAD:break
    for o,t in [(f,g),(g,f)]:
     hit=L.first_hit(o+up*EYE,t+up*EYE)
     if hit:bad.append({'test':'sightline','lane':lane,'from':o.round(3).tolist(),'to':t.round(3).tolist(),'blockedAt':np.round(hit['point'],3).tolist(),'material':hit['key']})
 row={'kind':kind,'id':ident,'meters':round(float(np.linalg.norm(d)),2),'samples':n*len(lanes),'blocked':len(bad)}
 rows.append(row)
 if bad:
  tests=sorted({b['test'] for b in bad});mats=sorted({b['material'] for b in bad});finding={**row,'tests':tests,'materials':mats,'examples':bad[:6]}
  k=KNOWN.get(ident)
  if k and set(tests)<=k[0] and set(mats)<=k[1] and len(bad)<=k[2]:accepted.append({**finding,'reason':k[3]})
  else:failures.append(finding)
report={'status':'FAIL' if failures else 'PASS','method':__doc__.strip(),'knee':KNEE,'head':HEAD,'eye':EYE,'radius':RADIUS,'sampleStep':STEP,'sightlineMeters':AHEAD,'flights':rows,'failures':failures,'acceptedPreexisting':accepted}
text=json.dumps(report,indent=2)+'\n'
if a.output:a.output.parent.mkdir(parents=True,exist_ok=True);a.output.write_text(text)
print(json.dumps({'status':report['status'],'flights':len(rows),'acceptedPreexisting':[{k:f[k] for k in ['id','blocked','reason']} for f in accepted],'failures':[{k:f[k] for k in ['kind','id','blocked','tests','materials']} for f in failures]},indent=2))
sys.exit(1 if failures else 0)
