#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Asset/reference/UV contract audit; schema validation is a separate target."""
import json, sys
from pathlib import Path
import numpy as np
from PIL import Image
from gltf_io import Scene
root=Path(sys.argv[1]);s=Scene(root);g=s.doc;m=s.manifest
assert not any(p.is_symlink() for p in root.rglob('*')),'package symlink'
for a in root.rglob('*'):
 if a.is_file():assert a.stat().st_size<=128*1024**2,(a,'single-file budget')
for container in ['buffers','images']:
 for obj in g.get(container,[]):
  if 'uri' in obj:
   p=Path(obj['uri']);assert not p.is_absolute() and '..' not in p.parts and ':' not in str(p)
   assert (root/p).is_file(),p
for field in ['scene','preview']:
 assert (root/m[field]).is_file(),field
assert len(m['anchors'])>=6
assert m['attribution'][0]['path']=='.'
assert m['navigation']['node']<len(g['nodes'])
helper={m['navigation']['node']}|{c['node'] for c in m['collision']}
assert not helper&s.visible(),'helper geometry is visible'
light={a['material']:a for a in m['lightmaps']}
assert len(light)==len(m['lightmaps'])
for a in light.values():
 assert a['material']<len(g['materials']) and a['texture']<len(g['textures'])
 assert a['texCoord']==1 and a['intensity']>0
assert all(c['node']<len(g['nodes']) for c in m['collision'])
provenance=json.loads((root/'texture-provenance.json').read_text())
assert len({r['path'] for r in provenance})==len(provenance),'duplicate texture provenance'
assert {p.relative_to(root).as_posix() for p in (root/'textures').glob('*.png')}=={r['path'] for r in provenance},'incomplete per-texture provenance'
assert all(r['author'] and r['license']=='CC-BY-4.0' and r['recipe'] for r in provenance),'missing provenance fields'
rows=[];triangle_total=0
# Raster interior occupancy independently detects intersecting exported UV1 triangles.
# Shared triangle edges are excluded, including triangulated quad diagonals.
for ni,name in [(i,n.get('name','')) for i,n in enumerate(g['nodes']) if i in s.visible() and 'mesh' in n]:
 coverage=np.zeros((1024,1024),dtype=np.uint8);uvarea=0;tris=0
 for i,n,p,pos,indices in s.primitives():
  if i!=ni:continue
  assert p.get('mode',4)==4
  material=p.get('material');mat=g['materials'][material]
  if 'KHR_materials_unlit' in mat.get('extensions',{}):
   assert material not in light,(name,'unlit material must not receive irradiance')
   tris+=len(indices);continue
  assert 'TEXCOORD_0' in p['attributes']
  assert material in light,(name,'missing lighting binding')
  assert 'TEXCOORD_1' in p['attributes']
  uv=s.accessor(p['attributes']['TEXCOORD_1']);assert np.isfinite(uv).all()
  assert (uv>=-1e-6).all() and (uv<=1.000001).all()
  assert mat.get('pbrMetallicRoughness',{}).get('baseColorTexture',{}).get('texCoord',0)==0
  for tri in uv[indices]:
   a,b,c=tri;u=b-a;v=c-a;den=u[0]*v[1]-v[0]*u[1];uvarea+=abs(den)*.5;tris+=1
   if abs(den)<1e-13:continue
   lo=np.maximum(0,np.floor(np.min(tri,axis=0)*1024).astype(int));hi=np.minimum(1024,np.ceil(np.max(tri,axis=0)*1024).astype(int))
   yy,xx=np.mgrid[lo[1]:hi[1],lo[0]:hi[0]];dx=(xx+.5)/1024-a[0];dy=(yy+.5)/1024-a[1]
   f=(dx*v[1]-dy*v[0])/den;h=(u[0]*dy-u[1]*dx)/den
   inside=(f>1e-5)&(h>1e-5)&(f+h<1-1e-5)
   coverage[lo[1]:hi[1],lo[0]:hi[0]]+=inside.astype(np.uint8)
 overlap=int(np.sum(coverage>1));assert overlap==0,(name,'UV1 overlap pixels',overlap)
 assert uvarea<=1.001,(name,uvarea)
 triangle_total+=tris;rows.append({'node':name,'triangles':tris,'uv1Area':round(float(uvarea),5),'overlapSamples':overlap})
decoded=sum(Image.open(root/g['images'][t['source']]['uri']).width*Image.open(root/g['images'][t['source']]['uri']).height*4 for t in g['textures'])
# Match M1 Renderer::prepare: expanded visible vertices (40 bytes each),
# every mip of a linear view, plus an sRGB view for every color/emissive texture.
color=set()
for mat in g['materials']:
 for slot in [mat.get('pbrMetallicRoughness',{}).get('baseColorTexture'),mat.get('emissiveTexture')]:
  if slot:color.add(slot['index'])
mipped=0
for i,t in enumerate(g['textures']):
 w,h=Image.open(root/g['images'][t['source']]['uri']).size
 while True:
  mipped+=w*h*4*(2 if i in color else 1)
  if w==1 and h==1:break
  w=max(1,w//2);h=max(1,h//2)
geometry=triangle_total*3*40;gpu=mipped+geometry
buffers=sum(b['byteLength'] for b in g['buffers'])
assert gpu<=512*1024**2,('M1 GPU budget including mips and color/data views',gpu)
size=sum(p.stat().st_size for p in root.rglob('*') if p.is_file());assert size<1024**3
report={'status':'PASS','packageBytes':size,'decodedTextureBytes':decoded,'conservativeGpuBytes':gpu,'mippedTextureViewsBytes':mipped,'expandedGeometryBytes':geometry,'colorTextureViews':len(color),'textureObjects':len(g['textures']),'textureProvenanceEntries':len(provenance),'visualTriangles':triangle_total,'anchors':len(m['anchors']),'collisionNodes':len(m['collision']),'lightmapBindings':len(light),'UV1':rows}
print(json.dumps(report,indent=2))
