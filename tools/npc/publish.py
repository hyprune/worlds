#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Publish an imported NPC character (tools/npc-import output) under a public name.

  tools/npc/publish.py IMPORTED.glb IMPORT.report.json characters/NAME.glb

Rewrites only the glTF JSON chunk (the binary chunk is untouched): the armature node and
skin take NAME, a single material becomes `base`, and the asset records the licence and
attribution. Adds NAME's entry to characters/characters.json from the import report,
without the source file name or tool-specific step text."""
import hashlib, json, pathlib, struct, sys

src, report_path, out = map(pathlib.Path, sys.argv[1:4])
name = out.stem
data = src.read_bytes()
magic, version, _ = struct.unpack('<4sII', data[:12])
assert magic == b'glTF' and version == 2, 'not a GLB'
size, kind = struct.unpack('<I4s', data[12:20])
assert kind == b'JSON'
gltf = json.loads(data[20:20 + size])
rest = data[20 + size:]

for skin in gltf.get('skins', []):
    skin['name'] = name
    if 'skeleton' in skin:
        gltf['nodes'][skin['skeleton']]['name'] = name
for node in gltf['nodes']:  # the armature object: parent of `root`
    children = [gltf['nodes'][c].get('name') for c in node.get('children', [])]
    if 'root' in children and node.get('name') != 'root':
        node['name'] = name
if len(gltf.get('materials', [])) == 1:
    gltf['materials'][0]['name'] = 'base'
gltf['asset']['copyright'] = 'Hyprune contributors, CC-BY-4.0'
gltf['asset'].setdefault('extras', {}).update({
    'name': name, 'licence': 'CC-BY-4.0', 'author': 'Hyprune contributors',
    'source': 'https://github.com/hyprune/worlds/tree/main/characters'})

payload = json.dumps(gltf, separators=(',', ':')).encode()
payload += b' ' * (-len(payload) % 4)
body = struct.pack('<I4s', len(payload), b'JSON') + payload + rest
out.write_bytes(struct.pack('<4sII', b'glTF', 2, 12 + len(body)) + body)

report = json.loads(report_path.read_text())
manifest_path = out.parent / 'characters.json'
manifest = json.loads(manifest_path.read_text()) if manifest_path.exists() else {'characters': []}
entry = {
    'id': name, 'file': out.name, 'bytes': out.stat().st_size,
    'sha256': hashlib.sha256(out.read_bytes()).hexdigest(),
    'licence': 'CC-BY-4.0', 'author': 'Hyprune contributors',
    'heightMetres': report.get('height'), 'triangles': report.get('trianglesOut'), 'bones': report.get('bonesOut'),
    'walkSpeed': report.get('speeds', {}).get('walk'), 'runSpeed': report.get('speeds', {}).get('run'),
    'clips': sorted(set(report.get('clips', {}).values())),
    'clipsShared': bool(report.get('clipsFrom')),
}
if report.get('clipsFrom'):
    entry['hipHeightRatio'] = report['clipsFrom'].get('hipHeightRatio')
manifest['characters'] = sorted([c for c in manifest['characters'] if c['id'] != name] + [entry], key=lambda c: c['id'])
manifest_path.write_text(json.dumps(manifest, indent=2) + '\n')
print('published', out, entry['bytes'], 'bytes')
