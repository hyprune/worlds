#!/usr/bin/env node
// SPDX-License-Identifier: MIT
// Release budget report from glTF-Transform's inspect():
//   node tools/gltf/budgets.mjs <package> [--baseline <package>] [--output <json>]
// Triangles and draws count the visible scene only (helper collision and
// navigation nodes sit outside it). GPU MiB is glTF-Transform's VRAM estimate:
// every texture with its full mip chain (PNG as RGBA8; KTX2 by block format),
// lightmaps included, plus the visible vertex and index buffers. Core's own
// estimate (world::gpuBytes, check-package) may differ; both go in the report.
import fs from 'node:fs';
import path from 'node:path';
import {NodeIO} from '@gltf-transform/core';
import {ALL_EXTENSIONS} from '@gltf-transform/extensions';
import {inspect} from '@gltf-transform/functions';
import {MeshoptDecoder} from 'meshoptimizer';

const args=process.argv.slice(2);
const flag=name=>{const i=args.indexOf(name);if(i<0)return null;const v=args[i+1];args.splice(i,2);return v;};
const output=flag('--output'),baselineDir=flag('--baseline');
const MiB=x=>Math.round(x/1048576*100)/100;
await MeshoptDecoder.ready;
const io=new NodeIO().registerExtensions(ALL_EXTENSIONS).registerDependencies({'meshopt.decoder':MeshoptDecoder});

async function budgets(dir){
 const manifest=JSON.parse(fs.readFileSync(path.join(dir,'world.json'),'utf8'));
 const gltf=JSON.parse(fs.readFileSync(path.join(dir,manifest.scene),'utf8'));
 const doc=await io.read(path.join(dir,manifest.scene));
 const report=inspect(doc);const root=doc.getRoot();
 // glTF-Transform has one Texture per glTF image, in image order.
 const lightmapImages=new Set((manifest.lightmaps||[]).map(l=>gltf.textures[l.texture].source));
 let triangles=0,draws=0,vertexBytes=0,indexBytes=0;const perMesh=new Map();const seen=new Set();
 const visit=(node)=>{
  const mesh=node.getMesh();
  if(mesh)for(const prim of mesh.listPrimitives()){
   const idx=prim.getIndices();const pos=prim.getAttribute('POSITION');
   const t=prim.getMode()===4?Math.floor((idx?idx.getCount():pos.getCount())/3):0;
   triangles+=t;draws++;perMesh.set(mesh.getName()||'(unnamed)',(perMesh.get(mesh.getName()||'(unnamed)')||0)+t);
   if(!seen.has(prim)){seen.add(prim);for(const a of prim.listAttributes())vertexBytes+=a.getCount()*a.getElementSize()*a.getComponentSize();if(idx)indexBytes+=idx.getCount()*idx.getComponentSize();}
  }
  node.listChildren().forEach(visit);
 };
 (root.getDefaultScene()||root.listScenes()[0]).listChildren().forEach(visit);
 const textures=report.textures.properties.map((t,i)=>({index:i,name:t.name||t.uri,uri:t.uri,mimeType:t.mimeType,resolution:t.resolution,compression:t.compression,lightmap:lightmapImages.has(i),slots:t.slots,fileBytes:t.size,gpuBytes:t.gpuSize??0}));
 const sum=f=>textures.filter(f).reduce((s,t)=>s+t.gpuBytes,0);
 const collision=new Set((manifest.collision||[]).map(c=>c.node));let collisionTriangles=0;
 root.listNodes().forEach((node,i)=>{if(collision.has(i)&&node.getMesh())for(const p of node.getMesh().listPrimitives()){const x=p.getIndices();collisionTriangles+=Math.floor((x?x.getCount():p.getAttribute('POSITION').getCount())/3);}});
 const files=fs.readdirSync(dir,{recursive:true}).map(f=>path.join(dir,f)).filter(f=>fs.statSync(f).isFile());
 const gpu=sum(()=>true)+vertexBytes+indexBytes;
 return {world:manifest.id,version:manifest.version,formatVersion:manifest.formatVersion,
  visibleTriangles:triangles,drawCalls:draws,materials:root.listMaterials().length,collisionTriangles,
  textures:{count:textures.length,lightmaps:textures.filter(t=>t.lightmap).length,ktx2:textures.filter(t=>t.mimeType==='image/ktx2').length},
  gpuMiB:{total:MiB(gpu),materialTextures:MiB(sum(t=>!t.lightmap)),lightmaps:MiB(sum(t=>t.lightmap)),vertexBuffers:MiB(vertexBytes),indexBuffers:MiB(indexBytes)},
  packageMiB:MiB(files.reduce((s,f)=>s+fs.statSync(f).size,0)),
  extensionsUsed:gltf.extensionsUsed||[],extensionsRequired:gltf.extensionsRequired||[],
  largestTextures:[...textures].sort((a,b)=>b.gpuBytes-a.gpuBytes).slice(0,8).map(t=>({name:t.name,resolution:t.resolution,mimeType:t.mimeType,lightmap:t.lightmap,gpuMiB:MiB(t.gpuBytes)})),
  largestMeshes:[...perMesh].sort((a,b)=>b[1]-a[1]).slice(0,8).map(([name,tris])=>({name,triangles:tris})),
  inspectWarnings:[...new Set(Object.values(report).flatMap(r=>r.warnings||[]))]};
}

const result={tool:'glTF-Transform 4.5.1 inspect() + visible-scene traversal',method:'triangles/draws: visible scene primitives per node instance; GPU MiB: glTF-Transform VRAM estimate, full mip chains, lightmaps included, plus visible vertex/index buffers',...await budgets(args[0])};
if(baselineDir){
 const b=await budgets(baselineDir);
 result.baseline={version:b.version,visibleTriangles:b.visibleTriangles,drawCalls:b.drawCalls,gpuMiB:b.gpuMiB.total,packageMiB:b.packageMiB};
 result.delta={visibleTriangles:result.visibleTriangles-b.visibleTriangles,drawCalls:result.drawCalls-b.drawCalls,gpuMiB:MiB((result.gpuMiB.total-b.gpuMiB.total)*1048576),packageMiB:MiB((result.packageMiB-b.packageMiB)*1048576)};
}
const text=JSON.stringify(result,null,1)+'\n';
if(output){fs.mkdirSync(path.dirname(output),{recursive:true});fs.writeFileSync(output,text);}
process.stdout.write(text);
