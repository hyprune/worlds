#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Write an object's object.json (RFC-0011) from measured values, flags and an optional base.

  tools/object/manifest.py OUT/object.json --measured MEASURED.json --id ID --name NAME
      [--base PARTIAL.json] [--category C] [--version V] [--format 0.9] [--scene object.gltf]
      [--license SPDX --author NAME [--source URL]] [--description TEXT] [--tags a,b]
      [--surface floor|wall|ceiling|any ... | --fixed] [--free-rotation] [--scale-range MIN,MAX]
      [--collision NODE] [--thumbnail thumbnail.png] [--character [--accent] [--radius R]]

MEASURED is `node tools/gltf/object.mjs measure SCENE`: the bounds always come from it,
and for --character the clips (walk and run speeds from extras.speed), the height and the
`sit` seat height, kept only when it lies in the 0.2-1 m range seats use. The base (for
example traits.decorative, slots or traits.machine an author wrote) is merged under the
flags: a flag wins over the base, measured values win over both. A base `companion` block
(object format 0.10, RFC-0010 companions amendment) is kept, and the idle variants it names
are listed among the character's clips when the glTF has them.
"""
import argparse, json, pathlib, sys

# RFC-0010 clips core knows; other clips stay in the glTF but are not listed.
CHARACTER_CLIPS = ['idle', 'walk', 'run', 'idle_fidget', 'turn_left', 'turn_right', 'look_around', 'wave', 'nod', 'sit', 'sit_idle', 'stand', 'talk']
SPEED_CLIPS = {'walk', 'run'}


def character_trait(measured, accent, radius, base, idles=()):
    clips = measured.get('clips') or {}
    missing = [c for c in ('walk', 'idle') if c not in clips]
    if missing:
        raise SystemExit(f'MANIFEST: the character has no {" or ".join(missing)} clip')
    trait = dict(base or {})
    listed = {}
    for name in CHARACTER_CLIPS + [i for i in idles if i not in CHARACTER_CLIPS]:
        if name not in clips:
            continue
        entry = {}
        if name in SPEED_CLIPS:
            if 'speed' not in clips[name]:
                raise SystemExit(f'MANIFEST: clip {name} has no extras.speed (run the import step)')
            entry['speed'] = clips[name]['speed']
        if name == 'sit' and 0.2 <= measured.get('seatHeight', -1) <= 1:
            entry['seatHeight'] = measured['seatHeight']
        listed[name] = entry
    trait['clips'] = listed
    trait['height'] = round(measured['height'], 2)
    if radius is not None:
        trait['radius'] = radius
    if accent:
        trait['accent'] = True
    return trait


def main():
    ap = argparse.ArgumentParser(description=__doc__.split('\n')[0])
    ap.add_argument('out'); ap.add_argument('--measured', required=True); ap.add_argument('--base')
    ap.add_argument('--id', required=True); ap.add_argument('--name', required=True)
    ap.add_argument('--category'); ap.add_argument('--version'); ap.add_argument('--format')
    ap.add_argument('--scene'); ap.add_argument('--license'); ap.add_argument('--author'); ap.add_argument('--source')
    ap.add_argument('--description'); ap.add_argument('--tags')
    ap.add_argument('--surface', action='append', choices=['floor', 'wall', 'ceiling', 'any'])
    ap.add_argument('--fixed', action='store_true', help='no movable trait: placed by worlds only')
    ap.add_argument('--free-rotation', action='store_true'); ap.add_argument('--scale-range')
    ap.add_argument('--collision'); ap.add_argument('--thumbnail')
    ap.add_argument('--character', action='store_true'); ap.add_argument('--accent', action='store_true')
    ap.add_argument('--radius', type=float)
    a = ap.parse_args()
    measured = json.loads(pathlib.Path(a.measured).read_text())
    doc = json.loads(pathlib.Path(a.base).read_text()) if a.base else {}
    traits = dict(doc.get('traits') or {})
    head = {'formatVersion': a.format or doc.get('formatVersion') or '0.9', 'id': a.id, 'version': a.version or doc.get('version') or '1.0.0',
            'name': a.name}
    description = a.description or doc.get('description')
    if description:
        head['description'] = description
    head['category'] = a.category or doc.get('category') or ('characters' if a.character else 'other')
    tags = a.tags.split(',') if a.tags else doc.get('tags')
    if tags:
        head['tags'] = tags
    head['scene'] = a.scene or doc.get('scene') or 'object.gltf'
    licence = a.license or doc.get('license')
    if not licence:
        raise SystemExit('MANIFEST: --license (an SPDX expression) is required')
    head['license'] = licence
    attribution = doc.get('attribution')
    if a.author:
        entry = {'path': '.', 'author': a.author, 'license': licence}
        if a.source:
            entry['source'] = a.source
        attribution = [entry] + [x for x in (attribution or []) if x.get('path') != '.']
    if not attribution:
        raise SystemExit('MANIFEST: --author (or a base attribution) is required')
    head['attribution'] = attribution
    if not measured.get('bounds'):
        raise SystemExit('MANIFEST: the scene has no drawn geometry')
    head['bounds'] = measured['bounds']
    thumbnail = a.thumbnail or doc.get('thumbnail')
    if thumbnail:
        head['thumbnail'] = thumbnail
    head['lighting'] = doc.get('lighting') or {'mode': 'probe'}
    if a.character:
        idles = (doc.get('companion') or {}).get('idles') or []
        missing = [i for i in idles if i not in (measured.get('clips') or {})]
        if missing:
            raise SystemExit(f'MANIFEST: companion idle variants not in the glTF: {", ".join(missing)}')
        traits['character'] = character_trait(measured, a.accent, a.radius, traits.get('character'), idles)
    else:
        if a.collision:
            traits['collidable'] = {'node': a.collision}
        if a.fixed:
            traits.pop('movable', None)
        elif a.surface or a.free_rotation or a.scale_range or 'movable' not in traits:
            movable = dict(traits.get('movable') or {})
            if a.surface:
                movable['surfaces'] = sorted(set(a.surface), key=['floor', 'wall', 'ceiling', 'any'].index)
            if a.free_rotation:
                movable['upright'] = False
            if a.scale_range:
                movable['scale'] = [float(v) for v in a.scale_range.split(',')]
            traits['movable'] = movable
    head['traits'] = traits
    if doc.get('companion') is not None:
        if not a.character:
            raise SystemExit('MANIFEST: a companion block needs --character')
        head['companion'] = doc['companion']
    if doc.get('slots'):
        head['slots'] = doc['slots']
    pathlib.Path(a.out).write_text(json.dumps(head, indent=1) + '\n')
    print('MANIFEST', a.out, ' '.join(sorted(traits)))


if __name__ == '__main__':
    main()
