#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Derive world visibility regions from geometry instead of hand-authoring them.

Precomputed-visibility cells (as engines place them over walkable surfaces):
- cells: a CELL x CELL grid over the Recast navmesh built from the package's
  collision (tools/navmesh), one cell per floor level of each column, spanning
  eye heights from crouch to jump apex. A camera outside every cell (flying,
  noclip) draws everything, as core's visibility format requires.
- units: the rendered mesh nodes (exclusive glTF subtrees); occluders are opaque
  triangles, single-sided back faces never occlude.
- from-cell visibility: tools/pvs/pvs.cpp (forward rays + segments to unit surface
  samples), batch work on the bake host (AGENTS.md rule 3), or --local for tests.
- conservative margin: each cell's set is unioned with its 26 neighbours'; units
  whose bounds come within NEAR m of a cell are visible from it.
- output: camera regions (maximal boxes of cells with identical sets, unioned when
  merged) and one owner area per visibility class listing its regions in
  visibleFrom; units visible from every region stay unowned (always drawn).

Writes a visibility spec in the authored format (areas with nodeNames) and a
report comparing it with the package's current regions at every cell eye sample.
"""
import argparse,hashlib,json,math,os,shlex,struct,subprocess,sys,tempfile,time
from collections import defaultdict
from pathlib import Path
import numpy as np
sys.path.insert(0,str(Path(__file__).parent))
from gltf_io import Scene

RADIUS,HEIGHT,CLIMB=.3,1.8,.35                 # RFC-0004 capsule, core step height
EYE_LOW,EYE_HIGH=1.0,1.7+5**2/(2*9.81)         # crouch eye .. eye at jump apex (5 m/s)
CELL=4.0;LEVEL_GAP=2.5;NEAR=2.0
HELPER=Path(__file__).parent/'navmesh'/'navmesh.mjs';KERNEL=Path(__file__).parent/'pvs'/'pvs.cpp'

def navmesh(tri):
 cs,ch=.1,.05
 cfg=dict(cs=cs,ch=ch,tileSize=128,walkableSlopeAngle=math.degrees(math.acos(.65)),walkableHeight=math.ceil(HEIGHT/ch-1e-6),
  walkableClimb=math.floor(CLIMB/ch+1e-6),walkableRadius=math.ceil(RADIUS/cs-1e-6),maxEdgeLen=int(12/cs),
  maxSimplificationError=1.3,minRegionArea=round(.5/cs),mergeRegionArea=round(2/cs),maxVertsPerPoly=6,
  detailSampleDist=1.0,detailSampleMaxError=ch,bounds=[(tri.min(axis=(0,1))-1).tolist(),(tri.max(axis=(0,1))+[1,HEIGHT+1,1]).tolist()])
 with tempfile.NamedTemporaryFile('w',suffix='.json') as f:
  json.dump({'positions':tri.reshape(-1).round(5).tolist(),'indices':list(range(len(tri)*3)),'config':cfg,'points':[],'rays':[],'widths':[]},f);f.flush()
  out=subprocess.run(['node',str(HELPER),f.name],capture_output=True,text=True)
 if out.returncode:sys.exit('navmesh helper failed: '+out.stderr[-2000:])
 return [np.array(p['verts'],float) for p in json.loads(out.stdout)['polys']]

def inside(poly,x,z):
 """Point in convex/simple polygon (x,z), even-odd."""
 px,pz=poly[:,0],poly[:,2];j=np.roll(np.arange(len(poly)),1)
 return bool(np.sum(((pz>z)!=(pz[j]>z))&(x<(px[j]-px)*(z-pz)/(pz[j]-pz+1e-12)+px))%2)

def floor_at(poly,x,z):
 """Height of a navmesh polygon at (x,z): least squares plane through its vertices."""
 A=np.column_stack([poly[:,0],poly[:,2],np.ones(len(poly))]);c=np.linalg.lstsq(A,poly[:,1],rcond=None)[0]
 return float(c[0]*x+c[1]*z+c[2])

def cells_from(polys):
 cols=defaultdict(list)
 for k,p in enumerate(polys):
  lo=np.floor(p[:,[0,2]].min(0)/CELL).astype(int);hi=np.floor(p[:,[0,2]].max(0)/CELL).astype(int)
  for i in range(lo[0],hi[0]+1):
   for j in range(lo[1],hi[1]+1):cols[(i,j)].append(k)
 cells=[]
 for (i,j),ks in cols.items():
  grid=[(i*CELL+(a+.5)*CELL/3,j*CELL+(b+.5)*CELL/3) for a in range(3) for b in range(3)]
  floors=[]
  for x,z in grid:
   for k in ks:
    if inside(polys[k],x,z):floors.append((floor_at(polys[k],x,z),x,z))
  # Every polygon also samples its centroid and its corners pulled 0.25 m
  # inward wherever they fall in this column: a small raised surface (stair
  # landing, platform) between the 3x3 grid points still gets its level, so
  # no walkable floor is left outside every region (check-navmesh).
  for k in ks:
   c=polys[k].mean(0)
   for v in [c]+[q+(c-q)*min(1,.25/max(float(np.linalg.norm((c-q)[[0,2]])),1e-6)) for q in polys[k]]:
    if math.floor(v[0]/CELL)==i and math.floor(v[2]/CELL)==j:floors.append((floor_at(polys[k],float(v[0]),float(v[2])) if inside(polys[k],float(v[0]),float(v[2])) else float(v[1]),float(v[0]),float(v[2])))
  floors.sort()
  levels=[]
  for f in floors:
   if levels and f[0]-levels[-1][-1][0]<LEVEL_GAP:levels[-1].append(f)
   else:levels.append([f])
  for lv in levels:
   ys=[f[0] for f in lv]
   eyes=[(x,y+h,z) for y,x,z in lv for h in (EYE_LOW,1.7,EYE_HIGH)]
   cells.append({'col':(i,j),'level':len([c for c in cells if c['col']==(i,j)]),'eyes':eyes,
    'min':[i*CELL,min(ys)+EYE_LOW-.05,j*CELL],'max':[(i+1)*CELL,max(ys)+EYE_HIGH+.05,(j+1)*CELL]})
 return cells

def units_and_triangles(s,collision):
 doc=s.doc;unit_of={};units=[];tri=[];owner=[];flags=[];area=defaultdict(float);samples=defaultdict(list)
 for i,name,prim,pos,idx in s.primitives():
  if i in collision:continue
  if i not in unit_of:unit_of[i]=len(units);units.append({'node':i,'name':name,'primitives':0,'min':[math.inf]*3,'max':[-math.inf]*3})
  u=unit_of[i];units[u]['primitives']+=1;t=pos[idx]
  mat=doc['materials'][prim['material']] if 'material' in prim else {}
  occluder=mat.get('alphaMode','OPAQUE')=='OPAQUE';double=bool(mat.get('doubleSided',False))
  tri.append(t);owner.extend([u]*len(t));flags.extend([(1 if occluder else 0)|(2 if double else 0)]*len(t))
  units[u]['min']=np.minimum(units[u]['min'],t.reshape(-1,3).min(0)).tolist();units[u]['max']=np.maximum(units[u]['max'],t.reshape(-1,3).max(0)).tolist()
  samples[u].append(t)
 return units,np.concatenate(tri).astype(np.float32),np.array(owner,np.int32),np.array(flags,np.uint8),samples

def surface_points(tris,n,rng):
 t=np.concatenate(tris);a=.5*np.linalg.norm(np.cross(t[:,1]-t[:,0],t[:,2]-t[:,0]),axis=1)
 # Every triangle's centroid for small units, area-weighted points otherwise; points sit
 # 1 mm off the surface along the normal so the segment ends in front of it.
 n_=np.cross(t[:,1]-t[:,0],t[:,2]-t[:,0]);n_/=np.maximum(np.linalg.norm(n_,axis=1,keepdims=True),1e-12)
 if len(t)<=n:k=np.arange(len(t));u=np.full(len(t),1/3);v=np.full(len(t),1/3)
 else:
  k=rng.choice(len(t),size=n,p=a/a.sum());u=rng.random(n);v=rng.random(n);f=u+v>1;u[f]=1-u[f];v[f]=1-v[f]
 p=t[k,0]+(t[k,1]-t[k,0])*u[:,None]+(t[k,2]-t[k,0])*v[:,None]
 return np.concatenate([p+n_[k]*1e-3,p-n_[k]*1e-3]).astype(np.float32)   # both sides: double-sided or either facing

def request(path,tri,owner,flags,targets,cells,forward):
 with open(path,'wb') as f:
  f.write(b'HPVS1\0\0\0'+struct.pack('<4I',len(tri),len(targets),len(cells),forward))
  rec=np.zeros(len(tri),dtype=[('p','<f4',9),('u','<i4'),('f','u1')]);rec['p']=tri.reshape(len(tri),9);rec['u']=owner;rec['f']=flags;f.write(rec.tobytes())
  for pts in targets:f.write(struct.pack('<I',len(pts)));f.write(np.asarray(pts,np.float32).tobytes())
  for c in cells:e=np.asarray(c['eyes'],np.float32);f.write(struct.pack('<I',len(e)));f.write(e.tobytes())

def run_kernel(req,res,local,host):
 if local:
  exe=Path(tempfile.gettempdir())/'hyprune-pvs';subprocess.run(['g++','-O2','-std=c++20','-pthread',str(KERNEL),'-o',str(exe)],check=True)
  out=subprocess.run([str(exe),str(req),str(res),'2'],check=True,capture_output=True,text=True).stdout
 else:
  remote='hyprune-bake/pvs';q=shlex.quote
  subprocess.run(['ssh','-o','BatchMode=yes',host,f'mkdir -p {remote}'],check=True)
  subprocess.run(['rsync','-az',str(KERNEL),str(req),f'{host}:{remote}/'],check=True)
  cmd=f'cd {remote} && g++ -O3 -march=native -std=c++20 -pthread pvs.cpp -o pvs && ./pvs {q(req.name)} result.bin $(nproc)'
  out=subprocess.run(['ssh','-o','BatchMode=yes',host,cmd],check=True,capture_output=True,text=True).stdout
  subprocess.run(['rsync','-az',f'{host}:{remote}/result.bin',str(res)],check=True)
 data=res.read_bytes();assert data[:8]==b'HPVR1\0\0\0';nc,nu=struct.unpack('<2I',data[8:16])
 return json.loads(out.strip().splitlines()[-1]),np.frombuffer(data[16:],np.uint8).reshape(nc,nu)

def merge(cells,vis):
 """Greedy maximal boxes over each level band: grow along x, then z, through cells with identical sets."""
 key={(c['col'],c['level']):k for k,c in enumerate(cells)};done=set();regions=[]
 for k in sorted(range(len(cells)),key=lambda k:(cells[k]['level'],cells[k]['col'])):
  if k in done:continue
  c=cells[k];s=vis[k].tobytes();(i0,j0),lv=c['col'],c['level']
  same=lambda i,j:(q:=key.get(((i,j),lv))) is not None and q not in done and vis[q].tobytes()==s and abs(cells[q]['min'][1]-c['min'][1])<LEVEL_GAP
  i1=i0
  while same(i1+1,j0):i1+=1
  j1=j0
  while all(same(i,j1+1) for i in range(i0,i1+1)):j1+=1
  members=[key[((i,j),lv)] for i in range(i0,i1+1) for j in range(j0,j1+1)];done.update(members)
  regions.append({'cells':members,'set':vis[k].copy(),'min':np.min([cells[q]['min'] for q in members],0).tolist(),'max':np.max([cells[q]['max'] for q in members],0).tolist()})
 return regions

def main():
 p=argparse.ArgumentParser(description=__doc__,formatter_class=argparse.RawDescriptionHelpFormatter)
 p.add_argument('package',type=Path);p.add_argument('--output',type=Path,required=True,help='directory for spec, report and request')
 p.add_argument('--local',action='store_true',help='run the kernel locally (small tests only)');p.add_argument('--host',default=os.environ.get('HYPRUNE_BAKE_HOST','10.2.2.2'))
 p.add_argument('--apply',type=Path,help='write a copy of the package with the derived regions here (never edits the input)')
 p.add_argument('--in-place',action='store_true',help='build step: write the derived regions into the package itself')
 p.add_argument('--targets',type=int,default=2048);p.add_argument('--forward',type=int,default=4096);p.add_argument('--seed',type=int,default=7009)
 a=p.parse_args();a.output.mkdir(parents=True,exist_ok=True);started=time.time()
 s=Scene(a.package);m=s.manifest
 collision={c['node'] for c in m.get('collision',[])}|({m['navigation']['node']} if m.get('navigation') else set())
 coll=np.concatenate([pos[idx] for i,_,_,pos,idx in s.primitives(visible=False) if i in collision]).astype(float)
 polys=navmesh(coll);cells=cells_from(polys)
 units,tri,owner,flags,tris=units_and_triangles(s,collision)
 rng=np.random.default_rng(a.seed);targets=[surface_points(tris[u],a.targets,rng) for u in range(len(units))]
 req=a.output/'request.bin';request(req,tri,owner,flags,targets,cells,a.forward)
 stats,raw=run_kernel(req,a.output/'result.bin',a.local,a.host)
 vis=raw>0
 # Near rule and 26-neighbour dilation (same or adjacent level band).
 for k,c in enumerate(cells):
  for u,un in enumerate(units):
   if all(un['min'][d]-NEAR<=c['max'][d] and un['max'][d]+NEAR>=c['min'][d] for d in range(3)):vis[k,u]=True
 by_col=defaultdict(list)
 for k,c in enumerate(cells):by_col[c['col']].append(k)
 dilated=vis.copy()
 for k,c in enumerate(cells):
  i,j=c['col']
  for di in (-1,0,1):
   for dj in (-1,0,1):
    for q in by_col.get((i+di,j+dj),[]):
     if cells[q]['min'][1]<=c['max'][1]+LEVEL_GAP and cells[q]['max'][1]>=c['min'][1]-LEVEL_GAP:dilated[k]|=vis[q]
 regions=merge(cells,dilated)
 everywhere=np.all([r['set'] for r in regions],axis=0)
 classes=defaultdict(list)
 for u in range(len(units)):
  if everywhere[u]:continue
  classes[tuple(k for k,r in enumerate(regions) if r['set'][u])].append(u)
 areas=[{'id':f'cell-{k:03d}','bounds':{'min':[round(v,3) for v in r['min']],'max':[round(v,3) for v in r['max']]},'nodeNames':[],'visibleFrom':[],
  'reason':f'{len(r["cells"])} cells, {int(r["set"].sum())} of {len(units)} units potentially visible'} for k,r in enumerate(regions)]
 for n,(sigma,members) in enumerate(sorted(classes.items(),key=lambda kv:kv[1])):
  home=max(sigma,key=lambda k:len(regions[k]['cells'])) if sigma else None
  b=areas[home]['bounds'] if home is not None else {'min':[-1e5,-1e5,-1e5],'max':[-99999,-99999,-99999]}
  areas.append({'id':'owner-'+'-'.join(units[u]['name'].lower().removeprefix('visual-') for u in members)[:100],'bounds':b,
   'nodeNames':[units[u]['name'] for u in members],'visibleFrom':[areas[k]['id'] for k in sigma],
   'reason':f'derived: visible from {len(sigma)} of {len(regions)} cell regions'})
 assert len(areas)<=256,'too many visibility areas; increase CELL'
 spec={'formatVersion':m['formatVersion'],'version':m['version'],'unassignedAlwaysVisible':True,'generator':{'tool':'tools/derive-visibility.py',
  'cell':CELL,'eye':[EYE_LOW,EYE_HIGH],'near':NEAR,'targets':a.targets,'forwardRays':a.forward,'seed':a.seed,'package':m['id']+' '+m['version'],
  'sceneSHA256':hashlib.sha256((a.package/m['scene']).read_bytes()).hexdigest()},'areas':areas}
 (a.output/'visibility.generated.json').write_text(json.dumps(spec,indent=1)+'\n')
 region_of={q:k for k,r in enumerate(regions) for q in r['cells']}
 (a.output/'cells.json').write_text(json.dumps({'units':[un['name'] for un in units],'cells':[{'min':c['min'],'max':c['max'],'eyes':len(c['eyes']),
  'sampled':[units[u]['name'] for u in np.nonzero(raw[k])[0]],'visible':[units[u]['name'] for u in np.nonzero(dilated[k])[0]],'region':region_of[k]} for k,c in enumerate(cells)]})+'\n')
 # Comparison at every cell eye sample with core's semantics.
 node_units={un['node']:u for u,un in enumerate(units)};prims=np.array([un['primitives'] for un in units])
 def visible(areas_,owners,eye):
  cur={a_['id'] for a_ in areas_ if all(a_['bounds']['min'][d]<=eye[d]<=a_['bounds']['max'][d] for d in range(3))}
  out=np.ones(len(units),bool)
  if not cur:return out
  for a_ in areas_:
   if not (a_['id'] in cur or set(a_['visibleFrom'])&cur):
    for u in owners.get(a_['id'],[]):out[u]=False
  return out
 by_name={un['name']:u for u,un in enumerate(units)}
 gen_owners={a_['id']:[by_name[n] for n in a_['nodeNames']] for a_ in areas}
 hand=m.get('visibility',{}).get('areas',[])
 hand_owners={a_['id']:[node_units[n] for n in a_['nodes'] if n in node_units] for a_ in hand}
 rows=[];loss=0
 for k,c in enumerate(cells):
  for e in c['eyes']:
   g=visible(areas,gen_owners,e);h=visible(hand,hand_owners,e) if hand else np.ones(len(units),bool)
   truth=raw[k]>0
   loss+=int(np.any(truth&~g))
   rows.append((int(prims[g].sum()),int(prims[h].sum()),int(prims[truth].sum())))
 rows=np.array(rows)
 report={'package':m['id']+' '+m['version'],'seconds':round(time.time()-started,1),'kernel':stats,'navmeshPolygons':len(polys),'cells':len(cells),
  'regions':len(regions),'ownerAreas':len(classes),'areas':len(areas),'units':[{k:un[k] for k in ('node','name','primitives')}|{'regions':int(sum(r['set'][u] for r in regions))} for u,un in enumerate(units)],
  'eyeSamples':len(rows),'submittedPrimitives':{'all':int(prims.sum()),'generatedMean':round(float(rows[:,0].mean()),2),'handWrittenMean':round(float(rows[:,1].mean()),2),
  'sampledTruthMean':round(float(rows[:,2].mean()),2),'generatedLessThanHand':int((rows[:,0]<rows[:,1]).sum()),'generatedMoreThanHand':int((rows[:,0]>rows[:,1]).sum())},
  'eyesWhereGeneratedHidesASampledVisibleUnit':loss}
 (a.output/'report.json').write_text(json.dumps(report,indent=1)+'\n')
 if a.in_place:
  import world_visibility
  manifest=json.loads((a.package/'world.json').read_text());world_visibility.annotate(manifest,s.doc,a.output/'visibility.generated.json')
  (a.package/'world.json').write_text(json.dumps(manifest,indent=2)+'\n');report['applied']=str(a.package)
 if a.apply:
  import shutil,world_visibility
  target=a.apply/a.package.name;assert target.resolve()!=a.package.resolve(),'refusing to edit the input package'
  shutil.rmtree(target,ignore_errors=True);shutil.copytree(a.package,target)
  manifest=json.loads((target/'world.json').read_text());world_visibility.annotate(manifest,s.doc,a.output/'visibility.generated.json')
  (target/'world.json').write_text(json.dumps(manifest,indent=2)+'\n');report['applied']=str(target)
 print(json.dumps({k:v for k,v in report.items() if k!='units'}))

if __name__=='__main__':main()
