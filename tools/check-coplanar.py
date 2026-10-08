#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Port of the 0.004m same-facing coplanar probe technique, all three axes.
No Blender dependency. Only visual scene nodes; helper meshes are not art.
Sampling at 0.10m cannot certify arbitrarily small/off-axis surfaces, so source
also gives foreground trim explicit geometric offsets. No decoration bypass.
"""
import json,sys
from collections import defaultdict
import numpy as np
from gltf_io import Scene
if '--emissive' in sys.argv:
 import importlib.util
 spec=importlib.util.spec_from_file_location('emissive',__file__.replace('check-coplanar.py','check-emissive.py'));module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
 fixture=sys.argv[sys.argv.index('--fixtures')+1] if '--fixtures' in sys.argv else None
 report=module.check(sys.argv[1],fixture);print(json.dumps(report,indent=2));sys.exit(0 if report['status']=='PASS' else 1)
s=Scene(sys.argv[1]);GAP=.004;STEP=.10;hits=[];total=0
for axis in range(3):
 other=[i for i in range(3) if i!=axis];grid=defaultdict(list);scanned=0
 for node,name,p,positions,indices in s.primitives():
  for ti,v in enumerate(positions[indices]):
   normal=np.cross(v[1]-v[0],v[2]-v[0]);length=np.linalg.norm(normal)
   if length<1e-10:continue
   normal/=length
   if abs(normal[axis])<.999:continue
   scanned+=1;tri=v[:,other];a,b,c=tri;u=b-a;w=c-a;den=u[0]*w[1]-w[0]*u[1]
   if abs(den)<1e-12:continue
   lo=np.floor(tri.min(axis=0)/STEP).astype(int);hi=np.ceil(tri.max(axis=0)/STEP).astype(int)
   yy,xx=np.mgrid[lo[1]:hi[1],lo[0]:hi[0]];dx=(xx+.5)*STEP-a[0];dy=(yy+.5)*STEP-a[1]
   f=(dx*w[1]-dy*w[0])/den;h=(u[0]*dy-u[1]*dx)/den;inside=(f>1e-7)&(h>1e-7)&(f+h<1-1e-7)
   depth=v[0,axis]+f*(v[1,axis]-v[0,axis])+h*(v[2,axis]-v[0,axis])
   for x,y,z in zip(xx[inside],yy[inside],depth[inside]):grid[(int(x),int(y))].append((float(z),name,ti,normal.copy(),v.tolist(),s.doc['materials'][p['material']]['name']))
 pairs=defaultdict(int)
 for cell,stack in grid.items():
  stack.sort(key=lambda t:t[0])
  for a,b in zip(stack,stack[1:]):
   if b[0]-a[0]<GAP-1e-6 and a[3].dot(b[3])>.99999:pairs[(a[1],b[1],round(a[0],3),a[5],b[5],str(a[4]),str(b[4]))]+=1
 for (a,b,z,ma,mb,va,vb),count in pairs.items():hits.append({'axis':axis,'first':a,'second':b,'depth':z,'samples':count,'materials':[ma,mb],'vertices':[json.loads(va),json.loads(vb)]})
 total+=scanned
report={'status':'FAIL' if hits else 'PASS','probeSpacingMeters':STEP,'sameFacingGapMeters':GAP,'facesScanned':total,'stacks':hits}
print(json.dumps(report,indent=2));sys.exit(1 if hits else 0)
