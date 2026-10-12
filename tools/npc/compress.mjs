#!/usr/bin/env node
// SPDX-License-Identifier: MIT
// NPC character compression (bake host): as world format 0.7 packages, geometry is
// reordered, quantized and EXT_meshopt_compression encoded; textures become KTX2
// (KHR_texture_basisu, basisu flags per slot as tools/remote-optimize.sh: UASTC + zstd for
// colour and normal maps, ETC1S for metallic-roughness and occlusion). The walk/run speed the
// import step measured (report.speeds) is written as animation extras.speed.
//   node compress.mjs IN.glb OUT.glb --report REPORT.json [--basisu PATH]
import fs from 'node:fs';
import os from 'node:os';
import path from 'node:path';
import {execFileSync} from 'node:child_process';
import {NodeIO} from '@gltf-transform/core';
import {ALL_EXTENSIONS, EXTMeshoptCompression, KHRMeshQuantization, KHRTextureBasisu} from '@gltf-transform/extensions';
import {reorder, quantize} from '@gltf-transform/functions';
import {MeshoptDecoder, MeshoptEncoder} from 'meshoptimizer';

const args = process.argv.slice(2);
const flag = name => { const i = args.indexOf(name); if (i < 0) return null; const v = args[i + 1]; args.splice(i, 2); return v; };
const reportPath = flag('--report'), basisu = flag('--basisu');
const [input, output] = args;
await Promise.all([MeshoptDecoder.ready, MeshoptEncoder.ready]);
const io = new NodeIO().registerExtensions(ALL_EXTENSIONS).registerDependencies({'meshopt.decoder': MeshoptDecoder, 'meshopt.encoder': MeshoptEncoder});
const doc = await io.read(input);
const root = doc.getRoot();
const report = reportPath ? JSON.parse(fs.readFileSync(reportPath, 'utf8')) : {};
for (const anim of root.listAnimations()) {
  const speed = report.speeds?.[anim.getName()];
  if (speed) anim.setExtras({...anim.getExtras(), speed});
}
// Textures, with mips. Colour (base colour, emissive) and normal maps UASTC: ETC1S
// blocks band skin and cloth gradients (mean CIEDE2000 2.2-3.2 against the source vs
// 0.7). Data maps ETC1S, linear. Core transcodes either to the same GPU block format.
if (basisu) {
  const modes = new Map();
  const use = (tex, mode) => { if (tex) (modes.get(tex) || modes.set(tex, new Set()).get(tex)).add(mode); };
  for (const m of root.listMaterials()) {
    use(m.getBaseColorTexture(), 'srgb'); use(m.getEmissiveTexture(), 'srgb');
    use(m.getMetallicRoughnessTexture(), 'linear'); use(m.getOcclusionTexture(), 'linear'); use(m.getNormalTexture(), 'normal');
  }
  const flags = {srgb: ['-uastc', '-srgb'], normal: ['-uastc', '-linear', '-normal_map', '-mip_renorm'], linear: ['-q', '255', '-linear']};
  const tmp = fs.mkdtempSync(path.join(os.tmpdir(), 'npc-ktx2-'));
  for (const [i, tex] of root.listTextures().entries()) {
    if (tex.getMimeType() === 'image/ktx2') continue;
    const used = [...(modes.get(tex) || [])];
    if (used.length > 1) throw new Error(`texture ${i} is used as ${used.join(' and ')}: give each use its own image`);
    const src = path.join(tmp, `t${i}${tex.getMimeType() === 'image/jpeg' ? '.jpg' : '.png'}`), dst = path.join(tmp, `t${i}.ktx2`);
    fs.writeFileSync(src, tex.getImage());
    const mode = flags[used[0] || 'srgb'];
    execFileSync(basisu, ['-ktx2', '-mipmap', ...mode, '-file', src, '-output_file', dst], {stdio: 'ignore'});
    tex.setImage(fs.readFileSync(dst)).setMimeType('image/ktx2');
  }
  if (root.listTextures().length) doc.createExtension(KHRTextureBasisu).setRequired(true);
}
// One quantization volume for the whole character, so its meshes keep one shared skin.
await doc.transform(reorder({encoder: MeshoptEncoder}), quantize({quantizePosition: 16, quantizeTexcoord: 16, quantizeNormal: 10, quantizationVolume: 'scene'}));
doc.createExtension(EXTMeshoptCompression).setRequired(true).setEncoderOptions({method: EXTMeshoptCompression.EncoderMethod.QUANTIZE});
await io.write(output, doc);
const before = fs.statSync(input).size, after = fs.statSync(output).size;
console.log(JSON.stringify({input: path.basename(input), output: path.basename(output), bytes: [before, after],
  textures: root.listTextures().length, speeds: report.speeds || {}}));
