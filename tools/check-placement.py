#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Continuous window sweeps against actual exported visible triangles.
Triangle/OBB SAT includes all face, box-axis and edge cross-product axes.
Checks both requested window sizes and all declared free-placement positions.
"""
import argparse,json,math,sys
from pathlib import Path
import numpy as np
from gltf_io import Scene
p=argparse.ArgumentParser();p.add_argument('package',type=Path);p.add_argument('--output',type=Path);a=p.parse_args();s=Scene(a.package);m=s.manifest
from world_contract import homes
areas_,rows_,zones_=homes(m);mounts={'areas':areas_,'mounts':rows_};placement={'zones':zones_}
assert mounts.get('areas') and placement.get('zones'),'mounts and free-placement declarations required'
triangles=[];labels=[]
for ni,name,primitive,positions,indices in s.primitives():
 t=positions[indices];triangles.append(t);labels.extend([name+' / '+s.doc['materials'][primitive.get('material',0)].get('name','material')]*len(t))
triangles=np.concatenate(triangles);lo=triangles.min(axis=1);hi=triangles.max(axis=1)

def rotation(q):
 x,y,z,w=q
 return np.array([[1-2*(y*y+z*z),2*(x*y-z*w),2*(x*z+y*w)],[2*(x*y+z*w),1-2*(x*x+z*z),2*(y*z-x*w)],[2*(x*z-y*w),2*(y*z+x*w),1-2*(x*x+y*y)]])

def intersect(center,R,half):
 center=np.array(center);half=np.array(half);extent=abs(R)@half
 candidate=np.flatnonzero(np.all(hi>center-extent+1e-6,axis=1)&np.all(lo<center+extent-1e-6,axis=1))
 if not len(candidate):return []
 t=(triangles[candidate]-center)@R;live=np.ones(len(t),bool)
 def separate(axis):
  dots=np.sum(t*axis[:,None,:],axis=-1);r=np.sum(abs(axis)*half,axis=-1)
  return (dots.min(axis=1)>r+1e-6)|(dots.max(axis=1)<-r-1e-6)
 for k in range(3):
  axis=np.zeros((len(t),3));axis[:,k]=1;live&=~separate(axis)
 edges=[t[:,1]-t[:,0],t[:,2]-t[:,1],t[:,0]-t[:,2]]
 live&=~separate(np.cross(edges[0],edges[1]))
 for e in edges:
  for unit in np.eye(3):live&=~separate(np.cross(e,np.broadcast_to(unit,e.shape)))
 return [labels[candidate[i]] for i in np.flatnonzero(live)]

failures=[];checks=[];anchors={r['id']:r for r in m['anchors']};sizes=[(1.6,.9),(3.2,1.8)]
for r in mounts['mounts']:
 anchor=anchors[r['anchorId']];R=rotation(anchor['pose']['rotation']);origin=np.array(anchor['pose']['position']);depth=r.get('clearanceMeters',4)
 assert depth>=(16 if r['role']=='mounted-workspace' else 4),('insufficient mount approach',r['anchorId'],depth)
 for w,h in list(dict.fromkeys(sizes+[tuple(anchor['size'])])):
  # Include the actual mount rectangle, particularly whole-workspace walls.
  # Start beyond the physical bezel; continuous swept slab, not discrete samples.
  start=.10;end=depth;center=origin+R[:,2]*(start+end)/2
  hit=intersect(center,R,[w/2,h/2,(end-start)/2])
  checks.append({'anchorId':anchor['id'],'windowSize':[w,h],'sweepMeters':[start,end],'hits':len(hit)})
  if hit:failures.append({'anchorId':anchor['id'],'windowSize':[w,h],'intersections':sorted(set(hit))})
for zone in placement['zones']:
 low=np.array(zone['bounds']['min']);high=np.array(zone['bounds']['max']);assert np.all(high>low)
 # Entire reserved volume must be empty, so every placement/sweep within it is safe.
 hit=intersect((low+high)/2,np.eye(3),(high-low)/2)
 if hit:failures.append({'zoneId':zone['id'],'intersections':sorted(set(hit))})
 # Then sweep actual window rectangles over all three coordinates with both yaw axes.
 for w,h in sizes:
  margin=zone.get('clearance',.15);r=w/2+margin;rh=h/2+margin
  xs=np.linspace(low[0]+r,high[0]-r,5);ys=np.linspace(low[1]+rh,high[1]-rh,3);zs=np.linspace(low[2]+r,high[2]-r,5)
  assert xs[-1]>=xs[0] and ys[-1]>=ys[0] and zs[-1]>=zs[0],('zone too small',zone['id'],w,h)
  count=0
  for yaw in [0,math.pi/2]:
   R=rotation([0,math.sin(yaw/2),0,math.cos(yaw/2)])
   for x in xs:
    for y in ys:
     # A continuous Z sweep through the usable box for each fixed X/Y.
     center=np.array([x,y,(zs[0]+zs[-1])/2]);half=np.array([w/2,h/2,.025]);extent=abs(R)@half;halfworld=extent+np.array([0,0,(zs[-1]-zs[0])/2]);hit=intersect(center,np.eye(3),halfworld);count+=1
     if hit:failures.append({'zoneId':zone['id'],'windowSize':[w,h],'intersections':sorted(set(hit))})
  checks.append({'zoneId':zone['id'],'windowSize':[w,h],'continuousSweeps':count,'yawDegrees':[0,90]})
for area in mounts['areas']:
 assert area['primaryAnchor'] in anchors
 owned=[r for r in mounts['mounts'] if r['areaId']==area['id']]
 assert sum(r['role']=='mounted-workspace' for r in owned)==1
 assert set(area['toolAnchors'])=={r['anchorId'] for r in owned if r['role']=='tool'}
 assert all(r['workspaceSlot']==area['workspaceSlot'] for r in owned)
report={'status':'FAIL' if failures else 'PASS','visibleTriangles':len(triangles),'checks':checks,'failures':failures,'method':'continuous triangle/OBB SAT against exported visual geometry; all reserved-volume interiors and two window sizes'}
if a.output:a.output.write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps(report,indent=2));sys.exit(1 if failures else 0)
