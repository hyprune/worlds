#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Measure exported UV0 area density on substantial original tiled surfaces."""
import json,sys
from pathlib import Path
import numpy as np
from PIL import Image
from gltf_io import Scene
s=Scene(Path(sys.argv[1]));groups={}
for _,name,p,pos,indices in s.primitives():
 mat=s.doc['materials'][p['material']];slot=mat.get('pbrMetallicRoughness',{}).get('baseColorTexture')
 if not slot:continue
 tex=s.doc['textures'][slot['index']];uri=s.doc['images'][tex['source']]['uri'];asset=Path(uri).name.removesuffix('-albedo.png')
 if asset not in {'stone','metal','wood','rubber','brass','cloth','glass','panel'}:continue
 uv=s.accessor(p['attributes']['TEXCOORD_0']);width,height=Image.open(s.root/uri).size
 tri=pos[indices];area=np.linalg.norm(np.cross(tri[:,1]-tri[:,0],tri[:,2]-tri[:,0]),axis=1)*.5
 tuv=uv[indices];ab=tuv[:,1]-tuv[:,0];ac=tuv[:,2]-tuv[:,0];ua=np.abs(ab[:,0]*ac[:,1]-ab[:,1]*ac[:,0])*.5
 mask=(area>.02)&(ua>1e-8)
 density=np.sqrt(ua[mask]*width*height/area[mask]);groups.setdefault(asset,[]).extend(zip(density.tolist(),area[mask].tolist()))
rows=[]
for asset,values in sorted(groups.items()):
 if not values:continue
 values=sorted(values);density,area=np.array(values).T;cum=np.cumsum(area);median=float(density[np.searchsorted(cum,cum[-1]*.5)])
 assert 510<=median<=1026,(asset,'median density outside intended close-surface range',median)
 rows.append({'asset':asset,'substantialFaces':len(values),'surfaceAreaSquareMeters':round(float(cum[-1]),2),'areaWeightedMedianPxPerMeter':round(median,2),'fractionAreaWithin512to1024Tolerance':round(float(area[(density>=510)&(density<=1026)].sum()/cum[-1]),4)})
print(json.dumps({'status':'PASS','method':'sqrt(UV0 pixel area / physical triangle area), faces above .02 m2; bevels and unique trim/sheen sheets excluded','surfaces':rows},indent=2))
