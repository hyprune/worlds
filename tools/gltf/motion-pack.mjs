#!/usr/bin/env node
// SPDX-License-Identifier: MIT
// Build a motion pack (RFC-0010 amendment "Shared clip library"): clips from one or more
// rigged exports on one skeleton (mixamo-v1), as motion/<id>/ with motion.json (motionVersion
// 0.1) and one clips-only glTF per source rig (the skeleton and its animations, no mesh).
//
//   node tools/gltf/motion-pack.mjs SPEC.json OUT_DIR --rig <id>=<file.glb> [--rig ...]
//
// SPEC (kept beside the private sources: it names the source clips) lists the pack's id,
// name, skeleton, licence and attribution, and its clips: {rig, source, name, role, style?,
// loop?, trim? [start, end] seconds, hold? seconds}. Each clip is resampled at 30 fps; only the
// hips keep a translation; the root travel (the hips' straight-line horizontal drift over the
// clip) is removed, sway kept; the clip's speed (extras.speed, m/s) is, for walks and runs, the
// planted feet's backward speed, else the source's own or the removed travel: clips are
// in place, as core plays them. `hold` makes a still loop of the clip's last pose (a seated
// idle from the end of a sit-down). Public outputs carry only the spec's names.
import { NodeIO, Document } from '@gltf-transform/core';
import { ALL_EXTENSIONS } from '@gltf-transform/extensions';
import { MeshoptDecoder } from 'meshoptimizer';
import { mkdirSync, readFileSync, writeFileSync } from 'node:fs';
import { join } from 'node:path';

const FPS = 30;
const ROLES = ['idle', 'walk', 'run', 'sit-down', 'stand-up', 'seated-idle', 'wave', 'talk', 'guide', 'dance'];
const SLUG = /^[a-z0-9][a-z0-9-]*$/;
const [specPath, outDir, ...rest] = process.argv.slice(2);
if (!specPath || !outDir) {
  console.error('usage: motion-pack.mjs SPEC.json OUT_DIR --rig <id>=<file.glb> ...');
  process.exit(2);
}
const rigFiles = {};
for (let i = 0; i < rest.length; i++) {
  if (rest[i] !== '--rig') throw new Error(`unknown argument ${rest[i]}`);
  const [id, file] = rest[++i].split('=');
  rigFiles[id] = file;
}
const spec = JSON.parse(readFileSync(specPath, 'utf8'));
for (const key of ['id', 'name', 'skeleton', 'license', 'attribution', 'clips'])
  if (!(key in spec)) throw new Error(`spec: ${key} missing`);
if (!SLUG.test(spec.id) || !SLUG.test(spec.skeleton)) throw new Error('spec: id and skeleton are slugs');

// ---- small math (quaternions [x, y, z, w], column-major 4x4) ----
const qmul = (a, b) => [
  a[3] * b[0] + a[0] * b[3] + a[1] * b[2] - a[2] * b[1], a[3] * b[1] - a[0] * b[2] + a[1] * b[3] + a[2] * b[0],
  a[3] * b[2] + a[0] * b[1] - a[1] * b[0] + a[2] * b[3], a[3] * b[3] - a[0] * b[0] - a[1] * b[1] - a[2] * b[2]];
const qnorm = (q) => { const l = Math.hypot(...q) || 1; return q.map((v) => v / l); };
function slerp(a, b, u) {
  let d = a[0] * b[0] + a[1] * b[1] + a[2] * b[2] + a[3] * b[3];
  if (d < 0) { b = b.map((v) => -v); d = -d; }
  if (d > 0.9995) return qnorm(a.map((v, i) => v + (b[i] - v) * u));
  const th = Math.acos(d), s = Math.sin(th);
  const wa = Math.sin((1 - u) * th) / s, wb = Math.sin(u * th) / s;
  return a.map((v, i) => v * wa + b[i] * wb);
}
function trs(t, q, s) {
  const [x, y, z, w] = q;
  return [
    (1 - 2 * (y * y + z * z)) * s[0], 2 * (x * y + z * w) * s[0], 2 * (x * z - y * w) * s[0], 0,
    2 * (x * y - z * w) * s[1], (1 - 2 * (x * x + z * z)) * s[1], 2 * (y * z + x * w) * s[1], 0,
    2 * (x * z + y * w) * s[2], 2 * (y * z - x * w) * s[2], (1 - 2 * (x * x + y * y)) * s[2], 0,
    t[0], t[1], t[2], 1];
}
function mmul(a, b) {
  const c = new Array(16).fill(0);
  for (let j = 0; j < 4; j++) for (let i = 0; i < 4; i++) for (let k = 0; k < 4; k++) c[j * 4 + i] += a[k * 4 + i] * b[j * 4 + k];
  return c;
}
function inverseAffine(m) {
  const [a, d, g, , b, e, h, , c, f, i] = m;
  const det = a * (e * i - f * h) - b * (d * i - f * g) + c * (d * h - e * g), k = 1 / det;
  const r = [(e * i - f * h) * k, (f * g - d * i) * k, (d * h - e * g) * k, 0, (c * h - b * i) * k, (a * i - c * g) * k,
    (b * g - a * h) * k, 0, (b * f - c * e) * k, (c * d - a * f) * k, (a * e - b * d) * k, 0, 0, 0, 0, 1];
  for (let row = 0; row < 3; row++) r[12 + row] = -(r[row] * m[12] + r[4 + row] * m[13] + r[8 + row] * m[14]);
  return r;
}
const apply = (m, p) => [0, 1, 2].map((r) => m[r] * p[0] + m[4 + r] * p[1] + m[8 + r] * p[2] + m[12 + r]);

// Sample one glTF sampler at t (clamped): LINEAR (slerp for rotations), STEP, CUBICSPLINE (values).
function sampler(s, path) {
  const times = s.getInput().getArray(), out = s.getOutput().getArray(), mode = s.getInterpolation();
  const n = path === 'rotation' ? 4 : 3, cubic = mode === 'CUBICSPLINE';
  const value = (k) => Array.from(out.slice((cubic ? 3 * k + 1 : k) * n, (cubic ? 3 * k + 1 : k) * n + n));
  return (t) => {
    if (t <= times[0]) return value(0);
    if (t >= times[times.length - 1]) return value(times.length - 1);
    let lo = 0, hi = times.length - 1;
    while (hi - lo > 1) { const mid = (lo + hi) >> 1; if (times[mid] <= t) lo = mid; else hi = mid; }
    if (mode === 'STEP') return value(lo);
    const u = (t - times[lo]) / (times[hi] - times[lo]);
    const a = value(lo), b = value(hi);
    return path === 'rotation' ? qnorm(slerp(a, b, u)) : a.map((v, i) => v + (b[i] - v) * u);
  };
}
const key = (name) => name.slice(name.lastIndexOf(':') + 1).toLowerCase();

const io = new NodeIO().registerExtensions(ALL_EXTENSIONS).registerDependencies({ 'meshopt.decoder': MeshoptDecoder });
await MeshoptDecoder.ready;
mkdirSync(outDir, { recursive: true });
const manifest = { motionVersion: '0.1', id: spec.id, name: spec.name, skeleton: { id: spec.skeleton }, license: spec.license,
  attribution: spec.attribution, rigs: [], clips: [] };
const report = { pack: spec.id, rigs: {}, clips: [] };
const used = [...new Set(spec.clips.map((c) => c.rig))];
for (const rigId of used) {
  if (!rigFiles[rigId]) throw new Error(`no --rig ${rigId}=FILE`);
  const src = await io.read(rigFiles[rigId]);
  const root = src.getRoot(), skin = root.listSkins()[0];
  if (!skin) throw new Error(`${rigId}: no skin`);
  const joints = skin.listJoints(), jointSet = new Set(joints);
  const hips = joints.find((j) => key(j.getName()) === 'hips');
  if (!hips) throw new Error(`${rigId}: no hips`);
  // Rest world matrices of every node (parents of the skeleton included).
  const parentOf = new Map();
  for (const n of root.listNodes()) for (const c of n.listChildren()) parentOf.set(c, n);
  const world = (n) => (parentOf.has(n) ? mmul(world(parentOf.get(n)), n.getMatrix()) : n.getMatrix());
  const hipsParentWorld = parentOf.has(hips) ? world(parentOf.get(hips)) : trs([0, 0, 0], [0, 0, 0, 1], [1, 1, 1]);
  const hipsParentInverse = inverseAffine(hipsParentWorld);

  // The output rig: the skeleton (its ancestors as plain nodes) and the selected clips.
  const doc = new Document();
  const buffer = doc.createBuffer();
  const copies = new Map();
  const copy = (n) => {
    if (copies.has(n)) return copies.get(n);
    const c = doc.createNode(n.getName()).setTranslation(n.getTranslation()).setRotation(n.getRotation()).setScale(n.getScale());
    copies.set(n, c);
    const p = parentOf.get(n);
    if (p) copy(p).addChild(c);
    return c;
  };
  joints.forEach(copy);
  const top = [...copies.keys()].filter((n) => !parentOf.has(n)).map((n) => copies.get(n));
  doc.createScene('rig').addChild(top[0]);
  const ibm = skin.getInverseBindMatrices();
  const outSkin = doc.createSkin('rig');
  joints.forEach((j) => outSkin.addJoint(copies.get(j)));
  if (ibm) outSkin.setInverseBindMatrices(doc.createAccessor().setType('MAT4').setArray(new Float32Array(ibm.getArray())).setBuffer(buffer));
  outSkin.setSkeleton(copies.get(joints[0]));

  // Joint world positions for a frame (rotations from the clip, the hips from hipsLocal, other
  // translations and scales at rest), then the planted feet's backward speed, as core measures it
  // (world/Retarget.cpp plantedSpeed): a foot within 3 % of the hip height of its lowest point
  // over the clip is planted; the median of planted feet's backward (-Z) speeds.
  const feet = ['leftfoot', 'rightfoot'].map((k) => joints.find((j) => key(j.getName()) === k)).filter(Boolean);
  const restY = (n) => world(n)[13];
  const legOrRoot = (k) => k === 'root' || k.includes('foot') || k.includes('toe') || k.includes('leg');
  const hipHeight = restY(hips) - Math.min(restY(hips), ...joints.filter((j) => legOrRoot(key(j.getName()))).map(restY));
  function plantedSpeed(channels, hipsLocal, times, at) {
    if (feet.length < 2) return 0;
    const positions = Array.from(times, (_, k) => {
      const cache = new Map();
      const worldOf = (n) => {
        if (cache.has(n)) return cache.get(n);
        const s = channels.get(n);
        const t = n === hips && hipsLocal.length ? hipsLocal[k] : n.getTranslation();
        const local = trs(t, s?.rotation ? s.rotation(at(k)) : n.getRotation(), n.getScale());
        const m = parentOf.has(n) ? mmul(worldOf(parentOf.get(n)), local) : local;
        cache.set(n, m);
        return m;
      };
      return feet.map((f) => { const m = worldOf(f); return [m[12], m[13], m[14]]; });
    });
    const tolerance = 0.03 * Math.max(hipHeight, 0.1), speeds = [];
    for (let f = 0; f < 2; f++) {
      const low = Math.min(...positions.map((p) => p[f][1]));
      for (let k = 0; k + 1 < times.length; k++) {
        const p = positions[k][f], q = positions[k + 1][f];
        if (p[1] < low + tolerance && q[1] < low + tolerance) speeds.push(Math.max(0, -(q[2] - p[2]) / (times[k + 1] - times[k])));
      }
    }
    speeds.sort((x, y) => x - y);
    return speeds.length ? speeds[speeds.length >> 1] : 0;
  }
  const animations = new Map(root.listAnimations().map((a) => [a.getName(), a]));
  for (const clip of spec.clips.filter((c) => c.rig === rigId)) {
    if (!SLUG.test(clip.name) || !ROLES.includes(clip.role)) throw new Error(`clip ${clip.name}: slug name and a role`);
    const anim = animations.get(clip.source);
    if (!anim) throw new Error(`${rigId}: no animation for clip ${clip.name}`);
    const channels = new Map(); // joint -> {rotation?, translation?} samplers
    let end = 0;
    for (const ch of anim.listChannels()) {
      const n = ch.getTargetNode(), path = ch.getTargetPath();
      if (!jointSet.has(n) || (path !== 'rotation' && !(path === 'translation' && n === hips))) continue;
      const s = ch.getSampler();
      end = Math.max(end, s.getInput().getMax([])[0]);
      if (!channels.has(n)) channels.set(n, {});
      channels.get(n)[path] = sampler(s, path);
    }
    const [t0, t1] = clip.trim ?? [0, end];
    const hold = clip.hold ?? 0;
    const length = hold > 0 ? hold : t1 - t0;
    const frames = Math.max(2, Math.round(length * FPS) + 1);
    const times = Float32Array.from({ length: frames }, (_, k) => (k * length) / (frames - 1));
    const at = (k) => (hold > 0 ? t1 : t0 + times[k]);
    // Hips: world path, straight-line horizontal travel removed (the speed), back to local.
    let speed = 0;
    const hipsLocal = [];
    if (channels.get(hips)?.translation) {
      const pts = [...times].map((_, k) => apply(hipsParentWorld, channels.get(hips).translation(at(k))));
      const travel = [pts[frames - 1][0] - pts[0][0], 0, pts[frames - 1][2] - pts[0][2]];
      speed = hold > 0 ? 0 : Math.hypot(travel[0], travel[2]) / length;
      // A trimmed clip starts wherever the source had walked to: back over the rest position.
      const rest = apply(hipsParentWorld, hips.getTranslation());
      const start = clip.trim ? [pts[0][0] - rest[0], pts[0][2] - rest[2]] : [0, 0];
      pts.forEach((p, k) => {
        const u = k / (frames - 1);
        hipsLocal.push(apply(hipsParentInverse, [p[0] - start[0] - travel[0] * u, p[1], p[2] - start[1] - travel[2] * u]));
      });
    }
    // Speed: for walk and run the planted feet's backward speed (in place), so the feet don't
    // skate at the speed core moves the character; else (or unmeasurable) the source's own
    // (an in-place clip from npc-import carries extras.speed), else the removed travel.
    const own = anim.getExtras()?.speed;
    if (typeof own === 'number' && own > 0 && hold === 0) speed = own;
    const feetSpeed = clip.role === 'walk' || clip.role === 'run' ? plantedSpeed(channels, hipsLocal, times, at) : 0;
    if (feetSpeed > 0.05) speed = feetSpeed;
    const outAnim = doc.createAnimation(clip.name).setExtras({ speed: Math.round(speed * 1000) / 1000 });
    const input = doc.createAccessor().setType('SCALAR').setArray(times).setBuffer(buffer);
    for (const [n, s] of channels) {
      for (const path of ['rotation', 'translation']) {
        if (!s[path]) continue;
        const values = path === 'translation' ? hipsLocal.flat() : [...times].flatMap((_, k) => s.rotation(at(k)));
        const output = doc.createAccessor().setType(path === 'rotation' ? 'VEC4' : 'VEC3').setArray(Float32Array.from(values)).setBuffer(buffer);
        const smp = doc.createAnimationSampler().setInput(input).setOutput(output).setInterpolation('LINEAR');
        outAnim.addSampler(smp).addChannel(doc.createAnimationChannel().setTargetNode(copies.get(n)).setTargetPath(path).setSampler(smp));
      }
    }
    manifest.clips.push({ name: clip.name, role: clip.role, ...(clip.style ? { style: clip.style } : {}), rig: rigId,
      loop: clip.loop ?? true });
    report.clips.push({ name: clip.name, role: clip.role, style: clip.style ?? null, rig: rigId, seconds: Math.round(length * 1000) / 1000,
      speed: Math.round(speed * 1000) / 1000 });
  }
  await io.write(join(outDir, `${rigId}.glb`), doc);
  manifest.rigs.push({ id: rigId, scene: `${rigId}.glb` });
  report.rigs[rigId] = { joints: joints.length };
}
writeFileSync(join(outDir, 'motion.json'), JSON.stringify(manifest, null, 2) + '\n');
console.log(JSON.stringify(report));
