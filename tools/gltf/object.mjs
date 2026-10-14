#!/usr/bin/env node
// SPDX-License-Identifier: MIT
// Object directories (RFC-0011): measure a glTF and check a directory with the shared validator.
//   node object.mjs measure SCENE.gltf|.glb             measured values (JSON)
//   node object.mjs check DIR [--format 0.9] [--json]   tools/object-check
//   node object.mjs library DIR [--json]                a library directory (tools/library-pack)
// measure decodes the geometry (meshopt, quantisation) and reports what object.json
// can't state without it: exact rest-pose bounds (skinned meshes at their rest pose),
// drawn triangles, the largest texture, an estimate of GPU bytes and, for characters,
// clip speeds (extras.speed), the height and the seat height of the `sit` clip.
// check runs the schema repository's validate('object') (SCHEMA_DIR, default ../schema)
// on object.json with the glTF, the directory's files, the thumbnail size and these values.
import fs from 'node:fs';
import path from 'node:path';
import {pathToFileURL} from 'node:url';
import {NodeIO} from '@gltf-transform/core';
import {ALL_EXTENSIONS} from '@gltf-transform/extensions';
import {MeshoptDecoder} from 'meshoptimizer';

// Files that build or document an object but are not part of it (never packed into a library).
export const SOURCE_FILES = /^(build\.py|PROVENANCE(\.md)?|[^/]*\.PROVENANCE\.md|README\.md|[^/]*\.report\.json)$/;

const mul = (a, b) => Array.from({length: 16}, (_, i) => { const c = i >> 2, r = i & 3; return a[r] * b[c * 4] + a[4 + r] * b[c * 4 + 1] + a[8 + r] * b[c * 4 + 2] + a[12 + r] * b[c * 4 + 3]; });
const apply = (m, p) => [0, 1, 2].map(r => m[r] * p[0] + m[4 + r] * p[1] + m[8 + r] * p[2] + m[12 + r]);
const round = v => Math.round(v * 10000) / 10000;

// Image size from its header: PNG IHDR, JPEG SOF, KTX2.
export function imageSize(bytes, mime) {
  const b = Buffer.from(bytes);
  if (mime === 'image/png' || b.subarray(1, 4).toString() === 'PNG') return {width: b.readUInt32BE(16), height: b.readUInt32BE(20)};
  if (mime === 'image/ktx2' || b.subarray(1, 7).toString() === 'KTX 20') return {width: b.readUInt32LE(20), height: b.readUInt32LE(24)};
  for (let i = 2; i + 9 < b.length;) {
    if (b[i] !== 0xff) return null;
    const marker = b[i + 1], length = b.readUInt16BE(i + 2);
    if (marker >= 0xc0 && marker <= 0xcf && ![0xc4, 0xc8, 0xcc].includes(marker)) return {width: b.readUInt16BE(i + 7), height: b.readUInt16BE(i + 5)};
    i += 2 + length;
  }
  return null;
}

async function readDocument(scene) {
  await MeshoptDecoder.ready;
  const io = new NodeIO().registerExtensions(ALL_EXTENSIONS).registerDependencies({'meshopt.decoder': MeshoptDecoder});
  return io.read(scene);
}

// The final pose of an animation: every channel's last keyframe value.
function poseAt(animation, end = true) {
  for (const channel of animation.listChannels()) {
    const node = channel.getTargetNode(), sampler = channel.getSampler(), out = sampler.getOutput(), n = sampler.getInput().getCount();
    const path = channel.getTargetPath(), size = out.getElementSize(), cubic = sampler.getInterpolation() === 'CUBICSPLINE';
    if (!node || !['translation', 'rotation', 'scale'].includes(path)) continue;
    const index = (end ? n - 1 : 0) * (cubic ? 3 : 1) + (cubic ? 1 : 0), value = out.getElement(index, new Array(size));
    if (path === 'translation') node.setTranslation(value); else if (path === 'rotation') node.setRotation(value); else node.setScale(value);
  }
}

// Every drawn vertex in asset space at the current pose, with its dominant joint (skinned meshes).
function forEachVertex(doc, visit) {
  const scene = doc.getRoot().getDefaultScene() || doc.getRoot().listScenes()[0];
  const drawn = [];
  scene?.traverse(node => { if (node.getMesh()) drawn.push(node); });
  for (const node of drawn) {
    const skin = node.getSkin(), world = node.getWorldMatrix();
    const joints = skin?.listJoints() || [], ibm = skin?.getInverseBindMatrices();
    const skinMatrices = joints.map((joint, j) => mul(joint.getWorldMatrix(), ibm ? ibm.getElement(j, new Array(16)) : [1, 0, 0, 0, 0, 1, 0, 0, 0, 0, 1, 0, 0, 0, 0, 1]));
    for (const prim of node.getMesh().listPrimitives()) {
      const pos = prim.getAttribute('POSITION'), J = prim.getAttribute('JOINTS_0'), W = prim.getAttribute('WEIGHTS_0');
      if (!pos) continue;
      const p = [0, 0, 0], j = [0, 0, 0, 0], w = [0, 0, 0, 0];
      for (let i = 0; i < pos.getCount(); i++) {
        pos.getElement(i, p);
        if (skin && J && W) {
          J.getElement(i, j); W.getElement(i, w);
          const out = [0, 0, 0]; let top = 0;
          for (let k = 0; k < 4; k++) {
            if (!w[k]) continue;
            const q = apply(skinMatrices[j[k]], p);
            for (let a = 0; a < 3; a++) out[a] += w[k] * q[a];
            if (w[k] > w[top]) top = k;
          }
          visit(out, joints[j[top]]);
        } else visit(apply(world, p), null);
      }
    }
  }
}

function boundsOf(doc) {
  const min = [Infinity, Infinity, Infinity], max = [-Infinity, -Infinity, -Infinity];
  forEachVertex(doc, p => { for (let a = 0; a < 3; a++) { min[a] = Math.min(min[a], p[a]); max[a] = Math.max(max[a], p[a]); } });
  return min[0] === Infinity ? null : {min: min.map(round), max: max.map(round)};
}

export async function measure(scene) {
  const doc = await readDocument(scene), root = doc.getRoot();
  const sceneRoot = root.getDefaultScene() || root.listScenes()[0];
  let triangles = 0, gpuBytes = 0, maxTextureSize = 0;
  const accessors = new Set();
  sceneRoot?.traverse(node => {
    for (const prim of node.getMesh()?.listPrimitives() || []) {
      const indices = prim.getIndices(), count = (indices || prim.getAttribute('POSITION'))?.getCount() || 0, mode = prim.getMode();
      triangles += mode === 4 ? Math.floor(count / 3) : mode === 5 || mode === 6 ? Math.max(0, count - 2) : 0;
      for (const a of [indices, ...prim.listAttributes()]) if (a) accessors.add(a);
    }
  });
  for (const a of accessors) gpuBytes += a.getArray()?.byteLength || 0;
  for (const texture of root.listTextures()) {
    const size = imageSize(texture.getImage(), texture.getMimeType());
    if (!size) continue;
    maxTextureSize = Math.max(maxTextureSize, size.width, size.height);
    // Estimate: KTX2 transcodes to ~1 byte per pixel, PNG/JPEG upload as RGBA8; mips add a third.
    gpuBytes += Math.ceil(size.width * size.height * (texture.getMimeType() === 'image/ktx2' ? 1 : 4) * 4 / 3);
  }
  const result = {bounds: boundsOf(doc), triangles, maxTextureSize, gpuBytes};
  const animations = root.listAnimations();
  if (root.listSkins().length && animations.length) {
    result.clips = Object.fromEntries(animations.map(a => [a.getName(), {...(typeof a.getExtras().speed === 'number' ? {speed: a.getExtras().speed} : {})}]));
    result.height = result.bounds && result.bounds.max[1];
    const sit = animations.find(a => a.getName() === 'sit');
    if (sit) {
      // Seat height: the lowest thigh point above the root in the sit clip's final pose,
      // from the vertices along the middle of each thigh (hip and knee regions excluded).
      poseAt(sit);
      const rootNode = root.listNodes().find(n => n.getName() === 'root');
      const base = rootNode ? rootNode.getWorldMatrix()[13] : 0;
      const knee = new Map(root.listNodes().filter(n => /UpLeg$/.test(n.getName())).map(n => [n, n.listChildren()[0]]));
      let low = Infinity;
      forEachVertex(doc, (p, joint) => {
        if (!joint || !knee.get(joint)) return;
        const a = joint.getWorldMatrix().slice(12, 15), b = knee.get(joint).getWorldMatrix().slice(12, 15);
        const d = b.map((v, i) => v - a[i]), t = d.reduce((n, v, i) => n + v * (p[i] - a[i]), 0) / d.reduce((n, v) => n + v * v, 0);
        if (t >= 0.25 && t <= 0.75) low = Math.min(low, p[1]);
      });
      if (low < Infinity) result.seatHeight = round(low - base);
    }
  }
  return result;
}

// tools/object-check: the directory's files, glTF, thumbnail and measured values through the shared validator.
export async function check(dir, {format, schemaDir} = {}) {
  dir = path.resolve(dir);
  const {validate} = await import(pathToFileURL(path.resolve(schemaDir || process.env.SCHEMA_DIR || path.join(import.meta.dirname, '../../../schema'), 'lib/validate.mjs')));
  const files = [], ignored = [], problems = [];
  const walk = (d, depth) => {
    for (const entry of fs.readdirSync(d).sort()) {
      const full = path.join(d, entry), rel = path.relative(dir, full), st = fs.lstatSync(full);
      if (st.isSymbolicLink() || (!st.isFile() && !st.isDirectory())) { problems.push(`${rel}: links and devices are not allowed`); continue; }
      if (st.isDirectory()) { if (depth < 8) walk(full, depth + 1); else problems.push(`${rel}: too deep`); continue; }
      if (depth === 0 && SOURCE_FILES.test(entry)) { ignored.push(rel); continue; }
      if (/\.(js|mjs|cjs|py|sh|lua|so|wasm|html|exe)$/i.test(rel) || (st.mode & 0o111)) problems.push(`${rel}: executable content is not allowed`);
      files.push({path: rel, size: st.size});
    }
  };
  const st = fs.lstatSync(dir);
  if (st.isSymbolicLink() || !st.isDirectory()) return {object: path.basename(dir), status: 'FAIL', errors: [`${dir} is not a plain directory`], warnings: [], ignored: [], files: 0, bytes: 0};
  walk(dir, 0);
  const manifest = JSON.parse(fs.readFileSync(path.join(dir, 'object.json'), 'utf8'));
  const options = {directory: path.basename(dir), files};
  let measured;
  const scene = typeof manifest.scene === 'string' && !manifest.scene.includes('..') ? path.join(dir, manifest.scene) : null;
  if (scene && fs.existsSync(scene)) {
    const bytes = fs.readFileSync(scene);
    options.gltf = /\.glb$/i.test(scene) ? JSON.parse(bytes.subarray(20, 20 + bytes.readUInt32LE(12)).toString('utf8')) : JSON.parse(bytes.toString('utf8'));
    for (const ref of [...(options.gltf.buffers || []), ...(options.gltf.images || [])]) {
      if (ref.uri === undefined) continue;
      if (/^[a-z]+:|^\/|\\|%|(^|\/)\.\.?(\/|$)/i.test(ref.uri)) problems.push(`glTF URI ${ref.uri} is not a plain relative path`);
      else if (!files.some(f => f.path === path.posix.join(path.posix.dirname(manifest.scene), ref.uri))) problems.push(`glTF resource ${ref.uri} is missing`);
    }
    if (!problems.length) {
      measured = await measure(scene);
      options.measured = {bounds: measured.bounds, maxTextureSize: measured.maxTextureSize, gpuBytes: measured.gpuBytes};
    }
  }
  if (typeof manifest.thumbnail === 'string' && fs.existsSync(path.join(dir, manifest.thumbnail))) {
    const bytes = fs.readFileSync(path.join(dir, manifest.thumbnail)), size = imageSize(bytes, 'image/png');
    options.thumbnail = {...size, bytes: bytes.length};
  }
  const result = validate('object', manifest, undefined, format, options);
  // Character clips: what the import step measured must still hold.
  const character = manifest.traits?.character;
  if (character && measured?.seatHeight !== undefined && character.clips?.sit?.seatHeight !== undefined && Math.abs(character.clips.sit.seatHeight - measured.seatHeight) > 0.02)
    problems.push(`traits.character: sit seatHeight ${character.clips.sit.seatHeight} differs from the measured ${measured.seatHeight}`);
  if (character && measured?.height && Math.abs(character.height - measured.height) > 0.02) problems.push(`traits.character: height ${character.height} differs from the measured ${measured.height}`);
  const errors = [...problems, ...result.errors];
  return {object: manifest.id, formatVersion: manifest.formatVersion, status: errors.length ? 'FAIL' : 'PASS', errors, warnings: result.warnings || [], ignored, files: files.length,
    bytes: files.reduce((n, f) => n + f.size, 0), triangles: result.triangles ?? measured?.triangles, measured, paths: files.map(f => f.path)};
}

// A library directory (library.json, LICENSE, ATTRIBUTION.md, objects/<id>/, motion/<id>/):
// every object checked as above, then validate('library') with the objects' manifests and
// every file; each motion pack (shared clip library) passes validateMotion, sits in a
// directory named by its id and ships its rigs and nothing else.
export async function checkLibrary(dir, {schemaDir} = {}) {
  dir = path.resolve(dir);
  const {validate, validateMotion} = await import(pathToFileURL(path.resolve(schemaDir || process.env.SCHEMA_DIR || path.join(import.meta.dirname, '../../../schema'), 'lib/validate.mjs')));
  const manifest = JSON.parse(fs.readFileSync(path.join(dir, 'library.json'), 'utf8'));
  const objectsDir = path.join(dir, 'objects'), reports = [], objects = {}, files = [];
  for (const id of fs.existsSync(objectsDir) ? fs.readdirSync(objectsDir).sort() : []) {
    const report = await check(path.join(objectsDir, id), {schemaDir});
    reports.push(report);
    if (fs.existsSync(path.join(objectsDir, id, 'object.json'))) objects[id] = JSON.parse(fs.readFileSync(path.join(objectsDir, id, 'object.json'), 'utf8'));
  }
  const walk = d => { for (const e of fs.readdirSync(d).sort()) { const f = path.join(d, e), st = fs.lstatSync(f); if (st.isDirectory()) walk(f); else files.push({path: path.relative(dir, f), size: st.size}); } };
  walk(dir);
  const result = validate('library', manifest, undefined, undefined, {objects, files});
  const motionDir = path.join(dir, 'motion'), motion = [];
  for (const id of fs.existsSync(motionDir) ? fs.readdirSync(motionDir).sort() : []) {
    const packDir = path.join(motionDir, id), file = path.join(packDir, 'motion.json');
    if (!fs.existsSync(file)) { motion.push(`motion/${id}: no motion.json`); continue; }
    if (!validateMotion) { motion.push(`motion/${id}: this schema has no motion packs`); continue; }
    const pack = JSON.parse(fs.readFileSync(file, 'utf8')), r = validateMotion(pack);
    motion.push(...r.errors.map(e => `motion/${id}: ${e}`));
    if (pack.id !== id) motion.push(`motion/${id}: motion.json has id ${pack.id}`);
    const scenes = new Set((pack.rigs || []).map(rig => rig.scene));
    for (const scene of scenes) if (!fs.existsSync(path.join(packDir, scene))) motion.push(`motion/${id}: missing rig ${scene}`);
    for (const f of files.filter(f => f.path.startsWith(`motion/${id}/`)).map(f => f.path.slice(`motion/${id}/`.length)))
      if (f !== 'motion.json' && !scenes.has(f)) motion.push(`motion/${id}: ${f} is not part of the pack`);
  }
  const errors = [...result.errors, ...motion, ...reports.flatMap(r => r.errors.map(e => `objects/${r.object}: ${e}`)), ...reports.flatMap(r => r.ignored.map(i => `objects/${r.object}: source file ${i} must not ship`))];
  return {library: manifest.id, version: manifest.version, formatVersion: manifest.formatVersion, status: errors.length ? 'FAIL' : 'PASS', errors,
    files: files.length, bytes: files.reduce((n, f) => n + f.size, 0), objects: reports.map(r => ({id: r.object, formatVersion: r.formatVersion, status: r.status, triangles: r.triangles, bytes: r.bytes}))};
}

if (process.argv[1] && import.meta.url === pathToFileURL(path.resolve(process.argv[1])).href) {
  const args = process.argv.slice(2), flag = name => { const i = args.indexOf(name); return i < 0 ? undefined : args.splice(i, 2)[1]; };
  const json = args.includes('--json') ? (args.splice(args.indexOf('--json'), 1), true) : false;
  const format = flag('--format'), schemaDir = flag('--schema');
  const [verb, ...targets] = args;
  if (verb === 'measure' && targets.length === 1) console.log(JSON.stringify(await measure(targets[0]), null, 1));
  else if (verb === 'library' && targets.length === 1) {
    const report = await checkLibrary(targets[0], {schemaDir});
    console.log(json ? JSON.stringify(report, null, 1) : `${report.status} library ${report.library}@${report.version} (format ${report.formatVersion}, ${report.objects.length} objects, ${report.files} files, ${report.bytes} bytes)\n` + report.errors.map(e => `  error: ${e}`).join('\n'));
    process.exitCode = report.status === 'PASS' ? 0 : 1;
  }
  else if (verb === 'check' && targets.length) {
    let failed = false;
    for (const target of targets) {
      const report = await check(target, {format, schemaDir});
      failed ||= report.status !== 'PASS';
      if (json) console.log(JSON.stringify(report, null, 1));
      else {
        console.log(`${report.status} ${report.object} (format ${report.formatVersion}, ${report.files} files, ${report.bytes} bytes, ${report.triangles} triangles)`);
        for (const e of report.errors) console.log(`  error: ${e}`);
        for (const w of report.warnings) console.log(`  warning: ${w}`);
      }
    }
    process.exitCode = failed ? 1 : 0;
  } else { console.error('usage: object.mjs measure SCENE | check DIR... | library DIR  [--format F] [--schema DIR] [--json]'); process.exitCode = 2; }
}
