#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Independent exported walking graph support, slope and standing clearance audit."""
import json,sys,math
from pathlib import Path
import numpy as np
from gltf_io import Scene
root=Path(sys.argv[1]);s=Scene(root);m=s.manifest;route=m['extensions']['com.hyprune.lumen-reach.routes'];nodes={n['id']:np.array(n['position']) for n in route['nodes']};collision={c['node'] for c in m['collision']}
assert len(nodes)<=64 and len(route['edges'])<=256,'core graph limits exceeded'
tri=[]
for i,name,p,pos,indices in s.primitives(visible=False):
 if i in collision:tri.extend(pos[indices])
tri=np.array(tri);low=tri.min(axis=1);high=tri.max(axis=1);failures=[];rows=[]
# Graph must be connected from arrival, including elevated branches.
seen={'arrival'}
while True:
 old=len(seen)
 for e in route['edges']:
  if e['from'] in seen:seen.add(e['to'])
  if e['to'] in seen:seen.add(e['from'])
 if len(seen)==old:break
assert seen==set(nodes),('disconnected graph',set(nodes)-seen)

def nearest(points,t):
 # Closest point on triangle: face interior or one of its edges.
 a,b,c=t[:,0],t[:,1],t[:,2];ab=b-a;ac=c-a;n=np.cross(ab,ac);nn=(n*n).sum(axis=1);p=points
 proj=p-n*((((p-a)*n).sum(axis=1)/np.maximum(nn,1e-20))[:,None]);v=proj-a
 d00=(ab*ab).sum(axis=1);d01=(ab*ac).sum(axis=1);d11=(ac*ac).sum(axis=1);d20=(v*ab).sum(axis=1);d21=(v*ac).sum(axis=1);den=d00*d11-d01*d01
 u=(d11*d20-d01*d21)/np.maximum(den,1e-20);w=(d00*d21-d01*d20)/np.maximum(den,1e-20);inside=(u>=0)&(w>=0)&(u+w<=1)&(den>1e-14)
 dist=np.where(inside,((p-proj)**2).sum(axis=1),np.inf)
 for x,y in [(a,b),(b,c),(c,a)]:
  e=y-x;frac=np.clip(((p-x)*e).sum(axis=1)/np.maximum((e*e).sum(axis=1),1e-20),0,1);q=x+e*frac[:,None];dist=np.minimum(dist,((p-q)**2).sum(axis=1))
 return dist

def check(p):
 # Verify the actual support directly beneath expected feet via vertical ray.
 valid=(low[:,0]<=p[0]+1e-5)&(high[:,0]>=p[0]-1e-5)&(low[:,2]<=p[2]+1e-5)&(high[:,2]>=p[2]-1e-5)
 t=tri[valid];a,b,c=t[:,0],t[:,1],t[:,2];v0=b[:,[0,2]]-a[:,[0,2]];v1=c[:,[0,2]]-a[:,[0,2]];v2=p[[0,2]]-a[:,[0,2]];den=v0[:,0]*v1[:,1]-v0[:,1]*v1[:,0];safe=abs(den)>1e-10
 u=np.divide(v2[:,0]*v1[:,1]-v2[:,1]*v1[:,0],den,out=np.zeros(len(den)),where=safe);v=np.divide(v0[:,0]*v2[:,1]-v0[:,1]*v2[:,0],den,out=np.zeros(len(den)),where=safe);y=a[:,1]+u*(b[:,1]-a[:,1])+v*(c[:,1]-a[:,1]);supported=safe&(u>=-1e-5)&(v>=-1e-5)&(u+v<=1+1e-5)&(abs(y-p[1])<.06)
 if not supported.any():return 'no walkable support'
 # Match core's 0.3m bottom cap and 3cm push-out budget. Include
 # small slab risers: ignoring all geometry below feet+0.12 missed a roof join.
 valid=(high[:,0]>p[0]-.3)&(low[:,0]<p[0]+.3)&(high[:,2]>p[2]-.3)&(low[:,2]<p[2]+.3)&(high[:,1]>p[1]+.025)&(low[:,1]<p[1]+1.8)
 t=tri[valid]
 if not len(t):return None
 # Resolve closest capsule-axis point using convex distance minimization.
 bottom=p+np.array([0,.3,0]);top=p+np.array([0,1.5,0]);lower=np.zeros(len(t));upper=np.ones(len(t))
 for _ in range(22):
  u=(2*lower+upper)/3;v=(lower+2*upper)/3;du=nearest(bottom+(top-bottom)*u[:,None],t);dv=nearest(bottom+(top-bottom)*v[:,None],t);choose=du<dv;upper=np.where(choose,v,upper);lower=np.where(choose,lower,u)
 dist=nearest(bottom+(top-bottom)*((lower+upper)/2)[:,None],t)
 if np.min(dist)<.27**2:return 'standing capsule intersects collision'
 return None
for e in route['edges']:
 a,b=nodes[e['from']],nodes[e['to']];delta=b-a;horizontal=np.linalg.norm(delta[[0,2]]);slope=abs(delta[1])/max(horizontal,1e-6);assert slope<=.4,(e,'slope too steep',slope)
 samples=max(2,math.ceil(np.linalg.norm(delta)/.25));bad=[]
 for t in np.linspace(0,1,samples):
  p=a+(b-a)*t;error=check(p)
  if error:bad.append({'position':p.tolist(),'reason':error})
 if bad:failures.append({'edge':[e['from'],e['to']],'failures':bad[:5],'failedSamples':len(bad)})
 rows.append({'edge':[e['from'],e['to']],'meters':float(np.linalg.norm(delta)),'slope':float(slope),'samples':samples})
for flight in m['extensions'].get('com.hyprune.lumen-reach.stairs',{}).get('paths',[]):
 a,b=np.array(flight['from']),np.array(flight['to']);samples=max(2,math.ceil(np.linalg.norm(b-a)/.25));bad=[]
 for t in np.linspace(0,1,samples):
  p=a+(b-a)*t;error=check(p)
  if error:bad.append({'position':p.tolist(),'reason':error})
 if bad:failures.append({'stair':flight['id'],'failures':bad[:5],'failedSamples':len(bad)})
 rows.append({'stair':flight['id'],'meters':float(np.linalg.norm(b-a)),'samples':samples})
report={'status':'FAIL' if failures else 'PASS','connectedNodes':len(seen),'edges':rows,'failures':failures,'method':'exported collision triangle floor support and continuous standing capsule clearance sampled at <=0.25m; all graph branches'}
print(json.dumps(report,indent=2));sys.exit(1 if failures else 0)
