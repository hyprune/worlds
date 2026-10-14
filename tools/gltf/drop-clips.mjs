#!/usr/bin/env node
// SPDX-License-Identifier: MIT
// Remove named animations from a character glTF, everything else kept (meshopt geometry and
// KTX2 textures pass through; meshopt is re-encoded): for a character that should take a
// role's clip from a motion pack instead of its own (embedded clips win).
//   node tools/gltf/drop-clips.mjs IN.glb OUT.glb CLIP [CLIP ...]
import { NodeIO } from '@gltf-transform/core';
import { ALL_EXTENSIONS } from '@gltf-transform/extensions';
import { prune } from '@gltf-transform/functions';
import { MeshoptDecoder, MeshoptEncoder } from 'meshoptimizer';

const [input, output, ...names] = process.argv.slice(2);
if (!input || !output || !names.length) {
  console.error('usage: drop-clips.mjs IN.glb OUT.glb CLIP [CLIP ...]');
  process.exit(2);
}
await Promise.all([MeshoptDecoder.ready, MeshoptEncoder.ready]);
const io = new NodeIO().registerExtensions(ALL_EXTENSIONS)
  .registerDependencies({ 'meshopt.decoder': MeshoptDecoder, 'meshopt.encoder': MeshoptEncoder });
const doc = await io.read(input);
const dropped = [];
for (const anim of doc.getRoot().listAnimations()) {
  if (!names.includes(anim.getName())) continue;
  dropped.push(anim.getName());
  for (const s of anim.listSamplers()) {
    const [i, o] = [s.getInput(), s.getOutput()];
    s.dispose();
    for (const a of [i, o]) if (a && a.listParents().every((p) => p === doc.getRoot())) a.dispose();
  }
  anim.dispose();
}
const missing = names.filter((n) => !dropped.includes(n));
if (missing.length) {
  console.error(`no animation named ${missing.join(', ')}`);
  process.exit(1);
}
await doc.transform(prune({ propertyTypes: ['ACCESSOR'], keepAttributes: true, keepIndices: true }));
await io.write(output, doc);
console.log(JSON.stringify({ dropped, clips: doc.getRoot().listAnimations().map((a) => a.getName()) }));
