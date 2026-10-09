# SPDX-License-Identifier: MIT
"""Spherical derivatives: periodic longitude, latitude-correct poles, no edge extrusion."""
from pathlib import Path
import json, hashlib
import numpy as np
from PIL import Image
HERE=Path(__file__).parent

def smooth(x):
 x=np.clip(x,0,1);return x*x*(3-2*x)

def wrap(a):
 # Correct the endpoint difference over the whole circle, then smooth the join
 # locally. Unlike mirroring the painting, this preserves landmark handedness.
 h,w,_=a.shape
 a=a+(a[:,0:1]-a[:,-1:])*np.linspace(-.5,.5,w)[None,:,None]
 for i in range(48):
  t=.5*(1-i/48)**2;l=a[:,i].copy();r=a[:,-1-i].copy()
  a[:,i]=(1-t)*l+t*r;a[:,-1-i]=(1-t)*r+t*l
 return a

def save(name,a):
 h,w,_=a.shape
 for edge,rows in [(0,range(100)),(-1,range(h-100,h))]:
  color=a[edge].mean(axis=0)
  for y in rows:
   dist=y if edge==0 else h-1-y;t=smooth(1-dist/100)
   a[y]=a[y]*(1-t)+color*t
 a=np.round(np.clip(a,0,255)).astype('uint8');a[:,-1]=a[:,0]
 a[0]=a[0].mean(axis=0).round().astype('uint8');a[-1]=a[-1].mean(axis=0).round().astype('uint8')
 path=HERE/'tiles'/f'{name}-albedo.png';Image.fromarray(a).save(path,optimize=True)
 return {'name':name,'size':[w,h],'sha256':hashlib.sha256(path.read_bytes()).hexdigest(),'longitudeEdgeMax':int(abs(a[:,0].astype(int)-a[:,-1]).max()),'poleRangeMax':int(max(np.ptp(a[0],axis=0).max(),np.ptp(a[-1],axis=0).max()))}

def prepare():
 day=np.array(Image.open(HERE/'source/sky-v7.png').convert('RGB').resize((2048,1024),Image.Resampling.LANCZOS),dtype=float)
 rows=[save('sky-v7',wrap(day))]
 src=np.array(Image.open(HERE/'source/night-vista.png').convert('RGB').resize((2048,512),Image.Resampling.LANCZOS),dtype=float)
 # Original night master occupies the 0..40-degree horizon band, surrounded by
 # actual gradients, never a repeated first/last image row.
 sky=np.empty((1024,2048,3),float);zen=np.array([2,28,61]);ground=np.array([22,36,49])
 for y in range(1024):
  latitude=90-y/1023*180
  if latitude>=40:sky[y]=zen
  elif latitude>=0:
   row=src[min(511,int((40-latitude)/40*511))];t=smooth(latitude/40)
   sky[y]=row*(1-t**5)+zen*t**5
  else:
   t=smooth(-latitude/35);sky[y]=src[-1]*(1-t)+ground*t
 rows.append(save('night-sky-v7',wrap(sky)))
 (HERE/'tiles/sky-report.json').write_text(json.dumps(rows,indent=2)+'\n')
if __name__=='__main__':prepare()
