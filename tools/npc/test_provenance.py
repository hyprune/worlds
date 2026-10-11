#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""python3 tools/npc/test_provenance.py: the PROVENANCE rules."""
import pathlib, sys, tempfile
sys.path.insert(0, str(pathlib.Path(__file__).parent))
from provenance import check
GOOD = '''Source: Meshy Pro, generated from the owner's own concept
Author: Rick
Licence: CC-BY-4.0
Animations: Meshy preset library
Resemblance check: original design, resembles no third-party character
'''
with tempfile.TemporaryDirectory() as d:
    src = pathlib.Path(d) / 'resident.glb'; src.write_bytes(b'')
    assert check(src)[1] == ['no PROVENANCE next to ' + str(src) + ' (PROVENANCE, PROVENANCE.md or resident.PROVENANCE.md)']
    (pathlib.Path(d) / 'PROVENANCE').write_text(GOOD); parsed, problems = check(src)
    assert not problems and parsed['licence'] == 'CC-BY-4.0', problems
    (pathlib.Path(d) / 'PROVENANCE').write_text(GOOD.replace('CC-BY-4.0', 'All rights reserved')); assert any('licence' in p for p in check(src)[1])
    (pathlib.Path(d) / 'PROVENANCE').write_text(GOOD.replace('Animations: Meshy preset library\n', '')); assert any('Animations' in p for p in check(src)[1])
    (pathlib.Path(d) / 'PROVENANCE').write_text(GOOD.replace('original design, resembles no third-party character', 'looks like a famous game hero')); assert check(src)[1]
print('PASS provenance rules')
