#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""python3 tools/npc/test_provenance.py: the PROVENANCE rules."""
import pathlib, sys, tempfile
sys.path.insert(0, str(pathlib.Path(__file__).parent))
from provenance import check, OBJECT_REQUIRED
GOOD = '''Source: AI 3D tool, generated from the author's own concept
Author: Hyprune contributors
Licence: CC-BY-4.0
Animations: the tool's preset library
Resemblance check: original design, resembles no third-party character
'''
with tempfile.TemporaryDirectory() as d:
    src = pathlib.Path(d) / 'resident.glb'; src.write_bytes(b'')
    assert check(src)[1] == ['no PROVENANCE next to ' + str(src) + ' (PROVENANCE, PROVENANCE.md or resident.PROVENANCE.md)']
    (pathlib.Path(d) / 'PROVENANCE').write_text(GOOD); parsed, problems = check(src)
    assert not problems and parsed['licence'] == 'CC-BY-4.0', problems
    (pathlib.Path(d) / 'PROVENANCE').write_text(GOOD.replace('CC-BY-4.0', 'All rights reserved')); assert any('licence' in p for p in check(src)[1])
    (pathlib.Path(d) / 'PROVENANCE').write_text(GOOD.replace('Animations: the tool\'s preset library\n', '')); assert any('Animations' in p for p in check(src)[1])
    (pathlib.Path(d) / 'PROVENANCE').write_text(GOOD.replace('original design, resembles no third-party character', 'looks like a famous game hero')); assert check(src)[1]
    # Objects (tools/object-import): no animation or resemblance lines needed.
    (pathlib.Path(d) / 'PROVENANCE').write_text('Source: modelled by the author\nAuthor: Hyprune contributors\nLicence: CC0-1.0\n')
    assert check(src, OBJECT_REQUIRED)[1] == [] and check(src)[1]
print('PASS provenance rules')
