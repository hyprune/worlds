#!/usr/bin/env node
// SPDX-License-Identifier: MIT
// Geometry-only decode of a world format 0.7 scene for the Python tools
// (tools/gltf_io.py reads plain float/uint glTF only).
//   node decode.mjs <package-dir> <out-dir>
// Writes <out-dir>/scene.gltf + scene.bin: EXT_meshopt_compression decoded,
// KHR_mesh_quantization dequantised to float, textures and images dropped.
// Nodes, meshes and primitives keep their order and indices (no cleanup or
// prune), so world.json's node references still hold.
import fs from 'node:fs';
import path from 'node:path';
import {NodeIO} from '@gltf-transform/core';
import {ALL_EXTENSIONS} from '@gltf-transform/extensions';
import {dequantize} from '@gltf-transform/functions';
import {MeshoptDecoder} from 'meshoptimizer';

const [src,dst]=process.argv.slice(2);
if(!src||!dst)throw new Error('usage: decode.mjs <package-dir> <out-dir>');
await MeshoptDecoder.ready;
const io=new NodeIO().registerExtensions(ALL_EXTENSIONS).registerDependencies({'meshopt.decoder':MeshoptDecoder});
const world=JSON.parse(fs.readFileSync(path.join(src,'world.json'),'utf8'));
// Images are never read: each image URI resolves to an empty resource.
const json=JSON.parse(fs.readFileSync(path.join(src,world.scene),'utf8'));
const resources={};
for(const image of json.images||[])if(image.uri)resources[image.uri]=new Uint8Array(0);
for(const b of json.buffers||[])if(b.uri)resources[b.uri]=new Uint8Array(fs.readFileSync(path.join(src,path.dirname(world.scene),b.uri)));
const doc=await io.readJSON({json,resources});
await doc.transform(dequantize({pattern:/^POSITION$/}));
const root=doc.getRoot();
for(const t of root.listTextures())t.dispose();
for(const e of root.listExtensionsUsed())e.dispose();
for(const b of root.listBuffers().slice(1))b.dispose();
const buffer=root.listBuffers()[0]??doc.createBuffer();
for(const a of root.listAccessors())a.setBuffer(buffer);
buffer.setURI('scene.bin');
fs.mkdirSync(dst,{recursive:true});
await io.write(path.join(dst,'scene.gltf'),doc);
process.stdout.write(JSON.stringify({src,dst,nodes:root.listNodes().length,meshes:root.listMeshes().length})+'\n');
