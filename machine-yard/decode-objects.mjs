#!/usr/bin/env node
// SPDX-License-Identifier: MIT
// Plain copies of the optimised machine objects for Blender (bake occluders, review stills).
//   node machine-yard/decode-objects.mjs <objects/machines> <out-dir> <id>...
// Blender's importer reads neither KHR_texture_basisu nor EXT_meshopt_compression: this decodes
// meshopt, dequantises, and swaps each KTX2 image for the Lumen Reach PNG tile of the same
// name (the KTX2 files are encodes of those tiles). Writes <out-dir>/<id>.glb.
import fs from 'node:fs';
import path from 'node:path';
import {createRequire} from 'node:module';
const here = path.dirname(new URL(import.meta.url).pathname);
const require = createRequire(path.join(here, '../tools/gltf/package.json'));
const {NodeIO} = require('@gltf-transform/core');
const {ALL_EXTENSIONS} = require('@gltf-transform/extensions');
const {dequantize} = require('@gltf-transform/functions');
const {MeshoptDecoder} = require('meshoptimizer');

const [src, dst, ...ids] = process.argv.slice(2);
const tiles = path.join(here, '../lumen-reach/materials/tiles');
await MeshoptDecoder.ready;
const io = new NodeIO().registerExtensions(ALL_EXTENSIONS).registerDependencies({'meshopt.decoder': MeshoptDecoder});
fs.mkdirSync(dst, {recursive: true});
for (const id of ids) {
  const dir = path.join(src, id);
  const json = JSON.parse(fs.readFileSync(path.join(dir, 'object.gltf'), 'utf8'));
  const resources = {};
  for (const b of json.buffers || []) if (b.uri) resources[b.uri] = new Uint8Array(fs.readFileSync(path.join(dir, b.uri)));
  for (const im of json.images || []) {
    if (!im.uri) continue;
    const png = path.join(tiles, im.uri.replace(/\.ktx2$/, '.png'));
    resources[im.uri] = new Uint8Array(fs.readFileSync(fs.existsSync(png) ? png : path.join(dir, im.uri)));
  }
  const doc = await io.readJSON({json, resources});
  await doc.transform(dequantize());
  const root = doc.getRoot();
  for (const t of root.listTextures()) if (t.getMimeType() === 'image/ktx2') { t.setMimeType('image/png'); t.setURI(t.getURI().replace(/\.ktx2$/, '.png')); }
  for (const e of root.listExtensionsUsed())
    if (['EXT_meshopt_compression', 'KHR_texture_basisu', 'KHR_mesh_quantization', 'KHR_materials_variants'].includes(e.extensionName)) e.dispose();
  await io.write(path.join(dst, `${id}.glb`), doc);
  process.stdout.write(JSON.stringify({id, nodes: root.listNodes().length, meshes: root.listMeshes().length}) + '\n');
}
