#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Check the PROVENANCE note next to an NPC source (rule 4: original content with provenance).

    tools/npc/provenance.py SOURCE.glb|.fbx  ->  exit 0 and the parsed note, or exit 2 with what is missing

Looked up as PROVENANCE, PROVENANCE.md in the source's directory or <stem>.PROVENANCE.md.
Required lines (`Key: value`): Source (e.g. "Meshy Pro, generated from the owner's own
concept"), Author, Licence (CC-BY-4.0 or CC0-1.0), Animations (e.g. "Meshy preset library"
or "owner-made"), Resemblance check (a human statement that the character resembles no
third-party/game character). Public assets must not resemble third-party characters: the
tool can't judge that, so it requires the statement and prints it for review.
"""
import json, pathlib, re, sys

REQUIRED = ['Source', 'Author', 'Licence', 'Animations', 'Resemblance check']
LICENCES = ('CC-BY-4.0', 'CC0-1.0', 'CC0')

def find(src):
    src = pathlib.Path(src)
    for p in (src.parent / f'{src.stem}.PROVENANCE.md', src.parent / 'PROVENANCE.md', src.parent / 'PROVENANCE'):
        if p.exists():
            return p
    return None

def check(src):
    note = find(src)
    if not note:
        return None, [f'no PROVENANCE next to {src} (PROVENANCE, PROVENANCE.md or {pathlib.Path(src).stem}.PROVENANCE.md)']
    fields, problems = {}, []
    for line in note.read_text().splitlines():
        m = re.match(r'^\s*[-*]?\s*([A-Za-z ]+?)\s*:\s*(.+)$', line)
        if m:
            fields[m.group(1).strip().lower()] = m.group(2).strip()
    for key in REQUIRED:
        if not fields.get(key.lower()):
            problems.append(f'{note.name}: missing "{key}:"')
    licence = fields.get('licence', fields.get('license', ''))
    if licence and not any(l.lower() in licence.lower() for l in LICENCES):
        problems.append(f'{note.name}: licence "{licence}" is not CC-BY-4.0 or CC0')
    if 'resemblance check' in fields and re.search(r'\b(resembles|looks like|based on)\b(?!.*\bno\b)', fields['resemblance check'], re.I):
        problems.append(f'{note.name}: the resemblance check names a likeness; public assets must not resemble third-party characters')
    return {'note': str(note), **fields}, problems

if __name__ == '__main__':
    parsed, problems = check(sys.argv[1])
    if problems:
        for p in problems:
            print('PROVENANCE:', p, file=sys.stderr)
        sys.exit(2)
    print(json.dumps(parsed, indent=2))
