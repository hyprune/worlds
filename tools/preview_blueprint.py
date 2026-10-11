# SPDX-License-Identifier: MIT
"""Dark blueprint preview of derived level SVGs (review only: rsvg-convert
renders a copy with a theme stylesheet; the package SVGs stay unstyled).
CSS beats presentation attributes in librsvg, so the stylesheet sets only
the colours a theme would add; `fill="none"` and widths come from the SVG."""
import shutil, subprocess, tempfile
from pathlib import Path
from PIL import Image

INK = '#0b1e33'


def stylesheet(frame):
    """Colours only, applied where the SVG has none (as the shell does):
    widths and fill="none" come from the SVG itself. Area outlines dashed."""
    dash = max(frame.viewbox[2], frame.viewbox[3]) / 1000
    return f"""
.grid{{stroke:#1d3a58}}
.floor{{fill:#173b5c;stroke:#3d6d98}}
.stair{{stroke:#9cc9ee}}
.void{{fill:#05101c}}
.wall{{stroke:#eef5fc}}
.opening{{stroke:#f3b24a}}
.screen{{stroke:#4fe3cf}}
.mount{{fill:#f3b24a;stroke:{INK}}}
.area{{stroke:#7fa6cc;stroke-dasharray:{6 * dash:.2f} {4 * dash:.2f}}}
.label{{fill:#dbe9f7}}
.route{{stroke:#ffcf5a}}
.waypoint{{fill:#ffcf5a;stroke:{INK}}}
.outline{{stroke:#a9c8e6}}
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
