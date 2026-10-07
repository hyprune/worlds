#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Unretouched matching camera comparisons. Labels/scaling only, no grading."""
import json,subprocess
from pathlib import Path
from PIL import Image,ImageDraw,ImageFont
ROOT=Path(__file__).resolve().parents[1];ART=ROOT/'artifacts/switchyard'
views=json.loads((ROOT/'switchyard/views.json').read_text())['views']
font=ImageFont.truetype(subprocess.check_output(['fc-match','-f','%{file}','sans'],text=True),26)
contact=Image.new('RGB',(1920,len(views)*580),(11,19,26))
for i,v in enumerate(views):
 name=v['id'];pair=Image.new('RGB',(3840,1140),(11,19,26));d=ImageDraw.Draw(pair)
 for col,(prefix,title) in enumerate([('','BLENDER / CYCLES'),('engine-','CORE M1 / GLES3')]):
  im=Image.open(ART/(prefix+name+'.png')).convert('RGB');assert im.size==(1920,1080)
  pair.paste(im,(col*1920,60));d.text((col*1920+24,16),name+'   '+title+'   / identical pose, vertical FOV 60 degrees',font=font,fill=(233,219,184))
 pair.save(ART/('comparison-'+name+'.png'));contact.paste(pair.resize((1920,570),Image.Resampling.LANCZOS),(0,i*580))
contact.save(ART/'engine-blender-contact-sheet.png')
print(ART/'engine-blender-contact-sheet.png')
