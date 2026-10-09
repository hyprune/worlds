#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Geometry/UV tests for a continuous environment at every view direction."""
import argparse,json,itertools
from collections import Counter
from pathlib import Path
import numpy as np
from PIL import Image
from gltf_io import Scene
p=argparse.ArgumentParser(description=__doc__);p.add_argument('package',type=Path);p.add_argument('--output',type=Path,required=True);a=p.parse_args();s=Scene(a.package);rows=[]
for _,name,prim,points,indices in s.primitives():
 mat=s.doc['materials'][prim['material']];key=mat.get('name','').split('--')[-1]
 if key not in ['sky-v7','night-sky-v7']:continue
 center=np.array([20,0,-65] if key=='sky-v7' else [57,0,-170]);radii=np.array([310,310,310] if key=='sky-v7' else [70,76,58])
 normalized=(points-center)/radii
 assert np.max(abs(np.linalg.norm(normalized,axis=1)-1))<1e-5,(key,'sphere shape')
 rounded=np.round(points,4);_,weld=np.unique(rounded,axis=0,return_inverse=True);tri=weld[indices];edges=Counter(tuple(sorted((int(x),int(y)))) for f in tri for x,y in zip(f,np.roll(f,-1)))
 assert all(n==2 for n in edges.values()),(key,'sky boundary/nonmanifold')
 assert len(set(weld))-len(edges)+len(tri)==2,(key,'sphere topology')
 v=points[indices];norm=np.cross(v[:,1]-v[:,0],v[:,2]-v[:,0]);assert np.all(np.linalg.norm(norm,axis=1)>1e-5),(key,'zero area')
 assert np.all(np.sum(norm*(v.mean(axis=1)-center),axis=1)<0),(key,'outward sky winding')
 uv=s.accessor(prim['attributes']['TEXCOORD_0']);expected=.5-np.arcsin(np.clip(normalized[:,1],-1,1))/np.pi
 assert np.max(abs(uv[:,1]-expected))<1e-4,(key,'nonlinear/clamped latitude')
 assert np.max(np.ptp(uv[indices][:,:,0],axis=1))<.016,(key,'longitude triangle crosses seam')
 texture=s.doc['textures'][mat['pbrMetallicRoughness']['baseColorTexture']['index']];sampler=s.doc['samplers'][texture['sampler']]
 assert sampler['wrapS']==10497 and sampler['wrapT']==33071
 image=np.asarray(Image.open(a.package/s.doc['images'][texture['source']]['uri']).convert('RGB'),dtype=int)
 assert np.array_equal(image[:,0],image[:,-1]),(key,'longitude image seam')
 assert np.ptp(image[0],axis=0).max()==0 and np.ptp(image[-1],axis=0).max()==0,(key,'polar streaks')
 row={'material':key,'triangles':len(tri),'closedManifold':True,'inwardWinding':True,'fullLatitudeUV':True,'seamlessLongitude':True,'uniformPoles':True}
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
result={'status':'PASS','scope':'Closed sky topology, winding, all-latitude UVs, texture edge and pole continuity, conservative far-clip envelope, architectural texture coverage. Engine random/owner images remain a separate visual review; finite samples do not prove arbitrary mesh quality.','skies':rows}
a.output.parent.mkdir(parents=True,exist_ok=True);a.output.write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result,indent=2))
