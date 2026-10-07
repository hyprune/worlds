#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Proof every authored glyph and every signage string with the geometric font."""
import json,sys
from pathlib import Path
from PIL import Image,ImageDraw
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'switchyard'))
from lettering import GLYPHS
ART=ROOT/'artifacts/switchyard'
strings=json.loads((ART/'signage-strings.json').read_text())
assert all(len(rows)==7 and all(len(row)==5 and set(row)<={'0','1'} for row in rows) for rows in GLYPHS.values())
assert len({tuple(rows) for rows in GLYPHS.values()})==len(GLYPHS),'duplicate glyph shapes'
used=set(''.join(strings))-{' '};assert not used-set(GLYPHS),used-set(GLYPHS)
assert sum(a!=b for ra,rb in zip(GLYPHS['D'],GLYPHS['O']) for a,b in zip(ra,rb))>=8,'D must read distinctly from O'
rows=['ABCDEFGHIJKLMNOPQRSTUVWXYZ','0123456789 / -','D O 0 B 8 R P Q']+strings
image=Image.new('RGB',(1740,80+len(rows)*86),(12,24,31));draw=ImageDraw.Draw(image)
draw.text((22,18),'SWITCHYARD / original geometric alphabet / all exported signage',fill=(211,211,195))
for i,word in enumerate(rows):
 for j,ch in enumerate(word):
  if ch==' ':continue
  for y,row in enumerate(GLYPHS[ch]):
   for x,bit in enumerate(row):
    if bit=='1':draw.rectangle((22+(j*6+x)*8,60+i*86+y*8,22+(j*6+x)*8+6,60+i*86+y*8+5),fill=(237,223,181))
image.save(ART/'lettering-proof.png')
report={'status':'PASS','glyphCount':len(GLYPHS),'usedGlyphs':''.join(sorted(used)),'strings':strings,'DversusOChangedPixels':sum(a!=b for ra,rb in zip(GLYPHS['D'],GLYPHS['O']) for a,b in zip(ra,rb)),'proof':'artifacts/switchyard/lettering-proof.png'}
(ART/'lettering-report.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report,indent=2))
