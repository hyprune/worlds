#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Label the machines lineup render: names, heights and the 1.7 m figure.

    python3 objects/machines/lineup.py LINEUP_DIR OUT.png
"""
import json, sys
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont

SANS_B = '/usr/share/fonts/noto/NotoSans-Bold.ttf'
MONO = '/usr/share/fonts/TTF/JetBrainsMonoNLNerdFont-Regular.ttf'
d_in, out = Path(sys.argv[1]), sys.argv[2]
im = Image.open(d_in / 'lineup.png').convert('RGB'); marks = json.loads((d_in / 'lineup.json').read_text())
CROP = int(im.height * .16)
im = im.crop((0, CROP, im.width, im.height)); W, H = im.size
sheet = Image.new('RGB', (W, H + 240), (16, 20, 24)); sheet.paste(im, (0, 110)); d = ImageDraw.Draw(sheet)
fb, fm = ImageFont.truetype(SANS_B, 52), ImageFont.truetype(MONO, 30)
d.text((40, 26), 'Starter machines, one scale', font=fb, fill=(232, 228, 216))
d.text((W - 40, 56), 'beside a 1.7 m figure · Eevee concept render of the object assets', font=fm, fill=(150, 156, 160), anchor='rm')
top, base = marks.pop('figure')
top, base = [top[0], top[1] - CROP], [base[0], base[1] - CROP]
x = top[0] - 50
d.line([(x, top[1] + 110), (x, base[1] + 110)], fill=(255, 200, 80), width=4)
for yy in (top[1], base[1]):
    d.line([(x - 14, yy + 110), (x + 14, yy + 110)], fill=(255, 200, 80), width=4)
d.text((x + 6, top[1] + 110 - 22), '1.7 m', font=fm, fill=(255, 200, 80), anchor='mb')
for mid, (t, b, name, bounds) in marks.items():
    h = bounds['max'][1] - bounds['min'][1]
    cx = b[0]
    d.text((cx, H + 140), name, font=ImageFont.truetype(SANS_B, 34), fill=(232, 228, 216), anchor='mm')
    fs = ImageFont.truetype(MONO, 26)
    d.text((cx, H + 180), f'{h:.2f} m tall', font=fs, fill=(150, 156, 160), anchor='mm')
    d.text((cx, H + 212), f'{bounds["max"][0] - bounds["min"][0]:.2f} m wide', font=fs, fill=(150, 156, 160), anchor='mm')
sheet.save(out, quality=92)
print(out, sheet.size)
