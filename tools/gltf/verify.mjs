#!/usr/bin/env node
// SPDX-License-Identifier: MIT
// Equivalence and index diff of an optimised package against its source:
//   node verify.mjs <src> <dst> [--output <json>]
// - world.json is unchanged except formatVersion and lightmaps[].texture;
// - every node, mesh and material keeps its index and name (world.json and
//   core address them by index);
// - every world.json reference resolves to the same thing: lightmap textures
//   to the same PNG and sampler, materials/nodes to the same names;
// - per primitive: same material, attributes and triangle count; world AABB
//   within the mesh's 16-bit quantisation step (quantize uses one volume per
//   mesh); world-space surface and TEXCOORD_1 (lightmap) area within the
//   bound that step allows (sum of triangle perimeters x step);
// - collision vertices within 5 mm of the source (walking tolerance);
// - required extensions: the source's plus only the three draft-0.7 ones.
import fs from 'node:fs';
import path from 'node:path';
import {NodeIO} from '@gltf-transform/core';
import {ALL_EXTENSIONS} from '@gltf-transform/extensions';
import {MeshoptDecoder} from 'meshoptimizer';

const args=process.argv.slice(2);
const oi=args.indexOf('--output');const output=oi>=0?args.splice(oi,2)[1]:null;
const [src,dst]=args;
await MeshoptDecoder.ready;
const io=new NodeIO().registerExtensions(ALL_EXTENSIONS).registerDependencies({'meshopt.decoder':MeshoptDecoder});
const failures=[];const fail=(what,detail)=>{if(failures.length<200)failures.push({what,...detail});};
const pkg=async dir=>{const world=JSON.parse(fs.readFileSync(path.join(dir,'world.json'),'utf8'));
 return {world,gltf:JSON.parse(fs.readFileSync(path.join(dir,world.scene),'utf8')),doc:await io.read(path.join(dir,world.scene))};};
const A=await pkg(src),B=await pkg(dst);
const ALLOWED=new Set([...(A.gltf.extensionsRequired||[]),'EXT_meshopt_compression','KHR_mesh_quantization','KHR_texture_basisu']);
for(const e of B.gltf.extensionsRequired||[])if(!ALLOWED.has(e))fail('extension outside the 0.7 contract',{extension:e});

// world.json: only the two expected fields may change.
const strip=w=>{const c=structuredClone(w);delete c.formatVersion;c.lightmaps=c.lightmaps.map(({texture,...r})=>r);return JSON.stringify(c);};
if(strip(A.world)!==strip(B.world))fail('world.json changed beyond formatVersion/lightmap texture indices',{});

// Indexed objects keep index and name.
for(const k of ['nodes','meshes','materials']){
 const a=A.gltf[k]||[],b=B.gltf[k]||[];
 if(a.length!==b.length)fail(`${k} count`,{src:a.length,dst:b.length});
 a.forEach((x,i)=>{if(b[i]?.name!==x.name)fail(`${k} renumbered`,{index:i,src:x.name,dst:b[i]?.name});});
}
A.gltf.nodes.forEach((n,i)=>{const m=B.gltf.nodes[i];if(m&&(n.mesh===undefined)!==(m.mesh===undefined))fail('node mesh binding',{index:i});
 if(m&&JSON.stringify(n.children||[])!==JSON.stringify(m.children||[]))fail('node hierarchy',{index:i});});

// Lightmap references: same PNG, same sampler parameters, same material.
const tex=(g,i)=>{const t=g.textures[i];return {uri:g.images[t.source]?.uri,sampler:t.sampler===undefined?{}:g.samplers[t.sampler]};};
A.world.lightmaps.forEach((l,i)=>{const r=B.world.lightmaps[i];
 const a=tex(A.gltf,l.texture),b=r.texture===undefined||!B.gltf.textures[r.texture]?null:tex(B.gltf,r.texture);
 if(!b||a.uri!==b.uri||JSON.stringify(a.sampler)!==JSON.stringify(b.sampler))fail('lightmap texture',{lightmap:i,src:a,dst:b});
 if(!/\.png$/i.test(b?.uri||''))fail('lightmap must stay PNG',{lightmap:i,dst:b?.uri});
 if(A.gltf.materials[l.material]?.name!==B.gltf.materials[r.material]?.name)fail('lightmap material',{lightmap:i});});
// Every material slot still reaches the same source image (PNG or its KTX2).
const stem=u=>u?.replace(/\.(png|ktx2)$/i,'');
const slots=m=>{const p=m.pbrMetallicRoughness||{};return {baseColor:p.baseColorTexture,metallicRoughness:p.metallicRoughnessTexture,normal:m.normalTexture,occlusion:m.occlusionTexture,emissive:m.emissiveTexture};};
const slotImage=(g,info)=>{if(!info)return null;const t=g.textures[info.index];const s=t.extensions?.KHR_texture_basisu?.source??t.source;return {image:stem(g.images[s]?.uri),texCoord:info.texCoord??0};};
A.gltf.materials.forEach((m,i)=>{const sa=slots(m),sb=slots(B.gltf.materials[i]||{});
 for(const k in sa){if(JSON.stringify(slotImage(A.gltf,sa[k]))!==JSON.stringify(slotImage(B.gltf,sb[k])))fail('material texture slot',{material:m.name,slot:k});}});

// Geometry, decoded and dequantised by glTF-Transform.
const mul=(m,v)=>[m[0]*v[0]+m[4]*v[1]+m[8]*v[2]+m[12],m[1]*v[0]+m[5]*v[1]+m[9]*v[2]+m[13],m[2]*v[0]+m[6]*v[1]+m[10]*v[2]+m[14]];
const tris=(prim)=>{const idx=prim.getIndices();const n=idx?idx.getCount():prim.getAttribute('POSITION').getCount();const out=[];for(let i=0;i+2<n;i+=3)out.push(idx?[idx.getScalar(i),idx.getScalar(i+1),idx.getScalar(i+2)]:[i,i+1,i+2]);return out;};
const area=(p,q,r)=>{const u=[q[0]-p[0],q[1]-p[1],q[2]-p[2]],v=[r[0]-p[0],r[1]-p[1],r[2]-p[2]];const c=[u[1]*v[2]-u[2]*v[1],u[2]*v[0]-u[0]*v[2],u[0]*v[1]-u[1]*v[0]];return Math.hypot(...c)/2;};
function stats(node,prim){
 const m=node.getWorldMatrix();const pos=prim.getAttribute('POSITION');const uv0=prim.getAttribute('TEXCOORD_0'),uv1=prim.getAttribute('TEXCOORD_1');
 const P=[];for(let i=0;i<pos.getCount();i++)P.push(mul(m,pos.getElement(i,[])));
 const lo=[Infinity,Infinity,Infinity],hi=[-Infinity,-Infinity,-Infinity];P.forEach(p=>p.forEach((x,k)=>{lo[k]=Math.min(lo[k],x);hi[k]=Math.max(hi[k],x);}));
 let surface=0,uvArea=0,perimeter=0,uvPerimeter=0,uv0Area=0,uv0Perimeter=0;const T=tris(prim);const d=(p,q)=>Math.hypot(...p.map((x,k)=>x-q[k]));
 for(const [a,b,c] of T){surface+=area(P[a],P[b],P[c]);perimeter+=d(P[a],P[b])+d(P[b],P[c])+d(P[c],P[a]);if(uv1){const ua=uv1.getElement(a,[]),ub=uv1.getElement(b,[]),uc=uv1.getElement(c,[]);uvArea+=Math.abs((ub[0]-ua[0])*(uc[1]-ua[1])-(uc[0]-ua[0])*(ub[1]-ua[1]))/2;uvPerimeter+=d(ua,ub)+d(ub,uc)+d(uc,ua);}
  if(uv0){const ua=uv0.getElement(a,[]),ub=uv0.getElement(b,[]),uc=uv0.getElement(c,[]);uv0Area+=Math.abs((ub[0]-ua[0])*(uc[1]-ua[1])-(uc[0]-ua[0])*(ub[1]-ua[1]))/2;uv0Perimeter+=d(ua,ub)+d(ub,uc)+d(uc,ua);}}
 return {P,lo,hi,surface,uvArea,perimeter,uvPerimeter,uv0Area,uv0Perimeter,uv0Span:uv0?Math.max(...[0,1].map(k=>{let lo=Infinity,hi=-Infinity;for(let i=0;i<uv0.getCount();i++){const v=uv0.getElement(i,[])[k];lo=Math.min(lo,v);hi=Math.max(hi,v);}return hi-lo;})):0,triangles:T.length,attributes:prim.listSemantics().sort().join(','),material:prim.getMaterial()?.getName()};
}
const collision=new Set(A.world.collision.map(c=>c.node));if(A.world.navigation)collision.add(A.world.navigation.node);
const na=A.doc.getRoot().listNodes(),nb=B.doc.getRoot().listNodes();
let primitives=0,maxCollisionError=0,maxBoxError=0;
na.forEach((node,i)=>{
 const ma=node.getMesh(),mb=nb[i]?.getMesh();if(!ma||!mb)return;
 const pa=ma.listPrimitives(),pb=mb.listPrimitives();
 if(pa.length!==pb.length){fail('primitive count',{node:node.getName()});return;}
 const all=pa.map(p=>stats(node,p));
 // One quantisation volume per mesh: its step bounds every primitive.
 const step=Math.max(...[0,1,2].map(k=>Math.max(...all.map(s=>s.hi[k]))-Math.min(...all.map(s=>s.lo[k]))))/65535*2+1e-5;
 pa.forEach((p,j)=>{
  const a=all[j],b=stats(nb[i],pb[j]);primitives++;
  for(const k of ['triangles','attributes','material'])if(a[k]!==b[k])fail('primitive '+k,{node:node.getName(),primitive:j,src:a[k],dst:b[k]});
  const box=Math.max(...a.lo.map((x,k)=>Math.abs(x-b.lo[k])),...a.hi.map((x,k)=>Math.abs(x-b.hi[k])));maxBoxError=Math.max(maxBoxError,box);
  if(box>step)fail('world bounds moved',{node:node.getName(),primitive:j,error:box,step});
  const bound={surface:a.perimeter*step+1e-6,uvArea:a.uvPerimeter*2/65535+1e-9,uv0Area:a.uv0Perimeter*2*Math.max(1,a.uv0Span)/65535+1e-9};
  for(const k of ['surface','uvArea','uv0Area'])if(Math.abs(a[k]-b[k])>bound[k])fail(k+' changed',{node:node.getName(),primitive:j,src:a[k],dst:b[k],bound:bound[k]});
  if(collision.has(i)){
   // Nearest source vertex for every optimised vertex (small meshes).
   for(const q of b.P){let best=Infinity;for(const r of a.P){const d=(q[0]-r[0])**2+(q[1]-r[1])**2+(q[2]-r[2])**2;if(d<best)best=d;}maxCollisionError=Math.max(maxCollisionError,Math.sqrt(best));}
  }
 });
});
if(maxCollisionError>.005)fail('collision moved beyond 5 mm',{maxCollisionError});

const size=d=>fs.readdirSync(d,{recursive:true}).map(f=>path.join(d,f)).filter(f=>fs.statSync(f).isFile()).reduce((s,f)=>s+fs.statSync(f).size,0);
const report={status:failures.length?'FAIL':'PASS',src,dst,formatVersion:B.world.formatVersion,extensionsRequired:B.gltf.extensionsRequired||[],
 counts:{nodes:B.gltf.nodes.length,meshes:B.gltf.meshes.length,materials:B.gltf.materials.length,primitives,lightmaps:B.world.lightmaps.length,ktx2Images:B.gltf.images.filter(i=>/\.ktx2$/i.test(i.uri||'')).length},
 maxCollisionErrorMeters:+maxCollisionError.toFixed(6),maxWorldBoundsErrorMeters:+maxBoxError.toFixed(6),
 packageMiB:{src:+(size(src)/1048576).toFixed(2),dst:+(size(dst)/1048576).toFixed(2)},failures};
const text=JSON.stringify(report,null,1)+'\n';
if(output)fs.writeFileSync(output,text);
process.stdout.write(text);process.exitCode=failures.length?1:0;
