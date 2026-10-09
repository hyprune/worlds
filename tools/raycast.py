# SPDX-License-Identifier: MIT
"""Vectorised ray/triangle and capsule/triangle queries for offline package audits."""
import numpy as np
from gltf_io import Scene


class Triangles:
 """Visible package triangles with their material key and sidedness."""
 def __init__(self,scene:Scene,keep=lambda key,mat:True):
  tri=[];keys=[];double=[]
  for _,name,prim,pos,idx in scene.primitives():
   mat=scene.doc['materials'][prim['material']] if 'material' in prim else {}
   key=mat.get('name','').split('--')[-1]
   if not keep(key,mat):continue
   tri.append(pos[idx]);keys.extend([key]*len(idx));double.extend([bool(mat.get('doubleSided',False))]*len(idx))
  self._set(np.concatenate(tri).astype(float),np.array(keys),np.array(double))

 def _set(self,tri,keys,double):
  self.tri=tri;self.keys=keys;self.double=double
  self.lo=self.tri.min(axis=1);self.hi=self.tri.max(axis=1)
  self.normal=np.cross(self.tri[:,1]-self.tri[:,0],self.tri[:,2]-self.tri[:,0])

 def subset(self,lo,hi):
  """Triangles overlapping an axis-aligned box, for many local queries."""
  i=self.near(np.asarray(lo,float),np.asarray(hi,float));out=object.__new__(Triangles);out._set(self.tri[i],self.keys[i],self.double[i]);return out

 def near(self,lo,hi):
  return np.nonzero(np.all(self.hi>=lo,axis=1)&np.all(self.lo<=hi,axis=1))[0]

 def first_hit(self,origin,target,eps=1e-4):
  """Nearest rendered hit on the segment origin->target. Back faces of
  single-sided materials are culled by the renderer, so they never occlude."""
  origin=np.asarray(origin,float);target=np.asarray(target,float);d=target-origin
  cand=self.near(np.minimum(origin,target)-eps,np.maximum(origin,target)+eps)
  if not len(cand):return None
  t=self.tri[cand];e1=t[:,1]-t[:,0];e2=t[:,2]-t[:,0];p=np.cross(d,e2);det=(e1*p).sum(axis=1)
  ok=np.abs(det)>1e-12;inv=np.divide(1,det,out=np.zeros_like(det),where=ok);s=origin-t[:,0]
  u=(s*p).sum(axis=1)*inv;q=np.cross(s,e1);v=(q@d)*inv;h=(e2*q).sum(axis=1)*inv
  facing=(self.normal[cand]@d)<0
  hit=ok&(u>=0)&(v>=0)&(u+v<=1)&(h>eps)&(h<1-eps)&(facing|self.double[cand])
  if not hit.any():return None
  i=np.argmin(np.where(hit,h,np.inf));return {'t':float(h[i]),'key':str(self.keys[cand[i]]),'point':(origin+d*h[i]).tolist()}


def nearest_sq(points,t):
 """Squared distance from each point to its triangle (points and t aligned)."""
 a,b,c=t[:,0],t[:,1],t[:,2];ab=b-a;ac=c-a;n=np.cross(ab,ac);nn=(n*n).sum(axis=1);p=points
 proj=p-n*((((p-a)*n).sum(axis=1)/np.maximum(nn,1e-20))[:,None]);v=proj-a
 d00=(ab*ab).sum(axis=1);d01=(ab*ac).sum(axis=1);d11=(ac*ac).sum(axis=1);d20=(v*ab).sum(axis=1);d21=(v*ac).sum(axis=1);den=d00*d11-d01*d01
 u=(d11*d20-d01*d21)/np.maximum(den,1e-20);w=(d00*d21-d01*d20)/np.maximum(den,1e-20);inside=(u>=0)&(w>=0)&(u+w<=1)&(den>1e-14)
 dist=np.where(inside,((p-proj)**2).sum(axis=1),np.inf)
 for x,y in [(a,b),(b,c),(c,a)]:
  e=y-x;frac=np.clip(((p-x)*e).sum(axis=1)/np.maximum((e*e).sum(axis=1),1e-20),0,1);q=x+e*frac[:,None];dist=np.minimum(dist,((p-q)**2).sum(axis=1))
 return dist


def segment_distance(t,bottom,top,iterations=24):
 """Minimum distance between segment bottom->top and each triangle."""
 lower=np.zeros(len(t));upper=np.ones(len(t))
 for _ in range(iterations):
  u=(2*lower+upper)/3;v=(lower+2*upper)/3
  du=nearest_sq(bottom+(top-bottom)*u[:,None],t);dv=nearest_sq(bottom+(top-bottom)*v[:,None],t)
  choose=du<dv;upper=np.where(choose,v,upper);lower=np.where(choose,lower,u)
 return np.sqrt(nearest_sq(bottom+(top-bottom)*((lower+upper)/2)[:,None],t))
