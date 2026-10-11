#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Owner composition beside matched, ungraded 0.5.0/0.6.0 engine views."""
import html
from pathlib import Path
from PIL import Image,ImageDraw,ImageOps
ROOT=Path(__file__).resolve().parents[1];ART=ROOT/'artifacts/lumen-reach-v3'
def concept_dir():
 """Private concept sheets: HYPRUNE_CONCEPT_DIR (environment or ~/.config/hyprune/dev.env)."""
 import sys;sys.path.insert(0,str(Path(__file__).resolve().parent));import devenv
 value=devenv.get('HYPRUNE_CONCEPT_DIR')
 if not value:sys.exit('Set HYPRUNE_CONCEPT_DIR (environment or ~/.config/hyprune/dev.env) to the private concept sheets; they are not in this repository.')
 return Path(value)
reference=concept_dir()/'03-frozen-bunker.png'
body=['<!doctype html><meta charset="utf-8"><title>Rime Vault v3 review</title><style>body{background:#101820;color:#eee;font:16px sans-serif;margin:24px}img{max-width:100%}a{color:#efbc80}</style><h1>Rime Vault — 0.5.0 to 0.6.0</h1><p>Owner artwork is a mood/composition reference. Both engine columns use identical poses, 60° FOV and 1080p output at Medium. Raw captures are ungraded; these thumbnails only resize and label.</p>']
for ident in ['03-rime-vault','03-rime-vault-tools','03-rime-vault-platform','03-rime-vault-services']:
 paths=[reference,ART/'before-engine'/('engine-'+ident+'.png'),ART/'after-engine'/('engine-'+ident+'.png')]
 labels=['Owner concept 03','Engine 0.5.0 / before','Engine 0.6.0 / after'];out=Image.new('RGB',(1920,400),(16,24,32));d=ImageDraw.Draw(out)
 for i,(path,label) in enumerate(zip(paths,labels)):
  im=ImageOps.contain(Image.open(path).convert('RGB'),(640,360));out.paste(im,(i*640+(640-im.width)//2,30+(360-im.height)//2));d.text((i*640+12,10),label,fill='white')
 out.save(ART/(ident+'-comparison.png'))
 body += ['<h2>'+html.escape(ident)+'</h2>','<img src="'+ident+'-comparison.png">','<p>'+' · '.join('<a href="'+html.escape(str(p))+'">'+label+'</a>' for p,label in zip(paths,labels))+'</p>']
(ART/'render-review.html').write_text('\n'.join(body)+'\n');print(ART/'render-review.html')
