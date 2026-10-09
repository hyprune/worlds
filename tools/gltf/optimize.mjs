#!/usr/bin/env node
// SPDX-License-Identifier: MIT
// World format 0.7 optimisation (flagged: needs the 0.7 contract merged).
//   node optimize.mjs --plan <src>                       texture encode plan (JSON)
//   node optimize.mjs <src> <dst> [--ktx2 <dir>]         optimised package
// Geometry: glTF-Transform reorder + quantize (16-bit positions/texcoords) +
// EXT_meshopt_compression, the settings of `gltf-transform meshopt
// --quantize-position 16 --quantize-texcoord 16`, but with cleanup off: the
// stock cleanup prunes and dedups materials, which renumbers what world.json
// references. Textures: material images encoded by basisu (remote-optimize.sh)
// become KHR_texture_basisu in place. Lightmaps stay PNG (draft 0.7 rule);
// glTF-Transform writes no texture entry for an image no material uses, so
// lightmap textures and their samplers are re-appended and world.json is
// re-pointed. verify.mjs then diffs every index world.json references.
import fs from 'node:fs';
import path from 'node:path';
import {NodeIO} from '@gltf-transform/core';
import {ALL_EXTENSIONS,EXTMeshoptCompression,KHRTextureBasisu} from '@gltf-transform/extensions';
import {reorder,quantize,prune} from '@gltf-transform/functions';
import {PropertyType} from '@gltf-transform/core';
import {MeshoptDecoder,MeshoptEncoder} from 'meshoptimizer';

const args=process.argv.slice(2);
const flag=name=>{const i=args.indexOf(name);if(i<0)return null;const v=args[i+1];args.splice(i,2);return v;};
const plan=args.includes('--plan')?(args.splice(args.indexOf('--plan'),1),true):false;
const ktx2Dir=flag('--ktx2');
await Promise.all([MeshoptDecoder.ready,MeshoptEncoder.ready]);
const io=new NodeIO().registerExtensions(ALL_EXTENSIONS).registerDependencies({'meshopt.decoder':MeshoptDecoder,'meshopt.encoder':MeshoptEncoder});
const load=dir=>{const world=JSON.parse(fs.readFileSync(path.join(dir,'world.json'),'utf8'));return {world,gltf:JSON.parse(fs.readFileSync(path.join(dir,world.scene),'utf8'))};};

// How basisu must encode each material image: colour (sRGB), data (linear)
// or normal map. An image used both ways stays PNG.
function encodePlan(gltf,world){
 const lightmaps=new Set(world.lightmaps.map(l=>gltf.textures[l.texture].source));
 const modes=new Map();
 const use=(info,mode)=>{if(!info)return;const img=gltf.textures[info.index].source;if(!lightmaps.has(img))(modes.get(img)||modes.set(img,new Set()).get(img)).add(mode);};
 for(const m of gltf.materials){const p=m.pbrMetallicRoughness||{};use(p.baseColorTexture,'srgb');use(m.emissiveTexture,'srgb');use(p.metallicRoughnessTexture,'linear');use(m.occlusionTexture,'linear');use(m.normalTexture,'normal');}
 const items=[],skipped=[];
 for(const [img,set] of modes){const uri=gltf.images[img].uri;
  if(set.size>1||!/\.png$/i.test(uri)){skipped.push({uri,reason:set.size>1?'colour and data use':'not PNG'});continue;}
  items.push({image:img,png:uri,ktx2:uri.replace(/\.png$/i,'.ktx2'),mode:[...set][0]});}
 return {items,skipped,lightmapImages:[...lightmaps].map(i=>gltf.images[i].uri)};
}

const [src,dst]=args;
const {world,gltf}=load(src);
if(plan){process.stdout.write(JSON.stringify(encodePlan(gltf,world),null,1)+'\n');process.exit(0);}
if(!dst)throw new Error('usage: optimize.mjs <src> <dst> [--ktx2 <dir>] | --plan <src>');
fs.rmSync(dst,{recursive:true,force:true});fs.cpSync(src,dst,{recursive:true});

const doc=await io.read(path.join(src,world.scene));
await doc.transform(
 reorder({encoder:MeshoptEncoder,target:'size',cleanup:false}),
 quantize({pattern:/^(POSITION|TEXCOORD|JOINTS|WEIGHTS|COLOR)(_\d+)?$/,patternTargets:/^(POSITION|TEXCOORD|JOINTS|WEIGHTS|COLOR|NORMAL|TANGENT)(_\d+)?$/,
  quantizePosition:16,quantizeTexcoord:16,quantizeNormal:8,cleanup:false}),
 // Drop only the float accessors quantize replaced; world.json never
 // references accessors, so nothing it points at moves.
 prune({propertyTypes:[PropertyType.ACCESSOR],keepAttributes:true,keepIndices:true,keepLeaves:true}));
doc.createExtension(EXTMeshoptCompression).setRequired(true).setEncoderOptions({method:EXTMeshoptCompression.EncoderMethod.FILTER});

const encoded=[];
if(ktx2Dir){
 const {items}=encodePlan(gltf,world);const textures=doc.getRoot().listTextures();
 for(const it of items){
  const file=path.join(ktx2Dir,path.basename(it.ktx2));
  if(!fs.existsSync(file))throw new Error('missing encoded texture '+file);
  // glTF-Transform keeps one Texture per glTF image, in image order.
  textures[it.image].setImage(fs.readFileSync(file)).setMimeType('image/ktx2').setURI(it.ktx2);
  fs.rmSync(path.join(dst,it.png));encoded.push(it);
 }
 if(encoded.length)doc.createExtension(KHRTextureBasisu).setRequired(true);
}
await io.write(path.join(dst,world.scene),doc);

// Re-append the lightmap textures world.json points at, with their samplers.
const out=JSON.parse(fs.readFileSync(path.join(dst,world.scene),'utf8'));
out.textures??=[];out.samplers??=[];
const same=(a,b)=>JSON.stringify(a??{})===JSON.stringify(b??{});
const remap={};
for(const l of world.lightmaps){
 if(l.texture in remap)continue;
 const t=gltf.textures[l.texture],uri=gltf.images[t.source].uri,sampler=t.sampler===undefined?undefined:gltf.samplers[t.sampler];
 const image=out.images.findIndex(i=>i.uri===uri);if(image<0)throw new Error('lightmap image lost: '+uri);
 let s;if(sampler){s=out.samplers.findIndex(x=>same(x,sampler));if(s<0)s=out.samplers.push(sampler)-1;}
 let ti=out.textures.findIndex(x=>x.source===image&&x.sampler===s&&!x.extensions);
 if(ti<0)ti=out.textures.push({source:image,...(s===undefined?{}:{sampler:s})})-1;
 remap[l.texture]=ti;
}
fs.writeFileSync(path.join(dst,world.scene),JSON.stringify(out));
const newWorld=structuredClone(world);
newWorld.lightmaps.forEach(l=>{l.texture=remap[l.texture];});
newWorld.formatVersion='0.7';
fs.writeFileSync(path.join(dst,'world.json'),JSON.stringify(newWorld,null,2)+'\n');

// Provenance travels with the encoded file.
const prov=path.join(dst,'texture-provenance.json');
if(fs.existsSync(prov)&&encoded.length){
 const rows=JSON.parse(fs.readFileSync(prov,'utf8'));const by=new Map(encoded.map(e=>[e.png,e]));
 for(const r of rows){const e=by.get(r.path);if(e)Object.assign(r,{path:e.ktx2,encodedFrom:e.png,encoding:`basisu 2.1.0 UASTC LDR 4x4, Zstandard, full mips, ${e.mode}`});}
 fs.writeFileSync(prov,JSON.stringify(rows,null,2)+'\n');
}
process.stdout.write(JSON.stringify({src,dst,formatVersion:'0.7',encodedTextures:encoded.length,lightmapTextures:remap,extensionsRequired:out.extensionsRequired||[]},null,1)+'\n');
