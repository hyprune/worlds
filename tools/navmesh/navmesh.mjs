#!/usr/bin/env node
// SPDX-License-Identifier: MIT
// Recast/Detour (recast-navigation-js) helper for tools/check-navmesh.py.
// Input: request JSON path (collision triangles, voxel config, queries).
// Output (stdout): navmesh polygons with island ids, point and width queries.
// World semantics, gates, allow-lists and the SVG live in the Python check.
import fs from 'node:fs';
import {init,NavMeshQuery} from 'recast-navigation';
import {generateTiledNavMesh} from 'recast-navigation/generators';

const req=JSON.parse(fs.readFileSync(process.argv[2],'utf8'));
await init();
const started=performance.now();
const {success,navMesh,error}=generateTiledNavMesh(req.positions,req.indices,req.config);
if(!success){console.error('navmesh generation failed:',error);process.exit(2);}
const buildMs=performance.now()-started;
const query=new NavMeshQuery(navMesh);
const NULL_LINK=0xffffffff;

// Every polygon with its vertices; union-find over Detour links gives the
// islands exactly as pathfinding sees them.
const polys=[];const index=new Map();const parent=[];
const find=i=>{while(parent[i]!==i){parent[i]=parent[parent[i]];i=parent[i];}return i;};
const links=[];
for(let t=0;t<navMesh.getMaxTiles();t++){
 const tile=navMesh.getTile(t);const header=tile.header();
 if(!header)continue;
 const base=navMesh.getPolyRefBase(tile);
 for(let p=0;p<header.polyCount();p++){
  const poly=tile.polys(p);const verts=[];
  for(let j=0;j<poly.vertCount();j++){const v=poly.verts(j);verts.push([tile.verts(3*v),tile.verts(3*v+1),tile.verts(3*v+2)].map(x=>Math.round(x*1000)/1000));}
  const ref=base+p;index.set(ref,polys.length);parent.push(polys.length);polys.push({ref,verts});
  for(let l=poly.firstLink();(l>>>0)!==NULL_LINK;){const link=tile.links(l);links.push([ref,link.ref()]);l=link.next();}
 }
}
for(const [a,b] of links){if(!index.has(b))continue;const x=find(index.get(a)),y=find(index.get(b));if(x!==y)parent[Math.max(x,y)]=Math.min(x,y);}
const islandOf=new Map();
polys.forEach((p,i)=>{const r=find(i);if(!islandOf.has(r))islandOf.set(r,islandOf.size);p.island=islandOf.get(r);});

const nearest=(p,h)=>{
 const r=query.findNearestPoly({x:p[0],y:p[1],z:p[2]},{halfExtents:{x:h[0],y:h[1],z:h[2]}});
 if(!r.success||!r.nearestRef)return null;
 const q=r.nearestPoint;return {ref:r.nearestRef,point:[q.x,q.y,q.z],island:polys[index.get(r.nearestRef)].island,overPoly:r.isOverPoly};
};
const points=(req.points||[]).map(q=>({id:q.id,hit:nearest(q.p,q.h)}));
// Clear width across a walking direction: Detour raycasts along the surface
// to the eroded navmesh border on both sides (the caller adds the radius back).
const widths=(req.widths||[]).map(w=>{
 const hit=nearest(w.p,[.15,.6,.15]);
 if(!hit)return {id:w.id,hit:null};
 const side=s=>{
  const end={x:hit.point[0]+s*w.side[0]*w.reach,y:hit.point[1],z:hit.point[2]+s*w.side[2]*w.reach};
  const r=query.raycast(hit.ref,{x:hit.point[0],y:hit.point[1],z:hit.point[2]},end);
  return r.t>1?w.reach:r.t*w.reach;
 };
 return {id:w.id,hit,left:side(1),right:side(-1)};
});
// Straight walks along the surface (route edges, stair lanes): the first
// navmesh border hit, plus the shortest-path length for the detour ratio.
const rays=(req.rays||[]).map(r=>{
 const a=nearest(r.a,r.h),b=nearest(r.b,r.h);
 if(!a||!b)return {id:r.id,start:a,end:b};
 const hit=query.raycast(a.ref,{x:a.point[0],y:a.point[1],z:a.point[2]},{x:b.point[0],y:b.point[1],z:b.point[2]});
 const path=query.computePath({x:a.point[0],y:a.point[1],z:a.point[2]},{x:b.point[0],y:b.point[1],z:b.point[2]},{halfExtents:{x:r.h[0],y:r.h[1],z:r.h[2]},maxPathPolys:4096,maxStraightPathPoints:4096});
 let length=null;
 if(path.success)length=path.path.slice(1).reduce((s,q,i)=>s+Math.hypot(q.x-path.path[i].x,q.y-path.path[i].y,q.z-path.path[i].z),0);
 return {id:r.id,start:a,end:b,t:hit.t>1?1:hit.t,pathLength:length};
});
process.stdout.write(JSON.stringify({buildMs:Math.round(buildMs),polys,islands:islandOf.size,points,widths,rays}));
