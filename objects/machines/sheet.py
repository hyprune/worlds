#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Compose a machine concept sheet from render.py's sheet views.

    python3 objects/machines/sheet.py VIEWS_DIR OUT.png [--thumbnail OBJECT_DIR]

Hero render, slot callout diagram (every slot and animated node with the
RFC-0013 target that drives it), the authored states side by side with the
input values that select them, and the machine's inputs and drives.
"""
import argparse, json, re
from collections import OrderedDict
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont

SANS = '/usr/share/fonts/noto/NotoSans-Regular.ttf'
SANS_B = '/usr/share/fonts/noto/NotoSans-Bold.ttf'
MONO = '/usr/share/fonts/TTF/JetBrainsMonoNLNerdFont-Regular.ttf'
BG, PANEL, INK, DIM = (16, 20, 24), (26, 31, 37), (232, 228, 216), (150, 156, 160)
KIND = {'states': (64, 200, 150), 'animation': (90, 170, 230), 'labels': (230, 220, 190), 'spawns': (255, 160, 70),
        'effects': (255, 120, 170), 'tracks': (255, 200, 80), 'stacks': (190, 150, 255), 'toggles': (140, 220, 240),
        'levels': (250, 240, 120)}


def font(path, size):
    try:
        return ImageFont.truetype(path, size)
    except OSError:
        return ImageFont.load_default()


def fit(img, w, h):
    im = img.copy(); im.thumbnail((w, h), Image.LANCZOS)
    return im


def group_callouts(points):
    """Group numbered siblings (stage-1-lamp .. stage-4-lamp) into one callout."""
    groups = OrderedDict()
    for p in points:
        key = re.sub(r'-\d+(-|$)', r'-#\1', p['target'])
        g = groups.setdefault((p['kind'], key), {'kind': p['kind'], 'target': key, 'pts': [], 'ids': []})
        g['pts'].append(p); g['ids'].append(p['target'])
    out = []
    for g in groups.values():
        if '#' in g['target']:
            nums = sorted({int(n) for t in g['ids'] for n in re.findall(r'-(\d+)(?:-|$)', t)})
            g['label'] = g['target'].replace('#', f'{{{nums[0]}..{nums[-1]}}}' if len(nums) > 1 else str(nums[0]))
        else:
            g['label'] = g['target']
        out.append(g)
    return out


def callout_panel(img, points, w, h):
    """Draw callouts onto the callout render: labels in left/right columns, leaders to the slots."""
    sx, sy = w / img.width, h / img.height
    im = img.resize((w, h), Image.LANCZOS).convert('RGBA')
    over = Image.new('RGBA', im.size, (0, 0, 0, 0)); d = ImageDraw.Draw(over)
    f = font(MONO, 21)
    groups = group_callouts(points)
    for g in groups:
        g['xy'] = [(p['xy'][0] * sx, p['xy'][1] * sy) for p in g['pts']]
        g['cy'] = sum(y for _, y in g['xy']) / len(g['xy']); g['cx'] = sum(x for x, _ in g['xy']) / len(g['xy'])
        g['paths'] = [[(q[0] * sx, q[1] * sy) for q in p['path']] for p in g['pts'] if 'path' in p]
    left = sorted([g for g in groups if g['cx'] < w / 2], key=lambda g: g['cy'])
    right = sorted([g for g in groups if g['cx'] >= w / 2], key=lambda g: g['cy'])
    for side, col in ((0, left), (1, right)):
        n = len(col)
        if not n:
            continue
        top, bottom = 60, h - 60
        slots = [top + (bottom - top) * (k + .5) / n for k in range(n)]
        # keep labels near their points when there is room
        ys = []
        for k, g in enumerate(col):
            y = min(max(g['cy'], slots[k] - 160), slots[k] + 160)
            if ys and y < ys[-1] + 34:
                y = ys[-1] + 34
            ys.append(y)
        overflow = ys[-1] - (h - 30) if ys else 0
        if overflow > 0:
            ys = [y - overflow for y in ys]
        for g, y in zip(col, ys):
            c = KIND.get(g['kind'], INK)
            tw = d.textlength(g['label'], font=f)
            x0 = 18 if side == 0 else w - 18 - tw - 22
            box = (x0, y - 15, x0 + tw + 22, y + 15)
            ax = box[2] if side == 0 else box[0]
            for path in g['paths']:
                d.line(path, fill=(*c, 230), width=4)
            for (px, py) in g['xy']:
                d.line([(ax, y), (px, py)], fill=(*c, 200), width=2)
                d.ellipse((px - 6, py - 6, px + 6, py + 6), outline=(*c, 255), width=3)
            d.rounded_rectangle(box, 7, fill=(12, 15, 18, 225), outline=(*c, 255), width=2)
            d.text((x0 + 11, y), g['label'], font=f, fill=(*c, 255), anchor='lm')
    return Image.alpha_composite(im, over).convert('RGB')


def main():
    ap = argparse.ArgumentParser(); ap.add_argument('views'); ap.add_argument('out'); ap.add_argument('--thumbnail')
    a = ap.parse_args()
    v = Path(a.views); s = json.loads((v / 'sheet.json').read_text()); m = s['manifest']; rep = s['report']
    W = 2560
    states = sorted(v.glob('state-*.png'), key=lambda p: int(p.stem.split('-')[1]))
    n = len(states)
    hero = Image.open(v / 'hero.png'); call = Image.open(v / 'callout.png')
    HEAD, ROW_A = 150, 900
    tile_w = (W - 40 - 16 * (n - 1)) // n
    t0 = Image.open(states[0]); tile_h = int(tile_w * t0.height / t0.width)
    ROW_B = tile_h + 100
    mach = m.get('traits', {}).get('machine', {})
    lines = []
    for i in mach.get('inputs', []):
        t = i['type'] + (f"[{', '.join(i['values'])}]" if 'values' in i else '') + \
            (f" {i['min']}-{i['max']}" if 'min' in i else '') + (f" x{i['repeat']}" if 'repeat' in i else '')
        mine = [dr['target'] for dr in mach.get('drives', []) if dr['input'].split('.')[0] == i['id']]
        targets = []
        for g in group_callouts([{'kind': '', 'target': t_} for t_ in mine]):
            targets.append(g['label'])
        targets = sorted(set(targets))
        targets += [f"(overrides {dr['input']}'s average)" for dr in mach.get('drives', [])
                    if dr.get('map', {}).get('average', {}).get('override') == i['id']]
        lines.append((f"{i['id']}: {t}", '→ ' + ', '.join(targets)))
    ROW_C = 70 + 34 * max(1, len(lines))
    H = HEAD + ROW_A + 30 + ROW_B + ROW_C + 40
    sheet = Image.new('RGB', (W, H), BG); d = ImageDraw.Draw(sheet)
    d.text((40, 18), f"{m['name']}", font=font(SANS_B, 54), fill=INK)
    d.text((40 + d.textlength(m['name'], font=font(SANS_B, 54)) + 28, 44), f"objects/machines/{m['id']}",
           font=font(MONO, 26), fill=DIM)
    d.text((40, 118), m['description'], font=font(SANS, 26), fill=(200, 196, 186), anchor='lm')
    b = m['bounds']; dims = [round(b['max'][k] - b['min'][k], 2) for k in range(3)]
    info = f"{rep['triangles']:,} triangles · proxy {rep['proxyTriangles']} · {dims[0]} × {dims[2]} m, {dims[1]} m tall · object format {m['formatVersion']} · {m['license']}"
    d.text((W - 40, 44), 'machine concept · RFC-0011 object, RFC-0013 machine', font=font(MONO, 22), fill=DIM, anchor='ra')
    d.text((W - 40, 80), info, font=font(MONO, 22), fill=DIM, anchor='ra')
    # Row A: hero | callouts
    y = HEAD
    hw = 1350
    sheet.paste(fit(hero, hw, ROW_A), (20, y))
    cw = W - hw - 60
    cp = callout_panel(call, s['callouts'], cw, int(cw * call.height / call.width))
    cp = cp.crop((0, 0, cw, min(cp.height, ROW_A - 50)))
    sheet.paste(cp, (hw + 40, y))
    fm = font(MONO, 22); leg_x = hw + 44
    for kind, c in KIND.items():
        d.ellipse((leg_x, y + cp.height + 18, leg_x + 16, y + cp.height + 34), outline=c, width=3)
        d.text((leg_x + 22, y + cp.height + 12), kind, font=fm, fill=c); leg_x += d.textlength(kind, font=fm) + 46
    d.rounded_rectangle((32, y + 12, 220, y + 52), 8, fill=(12, 15, 18)); d.text((46, y + 32), 'hero view', font=font(SANS_B, 22), fill=INK, anchor='lm')
    d.rounded_rectangle((hw + 52, y + 12, hw + 330, y + 52), 8, fill=(12, 15, 18)); d.text((hw + 66, y + 32), 'slots and targets', font=font(SANS_B, 22), fill=INK, anchor='lm')
    # Row B: states
    y = HEAD + ROW_A + 30
    d.text((40, y - 4), 'States (authored palettes, toggles, stacks; values a source would publish)', font=font(SANS_B, 26), fill=INK)
    y += 36
    for k, p in enumerate(states):
        x = 20 + k * (tile_w + 16)
        sheet.paste(fit(Image.open(p), tile_w, tile_h), (x, y))
        cap = s['states'][k] if k < len(s['states']) else ''
        fc = font(MONO, 21 if n <= 4 else 19); words = cap.split(' '); row = ''; ry = y + tile_h + 8
        for wd in words:
            if row and d.textlength(row + ' ' + wd, font=fc) > tile_w - 8:
                d.text((x + 4, ry), row, font=fc, fill=INK); ry += 28; row = wd
            else:
                row = (row + ' ' + wd).strip()
        d.text((x + 4, ry), row, font=fc, fill=INK)
    # Row C: inputs -> drives
    y += tile_h + 56
    d.text((40, y), 'Inputs and the drive targets they feed', font=font(SANS_B, 26), fill=INK)
    y += 42
    for k, (a_, b_) in enumerate(lines):
        d.text((40, y + k * 34), a_, font=fm, fill=(200, 230, 210))
        d.text((980, y + k * 34), b_, font=fm, fill=DIM)
    sheet.save(a.out, quality=92)
    if a.thumbnail:
        th = Image.open(v / 'thumb-512.png').convert('RGB').resize((256, 256), Image.LANCZOS)
        th.save(Path(a.thumbnail) / 'thumbnail.png', optimize=True)
    print(a.out, sheet.size)


main()
