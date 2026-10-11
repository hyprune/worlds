# SPDX-License-Identifier: MIT
"""Dark blueprint preview of derived level SVGs (review only: rsvg-convert
renders a copy with a theme stylesheet; the package SVGs stay unstyled).
The palette shows one reading of the class roles: floor/stair/void/mount/
waypoint filled, wall/opening/screen/area/route/grid/outline stroked only."""
import shutil, subprocess, tempfile
from pathlib import Path
from PIL import Image, ImageDraw

INK = '#0b1e33'


def stylesheet(frame):
    s = frame.scale                     # viewBox units per metre
    vb = min(frame.viewbox[2], frame.viewbox[3])
    px = vb / 1600                      # about one output pixel at 1600 px
    w = lambda metres, floor: max(metres * s, floor * px)
    return f"""
.grid{{fill:none;stroke:#1d3a58;stroke-width:{w(.04, .8):.3f}}}
.floor{{fill:#173b5c;stroke:#3d6d98;stroke-width:{w(.05, .9):.3f};stroke-linejoin:round}}
.stair{{fill:#22507a;fill-opacity:.85;stroke:#9cc9ee;stroke-width:{w(.04, .9):.3f};stroke-linecap:round}}
.void{{fill:#05101c}}
.wall{{fill:none;stroke:#eef5fc;stroke-width:{w(.12, 1.6):.3f};stroke-linejoin:round;stroke-linecap:round}}
.opening{{fill:none;stroke:#f3b24a;stroke-width:{w(.12, 1.8):.3f};stroke-linecap:round}}
.screen{{fill:none;stroke:#4fe3cf;stroke-width:{w(.35, 3.5):.3f};stroke-linecap:round}}
.mount{{fill:#f3b24a;stroke:{INK};stroke-width:{w(.05, .8):.3f}}}
.area{{fill:none;stroke:#7fa6cc;stroke-width:{w(.06, 1):.3f};stroke-dasharray:{w(.6, 6):.2f} {w(.4, 4):.2f}}}
.label{{fill:#dbe9f7}}
.route{{fill:none;stroke:#ffcf5a;stroke-width:{w(.18, 2):.3f};stroke-linejoin:round;stroke-linecap:round;stroke-opacity:.9}}
.waypoint{{fill:#ffcf5a;stroke:{INK};stroke-width:{w(.08, 1):.3f}}}
.outline{{fill:none;stroke:#a9c8e6;stroke-width:{w(.08, 1.4):.3f}}}
"""


def render_one(svg, frame, out, width=1600):
    if not shutil.which('rsvg-convert'):
        raise SystemExit('preview needs rsvg-convert (librsvg)')
    x0, y0, W, H = frame.viewbox
    head, rest = svg.split('>', 1)
    styled = f'{head}><style>{stylesheet(frame)}</style><rect x="{x0}" y="{y0}" width="{W}" height="{H}" fill="{INK}"/>{rest}'
    with tempfile.NamedTemporaryFile('w', suffix='.svg') as f:
        f.write(styled)
        f.flush()
        subprocess.run(['rsvg-convert', '-w', str(width), '-o', str(out), f.name], check=True)


def render(result, frame, out, world_name):
    """Per level when `out` contains {level}, else one side-by-side sheet."""
    out = Path(out)
    written = []
    if '{level}' in out.name:
        for lvl in result['levels']:
            target = out.with_name(out.name.replace('{level}', lvl['id']))
            target.parent.mkdir(parents=True, exist_ok=True)
            render_one(result['svgs'][lvl['id']], frame, target)
            written.append(str(target))
        return written
    with tempfile.TemporaryDirectory() as tmp:
        tiles = []
        for lvl in result['levels']:
            t = Path(tmp) / f'{lvl["id"]}.png'
            render_one(result['svgs'][lvl['id']], frame, t, width=900)
            tiles.append(Image.open(t).convert('RGB'))
        W = sum(t.width for t in tiles) + 16 * (len(tiles) + 1)
        H = max(t.height for t in tiles) + 32
        sheet = Image.new('RGB', (W, H), '#050d17')
        x = 16
        for t in tiles:
            sheet.paste(t, (x, 16))
            x += t.width + 16
        out.parent.mkdir(parents=True, exist_ok=True)
        sheet.save(out)
    return [str(out)]
