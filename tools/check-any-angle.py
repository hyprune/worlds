#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Geometry/UV tests for a continuous environment at every view direction."""
import argparse,json,itertools
from collections import Counter
from pathlib import Path
import numpy as np
from PIL import Image
from gltf_io import Scene
p=argparse.ArgumentParser(description=__doc__);p.add_argument('package',type=Path);p.add_argument('--output',type=Path,required=True);p.add_argument('--portals',type=Path,default=Path(__file__).resolve().parents[1]/'lumen-reach/portals.json');a=p.parse_args();s=Scene(a.package);rows=[]
# Declared passage portals (Blender metres) in glTF coordinates. Sky vertices
# created by a portal cut lie on chords, so shape/UV identities exempt them.
PORTALS=[]
for pt in json.loads(a.portals.read_text())['portals']:
 zs=[pt['floor']['z'],pt['floor']['z']+pt['floor']['slope']*(pt['y'][1]-pt['y'][0]),pt['ceiling']['z'],pt['ceiling']['z']+pt['ceiling']['slope']*(pt['y'][1]-pt['y'][0])]
 PORTALS.append((pt['id'],np.array([pt['x'][0],min(zs),-pt['y'][1]])-.05,np.array([pt['x'][1],max(zs),-pt['y'][0]])+.05,set(pt['objects'])))
SPECS=json.loads(a.portals.read_text())['portals']
def in_portal(points):
 return np.any([np.all((points>lo)&(points<hi),axis=1) for _,lo,hi,_ in PORTALS],axis=0) if PORTALS else np.zeros(len(points),bool)
def on_portal_plane(points):
 # Bisecting the faces that cross a portal leaves vertices on its planes a
 # face or so beyond the box; they are exact chords, not shape drift.
 out=np.zeros(len(points),bool)
 for pt,(_,lo,hi,_) in zip(SPECS,PORTALS):
  b=np.column_stack([points[:,0],-points[:,2],points[:,1]]);near=np.all((points>lo-10)&(points<hi+10),axis=1);y0=pt['y'][0]
  d=[b[:,0]-pt['x'][0],b[:,0]-pt['x'][1],b[:,1]-pt['y'][0],b[:,1]-pt['y'][1],b[:,2]-pt['floor']['z']-pt['floor']['slope']*(b[:,1]-y0),b[:,2]-pt['ceiling']['z']-pt['ceiling']['slope']*(b[:,1]-y0)]
  out|=near&np.any(np.abs(np.array(d))<1e-3,axis=0)
 return out
for _,name,prim,points,indices in s.primitives():
 mat=s.doc['materials'][prim['material']];key=mat.get('name','').split('--')[-1]
 if key not in ['sky-v7','night-sky-v7']:continue
 # Shapes mirror any_angle.vista/night: the basin is a power-4 superellipsoid.
 center=np.array([20,0,-65] if key=='sky-v7' else [57,0,-170]);radii=np.array([310,310,310] if key=='sky-v7' else [70,76,58.8]);power=2 if key=='sky-v7' else 4
 normalized=(points-center)/radii;cut=in_portal(points)|on_portal_plane(points)
 shape=np.sqrt((abs(normalized[:,0])**power+abs(normalized[:,2])**power)**(2/power)+normalized[:,1]**2)
 assert np.max(abs(shape[~cut]-1))<1e-5,(key,'sky shape')
 rounded=np.round(points,4);_,weld=np.unique(rounded,axis=0,return_inverse=True);tri=weld[indices];edges=Counter(tuple(sorted((int(x),int(y)))) for f in tri for x,y in zip(f,np.roll(f,-1)))
 assert all(n<=2 for n in edges.values()),(key,'sky nonmanifold')
 # Only declared portals may open the sky; every hole's rim lies inside one.
 boundary=[e for e,n in edges.items() if n==1];rim=np.unique(np.array(boundary,dtype=int).reshape(-1)) if boundary else np.zeros(0,int)
 first=np.zeros(len(set(weld))+1,int);first[weld]=np.arange(len(weld));assert np.all(in_portal(points[first[rim]])),(key,'sky hole outside a declared portal')
 parent=list(range(len(first)))
 def root(i):
  while parent[i]!=i:parent[i]=parent[parent[i]];i=parent[i]
  return i
 for x,y in boundary:parent[root(x)]=root(y)
 holes=len({root(int(i)) for i in rim})
 assert len(set(weld))-len(edges)+len(tri)==2-holes,(key,'sky topology')
 v=points[indices];norm=np.cross(v[:,1]-v[:,0],v[:,2]-v[:,0]);assert np.all(np.linalg.norm(norm,axis=1)>1e-5),(key,'zero area')
 assert np.all(np.sum(norm*(v.mean(axis=1)-center),axis=1)<0),(key,'outward sky winding')
 uv=s.accessor(prim['attributes']['TEXCOORD_0']);direction=normalized/np.linalg.norm(normalized,axis=1)[:,None];expected=.5-np.arcsin(np.clip(direction[:,1],-1,1))/np.pi
 assert np.max(abs(uv[~cut,1]-expected[~cut]))<1e-4,(key,'nonlinear/clamped latitude')
 assert np.max(np.ptp(uv[indices][:,:,0],axis=1))<.016,(key,'longitude triangle crosses seam')
 texture=s.doc['textures'][mat['pbrMetallicRoughness']['baseColorTexture']['index']];sampler=s.doc['samplers'][texture['sampler']]
 assert sampler['wrapS']==10497 and sampler['wrapT']==33071
 image=np.asarray(Image.open(a.package/s.doc['images'][texture['source']]['uri']).convert('RGB'),dtype=int)
 assert np.array_equal(image[:,0],image[:,-1]),(key,'longitude image seam')
 assert np.ptp(image[0],axis=0).max()==0 and np.ptp(image[-1],axis=0).max()==0,(key,'polar streaks')
 row={'material':key,'triangles':len(tri),'closedManifold':holes==0,'portalHoles':holes,'portalVertices':int(cut.sum()),'inwardWinding':True,'fullLatitudeUV':True,'seamlessLongitude':True,'uniformPoles':True}
 if key=='sky-v7':
  corners=np.array(list(itertools.product([-36,110],[-6,60],[-180,17])));dist=np.linalg.norm(corners-center,axis=1);row['reviewEnvelope']={'min':[-36,-6,-180],'max':[110,60,17]};row['conservativeMaxSkyDistance']=float(max(dist)+310);assert max(dist)<310 and max(dist)+310<500,'far clip or outside sky'
 rows.append(row)
assert len(rows)==2,('missing closed skies',rows)
# All exposed architectural materials have a texture. All helper guard volumes
# are collision-only and absent from the default visible scene.
for _,name,prim,_,_ in s.primitives():
 if name.startswith(('Collision','Guard collision')):raise AssertionError(('visible helper',name))
 if not name.startswith('Visual-') or name in ['Visual-vista','Visual-foliage']:continue
 mat=s.doc['materials'][prim['material']];assert 'baseColorTexture' in mat.get('pbrMetallicRoughness',{}) or 'emissiveTexture' in mat,(name,mat['name'],'untextured surface')
result={'status':'PASS','scope':'Closed sky topology (holes only at declared passage portals), winding, all-latitude UVs, texture edge and pole continuity, conservative far-clip envelope, architectural texture coverage. Engine random/owner images remain a separate visual review; finite samples do not prove arbitrary mesh quality.','skies':rows}
a.output.parent.mkdir(parents=True,exist_ok=True);a.output.write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result,indent=2))
