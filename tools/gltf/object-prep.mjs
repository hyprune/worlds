#!/usr/bin/env node
// SPDX-License-Identifier: MIT
// Make a glTF readable by Blender's importer (tools/object-import, thumbnails):
// meshopt and quantisation are decoded and KTX2 textures unpacked to PNG.
//   node object-prep.mjs IN.gltf|.glb OUT.glb [--basisu PATH]
// KTX2 needs basisu (tools/remote-optimize.sh builds it on the bake host).
import fs from 'node:fs';
import os from 'node:os';
import path from 'node:path';
import {execFileSync} from 'node:child_process';
import {NodeIO} from '@gltf-transform/core';
import {ALL_EXTENSIONS} from '@gltf-transform/extensions';
import {dequantize} from '@gltf-transform/functions';
import {MeshoptDecoder} from 'meshoptimizer';

const args = process.argv.slice(2);
const flag = name => { const i = args.indexOf(name); return i < 0 ? undefined : args.splice(i, 2)[1]; };
const basisu = flag('--basisu') || path.join(os.homedir(), 'opt/hyprune/basisu-2.1.0/src/bin/basisu');
const [input, output] = args;
if (!input || !output) { console.error('usage: object-prep.mjs IN OUT.glb [--basisu PATH]'); process.exit(2); }
await MeshoptDecoder.ready;
const io = new NodeIO().registerExtensions(ALL_EXTENSIONS).registerDependencies({'meshopt.decoder': MeshoptDecoder});
const doc = await io.read(input), root = doc.getRoot();
let unpacked = 0;
const ktx2 = root.listTextures().filter(t => t.getMimeType() === 'image/ktx2');
if (ktx2.length) {
  if (!fs.existsSync(basisu)) throw new Error(`KTX2 textures need basisu (${basisu})`);
  const tmp = fs.mkdtempSync(path.join(os.tmpdir(), 'object-prep-'));
  try {
    for (const [i, texture] of ktx2.entries()) {
      const file = path.join(tmp, `t${i}.ktx2`);
      fs.writeFileSync(file, texture.getImage());
      execFileSync(basisu, ['-unpack', '-no_ktx', '-file', file], {stdio: 'ignore', cwd: tmp});
      const png = fs.readdirSync(tmp).find(f => f.startsWith(`t${i}_unpacked_rgba_RGBA32_level_0_`));
      if (!png) throw new Error(`basisu did not unpack texture ${i}`);
      texture.setImage(fs.readFileSync(path.join(tmp, png))).setMimeType('image/png').setURI(`t${i}.png`);
      unpacked++;
    }
  } finally { fs.rmSync(tmp, {recursive: true, force: true}); }
}
await doc.transform(dequantize());
for (const name of ['EXT_meshopt_compression', 'KHR_mesh_quantization', 'KHR_texture_basisu'])
  root.listExtensionsUsed().find(e => e.extensionName === name)?.dispose();
await io.write(output, doc);
console.log(JSON.stringify({input: path.basename(input), output, unpackedTextures: unpacked}));
