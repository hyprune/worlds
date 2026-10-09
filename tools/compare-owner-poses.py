#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Before/after sheet at exact poses: owner live capture | nested before | nested after.

Images are unretouched; each is fitted (aspect preserved) into its cell. The
live column is the owner's own 4K capture of the published package in their
session (their graphics settings, HUD labels included). Both nested columns
come from the same private Intel nested harness at Medium, 0.5 render scale,
so they differ only by package.
"""
import argparse,json,textwrap
from pathlib import Path
from PIL import Image,ImageDraw,ImageFont,ImageOps
p=argparse.ArgumentParser(description=__doc__);p.add_argument('spec',type=Path);p.add_argument('--output',type=Path,required=True);a=p.parse_args()
spec=json.loads(a.spec.read_text());W,H,PAD,CAP=960,540,12,96
try:font=ImageFont.truetype('DejaVuSans.ttf',22);small=ImageFont.truetype('DejaVuSans.ttf',18);big=ImageFont.truetype('DejaVuSans-Bold.ttf',30)
except OSError:font=small=big=ImageFont.load_default()
cols=spec['columns'];rows=spec['rows'];top=110
sheet=Image.new('RGB',(PAD+len(cols)*(W+PAD),top+len(rows)*(H+CAP+PAD)),(12,18,24));d=ImageDraw.Draw(sheet)
d.text((PAD,14),spec['title'],font=big,fill='white');d.text((PAD,56),spec['subtitle'],font=small,fill=(190,200,210))
for c,label in enumerate(cols):d.text((PAD+c*(W+PAD)+6,84),label,font=font,fill=(245,186,112))
for r,row in enumerate(rows):
 y=top+r*(H+CAP+PAD)
 for c,path in enumerate(row['images']):
  x=PAD+c*(W+PAD);d.rectangle([x,y,x+W,y+H],fill=(28,36,44))
  if path and Path(path).exists():
   im=ImageOps.contain(Image.open(path).convert('RGB'),(W,H));sheet.paste(im,(x+(W-im.width)//2,y+(H-im.height)//2))
  else:d.text((x+20,y+H//2-12),'no live capture at this pose',font=font,fill=(140,150,160))
 d.text((PAD,y+H+6),row['id']+' - '+row['title'],font=font,fill='white')
 for i,line in enumerate(textwrap.wrap(row['caption'],width=250)[:3]):d.text((PAD,y+H+34+i*22),line,font=small,fill=(200,208,216))
a.output.parent.mkdir(parents=True,exist_ok=True);sheet.save(a.output,quality=90);print(a.output,sheet.size)
