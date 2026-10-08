#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Review owner references beside unmodified matched Cycles/engine captures."""
import html,json
from pathlib import Path
from PIL import Image,ImageDraw,ImageOps
ROOT=Path(__file__).resolve().parents[1];ART=ROOT/'artifacts/lumen-reach'
views=json.loads((ART/'views.json').read_text())['views'];references=sorted((ROOT/'concept/release-world').glob('0[1-4]-*.png'))
rows=[]
for i,reference in enumerate(references):
 primary=next(v['id'] for v in views if v['id'].startswith(f'{i+1:02d}-') and v['id'].count('-')==2)
 sources=[reference,ART/(primary+'.png'),ART/('engine-'+primary+'.png')]
 out=Image.new('RGB',(1920,408),(12,19,25));d=ImageDraw.Draw(out)
 for column,(label,path) in enumerate(zip(['Owner composition reference','Cycles / AgX','Engine / ACES'],sources)):
  im=Image.open(path).convert('RGB');im=ImageOps.contain(im,(640,360));out.paste(im,(column*640+(640-im.width)//2,26+(360-im.height)//2));d.text((column*640+12,9),label,fill='white')
 out.save(ART/(primary+'-comparison.png'));rows.append((primary,sources))
body=['<!doctype html><meta charset="utf-8"><title>Lumen Reach render review</title><style>body{background:#0c1319;color:#ddd;font:16px sans-serif;margin:24px}img{width:100%}a{color:#f5ba70}</style><h1>Lumen Reach render review</h1><p>Thumbnails preserve aspect ratio. Raw linked captures have no grading or retouching. Cycles and engine share authored camera pose and 60 degree vertical FOV; owner artwork is a composition reference.</p>']
for primary,sources in rows:
 body+=['<h2>'+html.escape(primary)+'</h2>', '<img src="'+primary+'-comparison.png">', '<p>'+ ' · '.join('<a href="'+html.escape(str(p))+'">'+label+'</a>' for p,label in zip(sources,['Original owner artwork','Raw Cycles capture','Raw engine capture']))+'</p>']
(ART/'render-review.html').write_text('\n'.join(body)+'\n')
print(ART/'render-review.html')
