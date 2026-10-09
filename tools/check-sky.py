#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Deterministic sky/backdrop audit from every walkable eye position.

Catches the 0.7.0 owner defects without image judgement:
- layers: every enclosing sky is opaque and single sided; no large blended
  backdrop card can double-expose a sky.
- ghost: seam processing must not superimpose mirrored or row-shifted copies
  of the painting (mirror correlation across the longitude seam, coherent
  per-row offsets near the seam versus the image centre).
- seam: every texture row whose seam step exceeds SEAM_SOFT_STEP must be
  hidden behind opaque geometry from every eye at that latitude.
- leaks: no view ray from a walkable eye first meets the culled back of a sky
  or terrain shell (standing outside a closed sky and seeing past it), and
  no terrain shell stands inside a closed sky at walking level.
- magnification: screen pixels per sky texel at 3840x2160, 60 deg vertical
  fov, nearest approach from any eye. Above MAX_PAINTED_MAGNIFICATION the
  texture under that triangle must be smooth (per-texel step <= SMOOTH_STEP
  levels), so bilinear magnification cannot show blocks, rings or streaks.
- terrain: distant backdrop terrain stays TERRAIN_DIP below every eye.
- poles: texture rows under the polar fans are uniform.
"""
import argparse,json,math,sys
from pathlib import Path
import numpy as np
from PIL import Image
sys.path.insert(0,str(Path(__file__).parent))
from gltf_io import Scene
from raycast import Triangles,nearest_sq
MAX_PAINTED_MAGNIFICATION=12.0
SMOOTH_STEP=4
POLE_RANGE=3
GHOST_MAX=.15
SEAM_SOFT_STEP=12
TERRAIN_DIP=6.0
STREAK_MAX=2.0
p=argparse.ArgumentParser(description=__doc__);p.add_argument('package',type=Path);p.add_argument('--poses',type=Path,action='append',default=[]);p.add_argument('--output',type=Path);a=p.parse_args()
s=Scene(a.package);m=s.manifest;H=2160;PIX=2*math.tan(math.radians(30))/H

# Walkable eyes: nav polygon centroids and corners pulled 0.35 m inside,
# every route node, stair ends and owner capture poses.
eyes=[]
for i,name,prim,pos,idx in s.primitives(visible=False):
 if i!=m['navigation']['node']:continue
 for t in pos[idx]:
  c=t.mean(axis=0);eyes.append(c)
  for v in t:
   d=c-v;eyes.append(v+d*min(1,.35/max(np.linalg.norm(d),1e-6)))
route=m['extensions']['com.hyprune.lumen-reach.routes'];nodes={n['id']:np.array(n['position']) for n in route['nodes']}
eyes+=list(nodes.values())
for e in route['edges']:
 x,y=nodes[e['from']],nodes[e['to']]
 for t in np.linspace(0,1,max(2,math.ceil(np.linalg.norm(y-x)/2))):eyes.append(x+(y-x)*t)
for f in m['extensions'].get('com.hyprune.lumen-reach.stairs',{}).get('paths',[]):eyes+=[np.array(f['from']),np.array(f['to'])]
eyes=[e+[0,1.7,0] for e in eyes]
owner=[]
for path in a.poses:
 for v in json.loads(path.read_text())['owner']:owner.append(np.array(v['position'],float))
eyes=np.unique(np.round(np.array(eyes+owner),3),axis=0)

def encloses(tri):
 # A shell encloses its box centre if rays in 26 jittered directions from
 # the centre nearly all meet it (aqueduct/spire kits do not; a passage
 # portal may let one ray through).
 c=(tri.reshape(-1,3).max(axis=0)+tri.reshape(-1,3).min(axis=0))/2;e1=tri[:,1]-tri[:,0];e2=tri[:,2]-tri[:,0];hits=0
 for d in [np.array(v,float)+[.013,.021,.017] for v in [(x,y,z) for x in (-1,0,1) for y in (-1,0,1) for z in (-1,0,1) if (x,y,z)!=(0,0,0)]]:
  pp=np.cross(d,e2);det=(e1*pp).sum(axis=1);ok=abs(det)>1e-12;inv=np.divide(1,det,out=np.zeros_like(det),where=ok);ss=c-tri[:,0];u=(ss*pp).sum(axis=1)*inv;q=np.cross(ss,e1);v=(q@d)*inv;h=(e2*q).sum(axis=1)*inv
  hits+=bool((ok&(u>=0)&(v>=0)&(u+v<=1)&(h>0)).any())
 return hits>=24
skies=[];big_blend=[]
for _,name,prim,pos,idx in s.primitives():
 mat=s.doc['materials'][prim['material']];key=mat.get('name','').split('--')[-1];size=float(np.linalg.norm(pos.max(axis=0)-pos.min(axis=0)))
 if mat.get('alphaMode','OPAQUE')!='OPAQUE':
  t=pos[idx];edge=float(max(np.linalg.norm(t[:,i]-t[:,(i+1)%3],axis=1).max() for i in range(3)))
  if edge>8:big_blend.append({'material':key,'longestEdgeMeters':round(edge,1),'alphaMode':mat['alphaMode']})
 slot=mat.get('pbrMetallicRoughness',{}).get('baseColorTexture')
 # A sky layer is a large unlit textured shell whose box encloses walkable eyes.
 inside=np.all((eyes>pos.min(axis=0))&(eyes<pos.max(axis=0)),axis=1).any()
 if 'KHR_materials_unlit' in mat.get('extensions',{}) and slot and size>60 and inside and encloses(pos[idx].astype(float)):skies.append((key,mat,prim,pos,idx,slot))
assert skies,'no sky layers'
failures=[];rows=[]
shells=Triangles(s,lambda key,mat:key in {k for k,*_ in skies} or key.startswith('land-'))
world=Triangles(s,lambda key,mat:key not in {k for k,*_ in skies})

def nearest(T,origin,target):
 """Nearest surface on the segment, culled or not, with its facing."""
 d=target-origin;cand=T.near(np.minimum(origin,target)-1e-4,np.maximum(origin,target)+1e-4)
 if not len(cand):return None
 t=T.tri[cand];e1=t[:,1]-t[:,0];e2=t[:,2]-t[:,0];pp=np.cross(d,e2);det=(e1*pp).sum(axis=1);ok=abs(det)>1e-12
 inv=np.divide(1,det,out=np.zeros_like(det),where=ok);ss=origin-t[:,0];u=(ss*pp).sum(axis=1)*inv;q=np.cross(ss,e1);v=(q@d)*inv;h=(e2*q).sum(axis=1)*inv
 hit=ok&(u>=0)&(v>=0)&(u+v<=1)&(h>1e-4)&(h<1)
 if not hit.any():return None
 j=np.argmin(np.where(hit,h,np.inf));front=(T.normal[cand[j]]@d)<0
 return {'t':float(h[j]),'key':str(T.keys[cand[j]]),'front':bool(front),'culled':bool(not front and not T.double[cand[j]]),'point':origin+d*h[j]}

# Closed skies are every sky except the outermost; terrain must never stand
# inside one at or above walking level (rock walls inside a basin's yard).
closed=[(k,(pp.max(axis=0)+pp.min(axis=0))/2,Triangles(s,lambda key,mat,k=k:key==k)) for k,_,_,pp,_,_ in sorted(skies,key=lambda r:np.ptp(r[3],axis=0).max())[:-1]]
def inside_closed(point):
 # Most of seven rays to targets spread across the sky's extent cross no
 # sky wall (a ray or two may slip through a passage portal).
 for k,c,T in closed:
  half=(T.tri.reshape(-1,3).max(axis=0)-T.tri.reshape(-1,3).min(axis=0))/2*.6
  targets=[c]+[c+half*np.array(v) for v in [(1,0,0),(-1,0,0),(0,1,0),(0,-1,0),(0,0,1),(0,0,-1)]]
  clear=sum(nearest(T,point,t) is None for t in targets)
  if clear>=5:return k
 return None

# Leak rays: 50 fibonacci directions to 700 m from every eye.
k=np.arange(50)+.5;phi=np.arccos(1-2*k/50);th=math.pi*(1+5**.5)*k;dirs=np.stack([np.cos(th)*np.sin(phi),np.cos(phi),np.sin(th)*np.sin(phi)],1)
leaks=[];rocks=[]
for e in eyes:
 for d in dirs:
  h=nearest(shells,e,e+d*700)
  if h is None:continue
  w=world.first_hit(e,e+d*700*h['t'])
  if w is not None:continue
  if h['culled']:leaks.append({'eye':e.round(2).tolist(),'direction':d.round(3).tolist(),'culledShell':h['key'],'meters':round(700*h['t'],2)})
  elif h['key'].startswith('land-') and h['point'][1]>e[1]-1 and inside_closed(h['point']):rocks.append({'eye':e.round(2).tolist(),'direction':d.round(3).tolist(),'terrain':h['key'],'meters':round(700*h['t'],2),'sky':inside_closed(h['point'])})
if rocks:failures.append({'test':'containment','count':len(rocks),'eyes':len({tuple(r['eye']) for r in rocks}),'examples':rocks[:8]})
# Distant terrain (beyond 120 m of the outer sky's centre, outside every
# closed sky's box) must sit >= TERRAIN_DIP below eye level from every eye so
# it never bands across the painted landscape (0.7.0 valley-shelf crests).
outer=max(skies,key=lambda r:np.ptp(r[3],axis=0).max())[3];oc=(outer.max(axis=0)+outer.min(axis=0))/2
land=Triangles(s,lambda key,mat:key.startswith('land-'));lv=land.tri.reshape(-1,3);lc=np.repeat(land.tri.mean(axis=1),3,axis=0)
far=np.hypot(lc[:,0]-oc[0],lc[:,2]-oc[2])>120
# The cragged mountain shell around a closed sky reaches ~15 m past its box.
for k,c,T in closed:far&=~np.all((lc>T.tri.reshape(-1,3).min(axis=0)-20)&(lc<T.tri.reshape(-1,3).max(axis=0)+20),axis=1)
fv=lv[far];dips=[]
for e in eyes:
 el=np.degrees(np.arctan2(fv[:,1]-e[1],np.hypot(fv[:,0]-e[0],fv[:,2]-e[2])));j=int(np.argmax(el));dips.append((float(el[j]),e,fv[j]))
worstdip=max(dips,key=lambda r:r[0])
terrain={'farVertices':int(far.sum()),'maxElevationDegrees':round(worstdip[0],2),'eye':worstdip[1].round(2).tolist(),'vertex':worstdip[2].round(2).tolist()}
if worstdip[0]>-TERRAIN_DIP:failures.append({'test':'terrainHorizon',**terrain})
if leaks:failures.append({'test':'leaks','count':len(leaks),'eyes':len({tuple(l['eye']) for l in leaks}),'examples':leaks[:8]})
if big_blend:failures.append({'test':'layers','transparentBackdrops':big_blend})

for key,mat,prim,pos,idx,slot in skies:
 row={'material':key,'alphaMode':mat.get('alphaMode','OPAQUE'),'doubleSided':bool(mat.get('doubleSided',False))}
 if row['alphaMode']!='OPAQUE' or row['doubleSided']:failures.append({'test':'layers','material':key,'detail':row})
 tex=s.doc['textures'][slot['index']];img=np.asarray(Image.open(a.package/s.doc['images'][tex['source']]['uri']).convert('RGB'),dtype=float);Hh,W=img.shape[:2]
 lum=img@[.299,.587,.114]
 def blur(x,r,axis):
  k=np.ones(2*r+1)/(2*r+1);return np.apply_along_axis(lambda v:np.convolve(np.pad(v,r,mode='wrap' if axis==1 else 'edge'),k,'valid'),axis,x)
 hp=lum-blur(blur(lum,4,0),4,1)
 band=slice(Hh//4,Hh*3//4)
 # Mirror ghost: high-pass column k against column W-2-k (last column
 # duplicates the first), versus the same offsets inside the image centre.
 def corr(x,y):
  x=x-x.mean();y=y-y.mean();return float((x*y).sum()/max(math.sqrt((x*x).sum()*(y*y).sum()),1e-9))
 mirror=np.mean([corr(hp[band,j],hp[band,W-2-j]) for j in range(4,33)])
 centre=np.mean([corr(hp[band,W//2+j],hp[band,W//2-1-j]) for j in range(4,33)])
 # Coherent row offsets: vertical high-pass of the row mean over 256
 # columns at the seam, relative to the same statistic at the image centre.
 def streak(cols):
  r=lum[band][:,cols].mean(axis=1);rh=r-np.convolve(np.pad(r,6,mode='edge'),np.ones(13)/13,'valid');return float(np.std(rh))
 # Each side separately: 0.7.0's ramp had opposite signs either side.
 streaks=max(streak(np.arange(W-257,W-1)),streak(np.arange(0,256)))/max(streak(np.arange(W//2-128,W//2+128)),1e-6)
 row['seamMirrorCorrelation']=round(mirror,3);row['centreMirrorCorrelation']=round(centre,3);row['seamRowStreakRatio']=round(streaks,3)
 # Relative to the same statistic at the image centre: smooth procedural
 # skies have near-zero high-pass energy and correlate everywhere.
 if mirror-centre>GHOST_MAX:failures.append({'test':'ghost','material':key,'mirrorCorrelation':row['seamMirrorCorrelation'],'centreCorrelation':row['centreMirrorCorrelation']})
 if streaks>STREAK_MAX:failures.append({'test':'ghost','material':key,'rowStreakRatio':row['seamRowStreakRatio']})
 # Per-texel step map (wraps in longitude).
 step=np.maximum(np.abs(np.roll(img,-1,axis=1)-img).max(axis=2),np.abs(np.diff(img,axis=0,append=img[-1:])).max(axis=2))
 seamstep=float(np.abs(img[:,0]-img[:,W-2]).max());row['seamColumnStepMax']=seamstep
 uv=s.accessor(prim['attributes']['TEXCOORD_0']);tri=pos[idx];tuv=uv[idx]
 # Magnification: largest texel edge in metres over eye distance and pixel angle.
 e1=tri[:,1]-tri[:,0];e2=tri[:,2]-tri[:,0];d1=(tuv[:,1]-tuv[:,0])*[W,Hh];d2=(tuv[:,2]-tuv[:,0])*[W,Hh]
 det=d1[:,0]*d2[:,1]-d1[:,1]*d2[:,0];ok=abs(det)>1e-9;det=np.where(ok,det,1)
 Ju=(e1*d2[:,1:2]-e2*d1[:,1:2])/det[:,None];Jv=(e2*d1[:,0:1]-e1*d2[:,0:1])/det[:,None]
 texel=np.where(ok,np.maximum(np.linalg.norm(Ju,axis=1),np.linalg.norm(Jv,axis=1)),0)
 normal=np.cross(e1,e2);centroid=tri.mean(axis=1);mag=np.zeros(len(tri));where=np.full(len(tri),-1)
 for i,e in enumerate(eyes):
  front=(normal*(centroid-e)).sum(axis=1)<0
  dist=np.sqrt(nearest_sq(np.repeat(e[None],len(tri),0),tri))
  mm=np.where(front,texel/np.maximum(dist,.05)/PIX,0);better=mm>mag;mag=np.where(better,mm,mag);where=np.where(better,i,where)
 # Local texture steps under every triangle's texel footprint.
 px=tuv*[W,Hh];lo=np.floor(px.min(axis=1)).astype(int)-1;hi=np.ceil(px.max(axis=1)).astype(int)+1;local=np.zeros(len(tri))
 for j in np.nonzero(mag>MAX_PAINTED_MAGNIFICATION)[0]:
  ys=np.arange(max(lo[j,1],0),min(hi[j,1],Hh));xs=np.arange(lo[j,0],hi[j,0])%W
  local[j]=step[np.ix_(ys,xs)].max() if len(ys) and len(xs) else 0
 blocky=np.nonzero((mag>MAX_PAINTED_MAGNIFICATION)&(local>SMOOTH_STEP))[0]
 worst=int(np.argmax(mag));row['maxScreenPixelsPerTexel']=round(float(mag[worst]),1);row['worstEye']=eyes[where[worst]].round(2).tolist()
 row['magnifiedTriangles']=int((mag>MAX_PAINTED_MAGNIFICATION).sum());row['blockyMagnifiedTriangles']=len(blocky)
 if len(blocky):
  j=blocky[np.argmax(mag[blocky]*local[blocky])]
  failures.append({'test':'magnification','material':key,'triangles':len(blocky),'worst':{'pixelsPerTexel':round(float(mag[j]),1),'texelStep':float(local[j]),'eye':eyes[where[j]].round(2).tolist(),'centroid':centroid[j].round(2).tolist()}})
 # Poles: rows under the first/last latitude ring are uniform.
 v=uv[:,1];ring=float(np.sort(np.unique(np.round(v,5)))[1])
 rows_top=img[:max(1,math.ceil(ring*Hh))];rows_bottom=img[int((1-ring)*Hh):]
 pole=float(max(np.ptp(rows_top,axis=1).max(),np.ptp(rows_bottom,axis=1).max()));row['poleBandRange']=pole
 if pole>POLE_RANGE:failures.append({'test':'poles','material':key,'range':pole})
 # Seam: continuous texture, or hidden behind opaque geometry for the band.
 seamv=np.nonzero((np.abs(uv[:,0])<1e-5)|(np.abs(uv[:,0]-1)<1e-5))[0]
 seamv=seamv[(uv[seamv,1]>.02)&(uv[seamv,1]<.98)];sp=pos[seamv]
 # Rows whose seam step stays visible must be hidden for every eye, by
 # architecture, terrain or another (nearer, opaque) sky.
 others=Triangles(s,lambda k2,m2,key=key:k2!=key and k2 in {k for k,*_ in skies})
 rowstep=np.abs(img[:,0]-img[:,W-2]).max(axis=1);hard=np.nonzero(rowstep>SEAM_SOFT_STEP)[0]
 row['seamHardRows']=len(hard);row['seamSoftRowsStepMax']=float(np.delete(rowstep,hard).max()) if len(hard)<Hh else None
 if len(hard):
  lats=sorted({int(5*round((90-(y+.5)/Hh*180)/5)) for y in hard if abs(90-(y+.5)/Hh*180)<85})
  # Recover the sky centre and radii from its bounding box (closed shells).
  c=(pos.max(axis=0)+pos.min(axis=0))/2;R=(pos.max(axis=0)-pos.min(axis=0))/2
  ang=np.arctan2(sp[:,0]-c[0],-(sp[:,2]-c[2]));az=float(np.arctan2(np.sin(ang).mean(),np.cos(ang).mean()));row['seamAzimuthDegrees']=round(math.degrees(az),2)
  visible=[]
  row['seamOccludedLatitudes']=lats
  for lat in lats:
   la=math.radians(lat);target=c+R*np.array([math.cos(la)*math.sin(az),math.sin(la),-math.cos(la)*math.cos(az)])
   for e in eyes:
    h=world.first_hit(e,target) or others.first_hit(e,target)
    if h is None:visible.append({'eye':e.round(2).tolist(),'latitude':lat})
  row['seamVisibleRays']=len(visible);row['seamRays']=len(eyes)*len(lats)
  if visible:failures.append({'test':'seam','material':key,'visibleRays':len(visible),'eyes':len({tuple(v['eye']) for v in visible}),'examples':visible[:6]})
 rows.append(row)
report={'status':'FAIL' if failures else 'PASS','method':__doc__.strip(),'eyes':len(eyes),'distantTerrain':terrain,'thresholds':{'maxPaintedMagnification':MAX_PAINTED_MAGNIFICATION,'smoothStep':SMOOTH_STEP,'poleRange':POLE_RANGE,'ghostMirrorCorrelation':GHOST_MAX,'rowStreakRatio':STREAK_MAX,'terrainDipDegrees':TERRAIN_DIP,'screen':[3840,2160],'verticalFovDegrees':60},'skies':rows,'failures':failures}
text=json.dumps(report,indent=2)+'\n'
if a.output:a.output.parent.mkdir(parents=True,exist_ok=True);a.output.write_text(text)
print(json.dumps({'status':report['status'],'eyes':len(eyes),'distantTerrain':terrain,'skies':rows,'failures':[{k:v for k,v in f.items() if k!='examples'} for f in failures]},indent=2))
sys.exit(1 if failures else 0)
