# SPDX-License-Identifier: MIT
"""`com.hyprune.blueprint` 0.1: derive per-level technical plans of a world
package and validate them (RFC-0004 amendment, IPC 0.20 `spatial.map.levels`).

derive-blueprint.py and check-blueprint.py are thin CLIs over this module.

Frame. Every level SVG uses the package map's frame: the overview SVG's
viewBox and the map's worldToMap (u = a*x + c*z + e, v = b*x + d*z + f,
normalised over the viewBox). `com.hyprune.map` 0.1 supplies it; a package
with only the legacy `com.hyprune.switchyard.map` 0.1 uses that profile's
documented 900 x 1000 transform u = (450 + 19x)/900, v = (200 - 18z)/1000.

Content (top-down XZ, one SVG per level band of feet heights):
- floor: the Recast navmesh (core walker slope, RFC-0004 capsule) of the
  islands a spawn or route node stands on, rasterised at 0.1 m, grown back
  by the agent radius, traced and simplified (Douglas-Peucker);
- stair: navmesh polygons steeper than STAIR_GRADIENT, grouped, outlined,
  hatched across the climb (tread lines every TREAD m) with an arrow up the
  slope; stair lanes of a `*.stairs` extension the navmesh did not show are
  drawn as hatched rectangles;
- wall: a plan cut. Near-vertical collision triangles are intersected with
  horizontal planes CUT m above each floor height of the level; segments
  within WALL_NEAR m of that floor are chained and simplified;
- opening: a gap in a wall line. Two tall (>= TALL m) wall segments on one
  line (directions within 14 deg, offset <= 0.35 m) whose facing ends are
  0.6..16 m apart (gaps over 2 m need >= 1 m of wall on both sides, so pillar
  rows don't count), the wall line continuing past both jambs (>= 85 % tall
  wall over max(3 m, 2 x the gap) each side, so furniture rows and pier
  lines don't count), with no tall wall in between and walkable floor at one
  height (within 0.5 m) in the gap and 0.5 m to both sides, mark a door or
  gap: a line across it plus jamb ticks. Openings beside a perpendicular
  wall, with jambs that are not collinear, or between floors at different
  heights (stair sides, ledges) are not found;
- screen: anchors with mount role mounted-workspace, or no mount (window
  anchors): a line along the anchor's width and a tick towards its facing;
- mount: tool-mount (circle) and data-object (diamond) anchors;
- area/label: each zone (or area) with floor on the level: its floor's
  bounding rectangle, and its name at the free floor spot nearest the
  area's floor centre where the text box clears walls, stairs, routes,
  marks, the title block and other labels (shrunk to 65 %, then allowed to
  cross routes, else omitted on that level);
- route/waypoint: walking-graph edges touching the band, named places;
- grid (10 m), outline (border, title block: world, level, height band,
  scale bar, north arrow placed in the emptiest corner).
Themed elements carry `class` and no fill/stroke.

Levels: flat floor heights of the navmesh are split greedily wherever floor
lies above other floor (> HEADROOM m apart, overlapping in plan by more than
OVERLAP_M2) until no band hides floor under floor (1..6 levels); --levels N
forces N bands, cutting at the most overlapping, then widest, height gaps.
Bands are contiguous: cuts sit mid-gap between floors, the lowest band
starts 1 m under the lowest floor, the highest ends HEIGHT+1 m over the
highest. Names: the band holding the default spawn is "Ground", others
"Level n" / "Lower n", plus the zone owning >= 60 % of the band's floor.
"""
import json, math, re, xml.etree.ElementTree as ET
from pathlib import Path
import numpy as np
from PIL import Image, ImageDraw

SVG_NS = 'http://www.w3.org/2000/svg'
CLASSES = 'grid floor wall stair opening screen mount area label route waypoint void outline'.split()
ELEMENTS = {'svg', 'g', 'rect', 'path', 'circle', 'ellipse', 'line', 'polyline', 'polygon', 'text', 'tspan'}
ATTRIBUTES = {'viewBox', 'width', 'height', 'x', 'y', 'x1', 'y1', 'x2', 'y2', 'rx', 'ry', 'cx', 'cy', 'r', 'd', 'points',
              'fill', 'stroke', 'stroke-width', 'stroke-linecap', 'stroke-linejoin', 'opacity', 'fill-opacity',
              'stroke-opacity', 'font-family', 'font-size', 'font-weight', 'text-anchor', 'transform'}
LEVEL_BYTES, TOTAL_BYTES, MAX_NODES, MAX_DEPTH, MAX_VALUE = 65536, 262144, 4096, 32, 8192
PATH_CHARS = 8000                  # split path data well under MAX_VALUE
ID = re.compile(r'[a-z][a-z0-9-]{0,31}')
SAFE_PATH = re.compile(r'(?!/)(?!.*(^|/)\.\.(/|$))[A-Za-z0-9_./-]+\.svg')
LEGACY_MAP = 'com.hyprune.switchyard.map'

CELL = .1                          # m, plan raster
RADIUS, HEIGHT = .3, 1.8           # RFC-0004 capsule (navmesh erosion, headroom)
PHYSICAL_SLOPE = math.degrees(math.acos(.65))  # core walker support limit
STAIR_GRADIENT = .2                # rise/run above which a navmesh polygon is a stair or ramp
TREAD = .35                        # m between hatch lines
CUT = .9                           # m above each floor: wall cut plane (catches guard rails)
TALL = 2.0                         # m above the floor: a wall rather than furniture (openings)
OPEN_MIN, OPEN_MAX = .6, 16.0      # m: opening widths looked for
DOOR, JAMB = 2.0, 1.0              # wider gaps need >= JAMB m of wall on both sides (not pillar rows)
WALL_NEAR = 1.5                    # m: cut segments kept near the floor they belong to
HEADROOM, OVERLAP_M2 = 2.0, 8.0    # level split: floor over floor
MIN_FLOOR_M2 = .3                  # smaller floor islands and holes are dropped


# ---------------------------------------------------------------- frame ----
class BlueprintError(ValueError):
    """A package that cannot get (or does not have) a valid blueprint."""


class Frame:
    """World XZ -> viewBox coordinates of the package map."""

    def __init__(self, viewbox, w2m, source):
        self.viewbox = tuple(float(v) for v in viewbox)
        self.w2m = tuple(float(v) for v in w2m)
        self.source = source
        a, b, c, d, e, f = self.w2m
        x0, y0, W, H = self.viewbox
        self.M = np.array([[a * W, c * W], [b * H, d * H]])
        self.t = np.array([x0 + e * W, y0 + f * H])
        self.scale = math.sqrt(abs(np.linalg.det(self.M)))      # viewBox units per metre

    def xy(self, xz):
        return np.asarray(xz, float).reshape(-1, 2) @ self.M.T + self.t

    def world(self, xy):
        return (np.asarray(xy, float).reshape(-1, 2) - self.t) @ np.linalg.inv(self.M).T

    def vector(self, dxz):
        return np.asarray(dxz, float) @ self.M.T


def svg_viewbox(text):
    root = ET.fromstring(text)
    vb = root.get('viewBox')
    if vb is None:
        raise BlueprintError('map SVG has no viewBox')
    v = [float(x) for x in re.split(r'[\s,]+', vb.strip())]
    if len(v) != 4 or v[2] <= 0 or v[3] <= 0:
        raise BlueprintError(f'bad map viewBox {vb!r}')
    return v


def map_frame(package, manifest):
    """The package map's frame, or raise ValueError when it has none."""
    ext = manifest.get('extensions', {})
    if 'com.hyprune.map' in ext:
        mp = ext['com.hyprune.map']
        if mp.get('version') != '0.1' or len(mp.get('worldToMap', [])) != 6:
            raise BlueprintError('com.hyprune.map must be version 0.1 with a 6-entry worldToMap')
        return Frame(svg_viewbox((Path(package) / mp['path']).read_text()), mp['worldToMap'], 'com.hyprune.map'), mp['path']
    if LEGACY_MAP in ext:
        mp = ext[LEGACY_MAP]
        # RFC-0004 "First-session optional Map profile": the documented transform.
        return Frame((0, 0, 900, 1000), (19 / 900, 0, 0, -18 / 1000, 450 / 900, 200 / 1000), LEGACY_MAP), mp['path']
    raise BlueprintError('the package has no map (com.hyprune.map 0.1): a blueprint needs its frame')


# --------------------------------------------------------------- raster ----
class Grid:
    """XZ raster at `cell` m: row = z, column = x."""

    def __init__(self, lo, hi, cell=CELL):
        span = np.maximum(np.asarray(hi, float) - lo, cell)
        self.cell = max(cell, math.sqrt(span[0] * span[1] / 6e6))
        self.x0, self.z0 = float(lo[0]), float(lo[1])
        self.W, self.H = int(span[0] / self.cell) + 2, int(span[1] / self.cell) + 2

    def empty(self):
        return np.zeros((self.H, self.W), bool)

    def fill(self, polys):
        img = Image.new('1', (self.W, self.H))
        draw = ImageDraw.Draw(img)
        for p in polys:
            q = (np.asarray(p, float) - [self.x0, self.z0]) / self.cell - .5
            if len(q) >= 3:
                draw.polygon([tuple(v) for v in q], fill=1, outline=1)
        return np.array(img, bool)

    def lines(self, segs, width=1):
        img = Image.new('1', (self.W, self.H))
        draw = ImageDraw.Draw(img)
        for a, b in segs:
            pa = (np.asarray(a) - [self.x0, self.z0]) / self.cell - .5
            pb = (np.asarray(b) - [self.x0, self.z0]) / self.cell - .5
            draw.line([tuple(pa), tuple(pb)], fill=1, width=width)
        return np.array(img, bool)

    def index(self, xz):
        q = np.floor((np.asarray(xz, float).reshape(-1, 2) - [self.x0, self.z0]) / self.cell).astype(int)
        return q[:, 1], q[:, 0]

    def sample(self, mask, xz):
        r, c = self.index(xz)
        ok = (r >= 0) & (r < self.H) & (c >= 0) & (c < self.W)
        out = np.zeros(len(r), bool)
        out[ok] = mask[r[ok], c[ok]]
        return out

    def corner(self, ij):
        """Raster corner (column, row) -> world XZ."""
        return np.asarray(ij, float) * self.cell + [self.x0, self.z0]


def dilate(mask, r):
    """Disk dilation by r cells (r small) or square for r > 6."""
    if r <= 0:
        return mask.copy()
    if r > 6:
        out = mask
        for axis in (0, 1):
            c = np.cumsum(np.pad(out, [(r + 1, r) if a == axis else (0, 0) for a in (0, 1)]).astype(np.int32), axis=axis)
            n = out.shape[axis]
            hi = np.take(c, np.arange(2 * r + 1, 2 * r + 1 + n), axis=axis)
            lo = np.take(c, np.arange(0, n), axis=axis)
            out = hi - lo > 0
        return out
    out = mask.copy()
    H, W = mask.shape
    for dy in range(-r, r + 1):
        for dx in range(-r, r + 1):
            if (dx or dy) and dx * dx + dy * dy <= r * r + r:
                out[max(dy, 0):H + min(dy, 0), max(dx, 0):W + min(dx, 0)] |= mask[max(-dy, 0):H + min(-dy, 0), max(-dx, 0):W + min(-dx, 0)]
    return out


def erode(mask, r):
    return ~dilate(~mask, r)


def trace(mask):
    """Boundary loops of a boolean raster as corner lists (column, row).
    Filled cells lie right of travel (y down): outer loops and holes wind
    oppositely, so an SVG nonzero fill keeps the holes. Diagonal-only
    contacts separate (turn left at saddles)."""
    m = np.pad(mask, 1)
    f = m[1:-1, 1:-1]
    H, W = mask.shape
    key = lambda i, j: i * (W + 1) + j
    out = {}
    for sel, (sj, si), (dj, di) in (
            (f & ~m[:-2, 1:-1], (0, 0), (1, 0)),     # top edge, east
            (f & ~m[1:-1, 2:], (1, 0), (0, 1)),      # right edge, south
            (f & ~m[2:, 1:-1], (1, 1), (-1, 0)),     # bottom edge, west
            (f & ~m[1:-1, :-2], (0, 1), (0, -1))):   # left edge, north
        ii, jj = np.nonzero(sel)
        for i, j in zip((ii + si).tolist(), (jj + sj).tolist()):
            out.setdefault(key(i, j), []).append((dj, di))
    loops = []
    while out:
        start = next(iter(out))
        i, j = divmod(start, W + 1)
        d = None
        pts = []
        while True:
            k = key(i, j)
            cands = out.get(k)
            if not cands:
                break
            if len(cands) == 1 or d is None:
                nd = cands[0]
            else:
                left = (d[1], -d[0])
                nd = left if left in cands else cands[0]
            cands.remove(nd)
            if not cands:
                del out[k]
            if nd != d:
                pts.append((j, i))
            d = nd
            j, i = j + nd[0], i + nd[1]
        if len(pts) >= 3:
            loops.append(np.array(pts, float))
    return loops


def area(p):
    p = np.asarray(p, float)
    return .5 * float(np.dot(p[:, 0], np.roll(p[:, 1], -1)) - np.dot(p[:, 1], np.roll(p[:, 0], -1)))


def simplify(p, tol, closed=False):
    """Douglas-Peucker; closed loops split at the point farthest from p[0]."""
    p = np.asarray(p, float)
    if len(p) < 3:
        return p
    if closed:
        far = int(np.argmax(((p - p[0]) ** 2).sum(1)))
        if far == 0:
            return p[:1]
        a = simplify(p[:far + 1], tol)
        b = simplify(np.vstack([p[far:], p[:1]]), tol)
        return np.vstack([a[:-1], b[:-1]])
    keep = np.zeros(len(p), bool)
    keep[0] = keep[-1] = True
    stack = [(0, len(p) - 1)]
    while stack:
        i, j = stack.pop()
        if j <= i + 1:
            continue
        a, b = p[i], p[j]
        d = b - a
        L = math.hypot(*d)
        q = p[i + 1:j] - a
        dist = np.abs(q[:, 0] * d[1] - q[:, 1] * d[0]) / L if L > 1e-12 else np.hypot(q[:, 0], q[:, 1])
        k = int(np.argmax(dist))
        if dist[k] > tol:
            keep[i + 1 + k] = True
            stack += [(i, i + 1 + k), (i + 1 + k, j)]
    return p[keep]


def chain(segs, q=.02):
    """Join segments sharing endpoints (quantised to q) into polylines."""
    nodes, adj, coords = {}, {}, {}
    edges = set()
    for a, b in segs:
        ka, kb = tuple(np.round(np.asarray(a) / q).astype(int)), tuple(np.round(np.asarray(b) / q).astype(int))
        if ka == kb or (ka, kb) in edges or (kb, ka) in edges:
            continue
        edges.add((ka, kb))
        coords.setdefault(ka, a)
        coords.setdefault(kb, b)
        adj.setdefault(ka, []).append(kb)
        adj.setdefault(kb, []).append(ka)
    used = set()
    lines = []

    def walk(k0, k1):
        line = [k0, k1]
        used.add(frozenset((k0, k1)))
        while len(adj[line[-1]]) == 2:
            nxt = [k for k in adj[line[-1]] if frozenset((line[-1], k)) not in used]
            if not nxt:
                break
            used.add(frozenset((line[-1], nxt[0])))
            line.append(nxt[0])
        return line
    for k in adj:
        if len(adj[k]) != 2:
            for n in adj[k]:
                if frozenset((k, n)) not in used:
                    lines.append(walk(k, n))
    for k in adj:
        for n in adj[k]:
            if frozenset((k, n)) not in used:
                lines.append(walk(k, n))
    return [np.array([coords[k] for k in line], float) for line in lines]


# ----------------------------------------------------------- svg output ----
def num(t):
    """Integer tenths -> shortest decimal text."""
    s = '-' if t < 0 else ''
    i, f = divmod(abs(int(t)), 10)
    return s + (str(i) if i or not f else '') + ('.' + str(f) if f else '')


def tenths(xy):
    return np.round(np.asarray(xy, float) * 10).astype(np.int64)


def joined(tokens):
    out = ''
    for t in tokens:
        out += t if (not out or t.startswith('-') or out[-1].isalpha()) else ' ' + t
    return out


def subpath(xy, closed):
    t = tenths(xy)
    keep = np.ones(len(t), bool)
    keep[1:] = np.any(t[1:] != t[:-1], axis=1)
    t = t[keep]
    if closed and len(t) > 1 and np.all(t[0] == t[-1]):
        t = t[:-1]
    if len(t) < (3 if closed else 2):
        return ''
    d = np.diff(t, axis=0)
    return 'M' + joined([num(t[0][0]), num(t[0][1])]) + 'l' + joined([num(v) for v in d.reshape(-1)]) + ('z' if closed else '')


def paths(cls, subpaths, extra=''):
    """`<path>` elements of one class, split under the attribute limit."""
    out, cur = [], ''
    for s in subpaths:
        if not s:
            continue
        if cur and len(cur) + len(s) > PATH_CHARS:
            out.append(f'<path class="{cls}"{extra} d="{cur}"/>')
            cur = ''
        cur += s
    if cur:
        out.append(f'<path class="{cls}"{extra} d="{cur}"/>')
    return out


def text_safe(s):
    return re.sub(r'[<>"]', '', s.replace('&', 'and')).strip()[:64]


# ------------------------------------------------------------ the world ----
def yaw_axes(q):
    x, y, z, w = q
    R = np.array([[1 - 2 * (y * y + z * z), 2 * (x * y - z * w), 2 * (x * z + y * w)],
                  [2 * (x * y + z * w), 1 - 2 * (x * x + z * z), 2 * (y * z - x * w)],
                  [2 * (x * z - y * w), 2 * (y * z + x * w), 1 - 2 * (x * x + y * y)]])
    return R[:, 0], R[:, 2]          # width axis, facing normal


def namespace(m, suffix):
    return next((v for k, v in m.get('extensions', {}).items() if k.endswith(suffix) and k != LEGACY_MAP), {})


def gradient(v):
    """Plane fit y = a x + b z + c of a polygon's vertices -> (a, b)."""
    A = np.column_stack([v[:, 0], v[:, 2], np.ones(len(v))])
    try:
        (a, b, _), *_ = np.linalg.lstsq(A, v[:, 1], rcond=None)
    except np.linalg.LinAlgError:
        return 0., 0.
    return float(a), float(b)


def pretty(ident):
    return ' '.join(w.capitalize() for w in re.split(r'[-_.]', ident) if w)


class World:
    """Navmesh, collision and manifest intent of one package."""

    def __init__(self, package, manifest, tri, nav, keep_islands):
        self.package, self.m, self.tri = Path(package), manifest, tri
        self.polys = []
        for q in nav['polys']:
            if q['island'] not in keep_islands or len(q['v']) < 3:
                continue
            v = q['v']
            a, b = gradient(v)
            self.polys.append(dict(v=v, y=float(v[:, 1].mean()), area=q['area'], grad=(a, b), slope=math.hypot(a, b)))
        if not self.polys:
            raise BlueprintError('no walkable navmesh floor around the spawns')
        allv = np.concatenate([p['v'] for p in self.polys])
        self.lo, self.hi = allv.min(0), allv.max(0)
        self.grid = Grid(self.lo[[0, 2]] - 4, self.hi[[0, 2]] + 4)
        self.spawns = {s['id']: np.array(s['pose']['position'], float) for s in manifest['spawns']}
        self.default = manifest.get('defaultSpawn', manifest['spawns'][0]['id'])
        routes = namespace(manifest, '.routes')
        self.nodes = {n['id']: n for n in routes.get('nodes', [])}
        self.edges = [(e['from'], e['to']) for e in routes.get('edges', []) if e['from'] in self.nodes and e['to'] in self.nodes]
        self.stair_lanes = namespace(manifest, '.stairs').get('paths', [])
        # Playable backstops: vertical collision reaching far below every floor.
        n = np.cross(self.tri[:, 1] - self.tri[:, 0], self.tri[:, 2] - self.tri[:, 0])
        L = np.linalg.norm(n, axis=1)
        ny = np.abs(n[:, 1]) / np.maximum(L, 1e-12)
        self.vertical = self.tri[(L > 1e-9) & (ny < .5) & (self.tri[:, :, 1].min(1) > self.lo[1] - 10)]

    def floor_below(self, xz, y):
        """Highest navmesh floor at XZ not above y (or None)."""
        best = None
        for p in self.polys:
            v = p['v']
            if p['y'] > y + .3 or best is not None and p['y'] <= best:
                continue
            if not (v[:, 0].min() <= xz[0] <= v[:, 0].max() and v[:, 2].min() <= xz[1] <= v[:, 2].max()):
                continue
            inside = False
            for k in range(len(v)):
                (x1, _, z1), (x2, _, z2) = v[k], v[k - 1]
                if (z1 > xz[1]) != (z2 > xz[1]) and xz[0] < (x2 - x1) * (xz[1] - z1) / (z2 - z1) + x1:
                    inside = not inside
            if inside:
                best = p['y']
        return best


# --------------------------------------------------------------- levels ----
def floor_heights(polys, tol=.5):
    """Clusters of flat floor heights: [(lo, hi, area)] sorted."""
    flat = sorted((p['y'], p['area']) for p in polys if p['slope'] < STAIR_GRADIENT)
    out = []
    for y, a in flat:
        if out and y - out[-1][1] <= tol:
            out[-1][1] = y
            out[-1][2] += a
        else:
            out.append([y, y, a])
    return [tuple(c) for c in out]


def detect_levels(world, count='auto'):
    """Bands [(minY, maxY)] covering every walkable height (see module doc)."""
    polys = world.polys
    clusters = [c for c in floor_heights(polys) if c[2] >= 1.0] or floor_heights(polys)
    coarse = Grid(world.lo[[0, 2]] - 1, world.hi[[0, 2]] + 1, cell=.5)
    masks = []
    for lo, hi, _ in clusters:
        masks.append(coarse.fill([p['v'][:, [0, 2]] for p in polys if p['slope'] < STAIR_GRADIENT and lo - .01 <= p['y'] <= hi + .01]))
    cell2 = coarse.cell ** 2

    def overlap(i, j):          # clusters i..j-1 in one band: floor over floor
        if j - i < 2:
            return 0.
        total = 0.
        for a in range(i, j):
            for b in range(a + 1, j):
                if clusters[b][0] - clusters[a][1] > HEADROOM:
                    total += float((masks[a] & masks[b]).sum()) * cell2
        return total

    bands = [(0, len(clusters))]       # cluster index ranges
    target = None if count == 'auto' else int(count)
    if target is not None and not 1 <= target <= 6:
        raise BlueprintError('--levels must be 1..6')
    if target is not None and target > len(clusters):
        raise BlueprintError(f'--levels {target}: only {len(clusters)} distinct floor heights')
    while len(bands) < (target or 6):
        best = None
        for bi, (i, j) in enumerate(bands):
            here = overlap(i, j)
            for k in range(i + 1, j):
                gain = here - overlap(i, k) - overlap(k, j)
                gap = clusters[k][0] - clusters[k - 1][1]
                score = (gain, gap)
                if best is None or score > best[0]:
                    best = (score, bi, k)
        if best is None:
            break
        (gain, _), bi, k = best
        if target is None and gain <= OVERLAP_M2:
            break
        i, j = bands[bi]
        bands[bi:bi + 1] = [(i, k), (k, j)]
    ys = [p['y'] for p in polys]
    cuts = [round((clusters[i - 1][1] + clusters[i][0]) / 2, 1) for i, _ in bands[1:]]
    edges = [math.floor((min(ys) - 1) * 10) / 10] + cuts + [math.ceil((max(ys) + HEIGHT + 1) * 10) / 10]
    return [(edges[k], edges[k + 1], clusters[i:j]) for k, (i, j) in enumerate(bands)]


def name_levels(world, bands):
    ground = next((k for k, (lo, hi, _) in enumerate(bands) if lo <= world.spawns[world.default][1] < hi), 0)
    zones = world.m.get('zones', [])
    out = []
    for k, (lo, hi, _) in enumerate(bands):
        if k == ground:
            ident, name = 'ground', 'Ground'
        elif k > ground:
            ident, name = f'level-{k - ground}', f'Level {k - ground}'
        else:
            ident, name = f'lower-{ground - k}', f'Lower {ground - k}'
        if len(bands) > 1:
            share = {}
            total = 0.
            for p in world.polys:
                if lo <= p['y'] < hi:
                    total += p['area']
                    c = p['v'].mean(0)
                    for z in zones:
                        if np.all(c >= np.array(z['bounds']['min']) - .5) and np.all(c <= np.array(z['bounds']['max']) + .5):
                            share[z['id']] = share.get(z['id'], 0) + p['area']
                            break
            top = max(share.items(), key=lambda kv: kv[1], default=None)
            if top and total and top[1] >= .6 * total:
                zname = next(z.get('name') or pretty(z['id']) for z in zones if z['id'] == top[0])
                name = f'{name} - {text_safe(zname)}'
        out.append(dict(id=ident, name=name[:64], minY=lo, maxY=hi))
    return out


# --------------------------------------------------------------- drawing ---
class Plan:
    """One level's drawing in viewBox units."""

    def __init__(self, world, frame, level, clusters, index, count, tol):
        self.w, self.f, self.level, self.clusters = world, frame, level, clusters
        self.index, self.count, self.tol = index, count, tol
        self.lo, self.hi = level['minY'], level['maxY']
        g = world.grid
        self.polys = [p for p in world.polys if self.lo <= p['y'] < self.hi]
        nav = g.fill([p['v'][:, [0, 2]] for p in self.polys])
        self.floor = dilate(nav, round(RADIUS / g.cell))
        self.floor = erode(dilate(self.floor, 1), 1)
        steep = [p for p in self.polys if p['slope'] >= STAIR_GRADIENT]
        self.steep = steep
        self.busy = g.empty()              # label keep-out
        # Feet height per cell (highest floor), grown like the floor.
        img = Image.new('F', (g.W, g.H), float('nan'))
        draw = ImageDraw.Draw(img)
        for p in sorted(self.polys, key=lambda p: p['y']):
            q = (p['v'][:, [0, 2]] - [g.x0, g.z0]) / g.cell - .5
            draw.polygon([tuple(v) for v in q], fill=p['y'], outline=p['y'])
        hgt = np.array(img)
        for _ in range(round(RADIUS / g.cell) + 1):
            grown = hgt.copy()
            for dr, dc in ((1, 0), (-1, 0), (0, 1), (0, -1)):
                shifted = np.roll(hgt, (dr, dc), axis=(0, 1))
                grown = np.where(np.isnan(grown), shifted, grown)
            hgt = grown
        self.height = hgt
        self.report = {'floorM2': round(float(nav.sum()) * g.cell ** 2, 1)}

    # Each part returns a list of SVG element strings.
    def U(self, metres):
        return metres * self.f.scale

    def loops_xy(self, mask, min_m2, tol):
        g = self.w.grid
        out = []
        for loop in trace(mask):
            if abs(area(loop)) * g.cell ** 2 < min_m2:
                continue
            xy = self.f.xy(g.corner(loop))
            s = simplify(xy, tol, closed=True)
            if len(s) >= 3:
                out.append(s)
        return out

    def floors(self):
        loops = self.loops_xy(self.floor, MIN_FLOOR_M2, self.tol)
        return paths('floor', [subpath(p, True) for p in loops])

    def stairs(self):
        g = self.w.grid
        steep = self.steep
        # Group steep polygons sharing vertices (1 cm).
        parent = list(range(len(steep)))

        def find(i):
            while parent[i] != i:
                parent[i] = parent[parent[i]]
                i = parent[i]
            return i
        seen = {}
        for i, p in enumerate(steep):
            for v in np.round(p['v'] / .01).astype(int):
                k = tuple(v)
                if k in seen:
                    a, b = find(i), find(seen[k])
                    parent[max(a, b)] = min(a, b)
                else:
                    seen[k] = i
        groups = {}
        for i in range(len(steep)):
            groups.setdefault(find(i), []).append(steep[i])
        outlines, hatch, arrows = [], [], []
        regions = g.empty()
        for grp in groups.values():
            m2 = sum(p['area'] for p in grp)
            if m2 < 1.0:
                continue
            mask = dilate(g.fill([p['v'][:, [0, 2]] for p in grp]), round(RADIUS / g.cell)) & self.floor
            if not mask.any():
                continue
            regions |= mask
            gr = np.sum([np.array(p['grad']) * p['area'] for p in grp], axis=0) / m2
            up = gr / (np.linalg.norm(gr) or 1)
            outlines += self.loops_xy(mask, .5, max(self.tol, .12 * self.f.scale))
            hatch += self.hatch(mask, up)
            arrows += self.arrow(mask, up)
        for lane in self.w.stair_lanes:
            a, b = np.array(lane['from'], float), np.array(lane['to'], float)
            if max(a[1], b[1]) < self.lo or min(a[1], b[1]) >= self.hi:
                continue
            mid = ((a + b) / 2)[[0, 2]]
            if g.sample(regions, mid)[0]:
                continue
            d = (b - a)[[0, 2]]
            L = np.linalg.norm(d)
            if L < .5:
                continue
            u = d / L if b[1] >= a[1] else -d / L
            side = np.array([-d[1], d[0]]) / L * lane['width'] / 2
            rect = np.array([a[[0, 2]] - side, b[[0, 2]] - side, b[[0, 2]] + side, a[[0, 2]] + side])
            mask = g.fill([rect])
            regions |= mask
            outlines.append(self.f.xy(rect))
            hatch += self.hatch(mask, u)
            arrows += self.arrow(mask, u)
        self.busy |= regions
        self.report['stairs'] = len(outlines)
        return paths('stair', [subpath(p, True) for p in outlines] + [subpath(p, False) for p in hatch + arrows])

    def hatch(self, mask, up):
        """Tread lines across `up` every TREAD m, clipped to the mask."""
        g = self.w.grid
        r, c = np.nonzero(mask)
        pts = g.corner(np.column_stack([c + .5, r + .5]))
        side = np.array([-up[1], up[0]])
        s, t = pts @ up, pts @ side
        out = []
        step = g.cell / 2
        for k in np.arange(math.ceil(s.min() / TREAD) * TREAD, s.max(), TREAD):
            ts = np.arange(t.min() - g.cell, t.max() + g.cell, step)
            q = up * k + np.outer(ts, side)
            inside = g.sample(mask, q)
            if not inside.any():
                continue
            edges = np.flatnonzero(np.diff(np.r_[0, inside.astype(int), 0]))
            for a, b in zip(edges[::2], edges[1::2]):
                if (b - a) * step >= .3:
                    out.append(self.f.xy(np.array([q[a], q[b - 1]])))
        return out

    def arrow(self, mask, up):
        g = self.w.grid
        r, c = np.nonzero(mask)
        pts = g.corner(np.column_stack([c + .5, r + .5]))
        s = pts @ up
        mid = pts.mean(0)
        L = (s.max() - s.min()) * .7
        if L < 1:
            return []
        a, b = mid - up * L / 2, mid + up * L / 2
        side = np.array([-up[1], up[0]])
        head = min(.6, L / 4)
        return [self.f.xy(np.array([a, b])), self.f.xy(np.array([b - up * head + side * head * .6, b, b - up * head - side * head * .6]))]

    def wall_segments(self):
        """Plan-cut segments in world XZ, one list per cut plane:
        [[(a, b, tall)]], tall when the cut collision reaches TALL m above
        the floor (walls, not furniture)."""
        g = self.w.grid
        T = self.w.vertical
        groups = []
        ylo, yhi = T[:, :, 1].min(1), T[:, :, 1].max(1)
        for lo, hi, _ in self.clusters:
            near = dilate(g.fill([p['v'][:, [0, 2]] for p in self.polys if lo - .3 <= p['y'] <= hi + .3]), round(WALL_NEAR / g.cell))
            for h in sorted({round(lo + CUT, 2), round(hi + CUT, 2)}):
                sel = (ylo < h) & (yhi > h)
                tri, top = T[sel], yhi[sel]
                if not len(tri):
                    continue
                d = tri[:, :, 1] - h
                pieces = []
                for i, j in ((0, 1), (1, 2), (2, 0)):
                    cross = (d[:, i] < 0) != (d[:, j] < 0)
                    t = np.where(cross, d[:, i] / np.where(cross, d[:, i] - d[:, j], 1), 0)
                    pieces.append((cross, tri[:, i] + (tri[:, j] - tri[:, i]) * t[:, None]))
                segs = []
                groups.append(segs)
                pts = [[] for _ in range(len(tri))]
                for cross, p in pieces:
                    for k in np.flatnonzero(cross):
                        pts[k].append(p[k][[0, 2]])
                for k, pk in enumerate(pts):
                    if len(pk) == 2 and np.hypot(*(pk[0] - pk[1])) > .01:
                        mid = (pk[0] + pk[1]) / 2
                        if g.sample(near, np.array([pk[0], mid, pk[1]])).any():
                            segs.append((pk[0], pk[1], top[k] >= h - CUT + TALL))
        return groups

    def walls(self):
        # Each cut plane is chained and straightened on its own (triangle
        # pieces split differently per height), then the planes' segments
        # are merged without duplicates and chained again.
        def lines_of(segs, tol):
            out = []
            for line in chain(segs):
                closed = len(line) > 3 and np.hypot(*(line[0] - line[-1])) < .03
                s = simplify(line, tol, closed=closed)
                if len(s) >= 2:
                    out.append((s, closed))
            return out
        merged = {}
        for group in self.wall_segments():
            for tall in (True, False):
                for line, closed in lines_of([(a, b) for a, b, t in group if t == tall], .02):
                    pts = np.vstack([line, line[:1]]) if closed else line
                    for a, b in zip(pts[:-1], pts[1:]):
                        ka, kb = tuple(np.round(a / .05).astype(int)), tuple(np.round(b / .05).astype(int))
                        if ka != kb:
                            key = min(ka, kb) + max(ka, kb)
                            merged[key] = (a, b, tall or merged.get(key, (0, 0, False))[2])
        self.wall_world = [(a, b) for a, b, _ in merged.values()]
        if self.wall_world:
            self.busy |= self.w.grid.lines(self.wall_world, width=5)
        self.tall_lines = lines_of([(a, b) for a, b, t in merged.values() if t], self.tol / self.f.scale)
        lines = [(simplify(self.f.xy(line), self.tol, closed=closed), closed) for line, closed in lines_of(self.wall_world, .02)]
        self.wall_lines = lines
        self.report['wallLines'] = len(lines)
        return paths('wall', [subpath(p, c) for p, c in lines])

    def openings(self):
        """Gaps between collinear wall pieces with floor through them."""
        g = self.w.grid
        f = self.f
        segs = []
        for w, closed in self.tall_lines:
            if closed:
                w = np.vstack([w, w[:1]])
            for a, b in zip(w[:-1], w[1:]):
                L = np.hypot(*(b - a))
                if L >= .3:
                    segs.append((a, b, (b - a) / L, L))
        if not segs:
            return []
        tall = [(w[k], w[k + 1]) for line, closed in self.tall_lines for w in [np.vstack([line, line[:1]]) if closed else line] for k in range(len(w) - 1)]
        wall_mask = g.lines(tall, width=2) if tall else g.empty()
        ends = {}
        for si, (a, b, u, L) in enumerate(segs):
            for end, out in ((a, -u), (b, u)):
                ends.setdefault(tuple(np.floor(end / OPEN_MAX).astype(int)), []).append((si, end, out, L))
        found = []
        for cell, items in ends.items():
            near = [it for dx in (-1, 0, 1) for dz in (-1, 0, 1) for it in ends.get((cell[0] + dx, cell[1] + dz), [])]
            for si, pa, ua, la in items:
                for sj, pb, ub, lb in near:
                    if sj <= si:
                        continue
                    gap = pb - pa
                    L = np.hypot(*gap)
                    if not OPEN_MIN <= L <= OPEN_MAX or (L > DOOR and min(la, lb) < JAMB):
                        continue
                    g1 = gap / L
                    if np.dot(ua, g1) < .97 or np.dot(ub, -g1) < .97:
                        continue
                    # Collinear: the far jamb lies on segment i's line.
                    if abs(ua[0] * gap[1] - ua[1] * gap[0]) > .35:
                        continue
                    ts = np.linspace(.25 / L, 1 - .25 / L, max(3, int(L / .1)))
                    line = pa + np.outer(ts, gap)
                    if g.sample(wall_mask, line).any():
                        continue
                    # Enclosure: the wall line carries on past both jambs
                    # (>= 85 % tall wall over max(3 m, 2 x the gap)), so
                    # free-standing furniture rows and pier lines don't count.
                    D = max(3., 2 * L)
                    ts = np.linspace(.15, D, max(4, int(D / .2)))
                    run = np.vstack([pa - np.outer(ts, g1), pb + np.outer(ts, g1)])
                    if g.sample(wall_mask, run).mean() < .85:
                        continue
                    mid = (pa + pb) / 2
                    n = np.array([-g1[1], g1[0]])
                    probes = np.array([mid, mid + n * .5, mid - n * .5])
                    if not g.sample(self.floor, probes).all():
                        continue
                    r, c = g.index(probes)
                    ok = (r >= 0) & (r < g.H) & (c >= 0) & (c < g.W)
                    hs = self.height[r[ok], c[ok]] if ok.all() else np.array([np.nan])
                    if np.isnan(hs).any() or np.ptp(hs) > .5:
                        continue        # a stair side or a ledge, not a passage
                    found.append((L, mid, pa, pb, n))
        # Shortest first; a jamb serves one opening, and openings on one
        # line may not overlap (box walls offer each gap on both faces).
        kept, jambs = [], []
        for L, mid, pa, pb, n in sorted(found, key=lambda r: r[0]):
            if any(min(np.hypot(*(pa - j)), np.hypot(*(pb - j))) < .5 for j in jambs):
                continue
            u = (pb - pa) / L
            clash = False
            for _, m2, qa, qb, _ in kept:
                if abs(np.dot(m2 - mid, n)) < .6:
                    lo, hi = sorted((np.dot(qa - pa, u), np.dot(qb - pa, u)))
                    if hi > .05 and lo < L - .05:
                        clash = True
                        break
            if clash:
                continue
            kept.append((L, mid, pa, pb, n))
            jambs += [pa, pb]
        found = [(mid, pa, pb, n) for _, mid, pa, pb, n in kept]
        out = []
        tick = .35
        for mid, pa, pb, n in found:
            out.append(f.xy(np.array([pa, pb])))
            out.append(f.xy(np.array([pa + n * tick, pa - n * tick])))
            out.append(f.xy(np.array([pb + n * tick, pb - n * tick])))
        self.report['openings'] = len(found)
        return paths('opening', [subpath(p, False) for p in out])

    def anchors(self):
        from world_contract import homes
        roles = {r['anchorId']: r['role'] for r in homes(self.w.m)[1]}
        screens, mounts, data = [], [], []
        nscreens = 0
        marks = []
        for an in self.w.m.get('anchors', []):
            role = roles.get(an['id'])
            if role is None and 'mount' in an:
                role = {'mounted-workspace': 'mounted-workspace', 'tool-mount': 'tool', 'data-object': 'data'}.get(an['mount'].get('role'))
            pos = np.array(an['pose']['position'], float)
            wax, nrm = yaw_axes(an['pose'].get('rotation', [0, 0, 0, 1]))
            size = an.get('size', [1, 1])
            hn = np.array([nrm[0], nrm[2]])
            front = pos[[0, 2]] + (hn / np.linalg.norm(hn) * 1.0 if np.linalg.norm(hn) > .3 else 0)
            y = self.w.floor_below(front, pos[1])
            if y is None:
                y = self.w.floor_below(pos[[0, 2]], pos[1])
            if y is None:
                y = pos[1] - size[1] / 2
            if not self.lo <= y < self.hi:
                continue
            marks.append((pos[[0, 2]] - wax[[0, 2]] * size[0] / 2 - [.3, .3], pos[[0, 2]] + wax[[0, 2]] * size[0] / 2 + [.3, .3]))
            if role in (None, 'mounted-workspace'):
                nscreens += 1
                if np.linalg.norm(hn) < .3:        # floor/ceiling screen: its footprint
                    hax = np.array([wax[0], wax[2]])
                    hax = hax / (np.linalg.norm(hax) or 1)
                    side = np.array([-hax[1], hax[0]]) * size[1] / 2
                    c = pos[[0, 2]]
                    w = hax * size[0] / 2
                    screens.append((self.f.xy(np.array([c - w - side, c + w - side, c + w + side, c - w + side])), True))
                    continue
                hn = hn / np.linalg.norm(hn)
                hax = np.array([-hn[1], hn[0]]) * size[0] / 2
                c = pos[[0, 2]]
                screens.append((self.f.xy(np.array([c - hax, c + hax])), False))
                tick = min(1.2, max(.5, size[0] * .12))
                screens.append((self.f.xy(np.array([c, c + hn * tick])), False))
            elif role == 'tool':
                mounts.append(self.f.xy(pos[[0, 2]])[0])
            else:
                data.append(self.f.xy(pos[[0, 2]])[0])
        self.report['screens'] = nscreens
        self.report['mounts'] = len(mounts) + len(data)
        if marks:
            self.busy |= self.w.grid.lines(marks, width=round(1.2 / self.w.grid.cell))
        out = paths('screen', [subpath(p, c) for p, c in screens])
        r = max(self.U(.35), 1.2)
        out += [f'<circle class="mount" cx="{num(t[0])}" cy="{num(t[1])}" r="{num(round(r * 10))}"/>' for t in tenths(mounts)] if mounts else []
        dia = [subpath(np.array([p + [0, -r], p + [r, 0], p + [0, r], p + [-r, 0]]), True) for p in data]
        out += paths('mount', dia)
        return out

    def area_parts(self):
        """Area outlines and labels: [(class, element)]."""
        g = self.w.grid
        m = self.w.m
        zones = [(z['id'], z.get('name') or pretty(z['id']), np.array(z['bounds']['min'], float), np.array(z['bounds']['max'], float))
                 for z in m.get('zones', [])]
        if not zones:
            for a in m.get('areas', []):
                vols = [v for v in a.get('playable', {}).get('volumes', []) if v.get('type') == 'box']
                if vols:
                    lo = np.min([v['min'] for v in vols], 0)
                    hi = np.max([v['max'] for v in vols], 0)
                    zones.append((a['id'], pretty(a.get('theme') or a['id']), lo, hi))
        if not zones and self.w.spawns:
            for sid, p in self.w.spawns.items():
                zones.append((sid, pretty(sid), p - [8, 2, 8], p + [8, 4, 8]))
        outlines, labels = [], []
        size = max(self.f.viewbox[2], self.f.viewbox[3]) * .02
        for zid, name, lo, hi in zones:
            if hi[1] < self.lo or lo[1] >= self.hi:
                continue
            r0, c0 = g.index(lo[[0, 2]])
            r1, c1 = g.index(hi[[0, 2]])
            r0, r1 = sorted((int(np.clip(r0[0], 0, g.H)), int(np.clip(r1[0], 0, g.H))))
            c0, c1 = sorted((int(np.clip(c0[0], 0, g.W)), int(np.clip(c1[0], 0, g.W))))
            sub = self.floor[r0:r1, c0:c1]
            if sub.sum() * g.cell ** 2 < 10:
                continue
            rr, cc = np.nonzero(sub)
            blo = g.corner([[cc.min() + c0, rr.min() + r0]]) [0] - .6
            bhi = g.corner([[cc.max() + c0 + 1, rr.max() + r0 + 1]])[0] + .6
            blo = np.maximum(blo, lo[[0, 2]])
            bhi = np.minimum(bhi, hi[[0, 2]])
            rect = np.array([blo, [bhi[0], blo[1]], bhi, [blo[0], bhi[1]]])
            outlines.append(self.f.xy(rect))
            # Label: the free floor spot nearest the area's floor centre
            # where the whole text box clears walls, stairs, routes, marks
            # and earlier labels; else the most open floor point.
            centre = np.array([cc.mean() + c0, rr.mean() + r0])
            spot, fs = None, size
            # Relax step by step: smaller text, then text may cross routes.
            for scale, keep_out in ((1, self.busy), (.8, self.busy), (.65, self.busy), (.8, self.hard), (.65, self.hard)):
                fs = size * scale
                spot = self.label_spot(name, fs, (r0, r1, c0, c1), centre, keep_out)
                if spot is not None:
                    break
            if spot is None:
                self.report.setdefault('labelsOmitted', []).append(name)
                continue
            xy = self.f.xy(g.corner([spot]))[0]
            self.reserve(xy, name, fs)
            t = tenths(xy)
            labels.append(f'<text class="label" x="{num(t[0])}" y="{num(t[1] + round(fs * 3.5))}" font-size="{num(round(fs * 10))}" '
                          f'font-family="sans-serif" text-anchor="middle">{text_safe(name)}</text>')
        self.report['areas'] = len(labels)
        return paths('area', [subpath(p, True) for p in outlines]), labels

    def text_box(self, name, fs):
        """Half extents (columns, rows) of a label's box on the world grid."""
        half_units = np.array([.3 * fs * len(name) + fs * .3, .65 * fs])
        half_m = np.abs(np.linalg.inv(self.f.M)) @ half_units
        return np.ceil(half_m / self.w.grid.cell).astype(int)

    def reserve(self, xy, name, fs):
        g = self.w.grid
        hc, hr = self.text_box(name, fs)
        r, c = g.index(self.f.world(xy))
        R0, R1 = np.clip([r[0] - hr, r[0] + hr + 1], 0, g.H)
        C0, C1 = np.clip([c[0] - hc, c[0] + hc + 1], 0, g.W)
        for keep_out in (self.busy, self.hard):
            keep_out[R0:R1, C0:C1] = True

    def label_spot(self, name, fs, window, centre, keep_out):
        """Box centre on the area's floor, box clear of `keep_out`."""
        g = self.w.grid
        r0, r1, c0, c1 = window
        hc, hr = self.text_box(name, fs)
        R0, R1, C0, C1 = max(r0 - hr, 0), min(r1 + hr, g.H), max(c0 - hc, 0), min(c1 + hc, g.W)
        free = ~keep_out[R0:R1, C0:C1]
        if free.shape[0] <= 2 * hr or free.shape[1] <= 2 * hc:
            return None
        S = np.pad(free.astype(np.int32).cumsum(0).cumsum(1), ((1, 0), (1, 0)))
        h, w = 2 * hr + 1, 2 * hc + 1
        full = S[h:, w:] - S[:-h, w:] - S[h:, :-w] + S[:-h, :-w] == h * w
        rr, cc = np.nonzero(full)
        rr, cc = rr + R0 + hr, cc + C0 + hc
        ok = (rr >= r0) & (rr < r1) & (cc >= c0) & (cc < c1)
        rr, cc = rr[ok], cc[ok]
        ok = self.floor[rr, cc]
        rr, cc = rr[ok], cc[ok]
        if not len(rr):
            return None
        k = int(np.argmin((cc - centre[0]) ** 2 + (rr - centre[1]) ** 2))
        return [cc[k] + .5, rr[k] + .5]

    def routes(self):
        w = self.w
        segs, places = [], []
        for a, b in w.edges:
            pa, pb = np.array(w.nodes[a]['position'], float), np.array(w.nodes[b]['position'], float)
            if max(pa[1], pb[1]) < self.lo or min(pa[1], pb[1]) >= self.hi:
                continue
            segs.append((pa[[0, 2]], pb[[0, 2]]))
        lumen_style = any('waypoint' in n for n in w.nodes.values())
        for nid, n in w.nodes.items():
            p = np.array(n['position'], float)
            if not self.lo <= p[1] < self.hi:
                continue
            if (n.get('waypoint', True) if lumen_style else not nid.startswith('junction-')):
                places.append(self.f.xy(p[[0, 2]])[0])
        if not w.nodes:
            places = [self.f.xy(p[[0, 2]])[0] for p in w.spawns.values() if self.lo <= p[1] < self.hi]
        lines = [self.f.xy(l) for l in chain(segs)]
        g = self.w.grid
        if segs:
            self.busy |= g.lines(segs, width=max(3, round(1.2 / g.cell)))
        for xy in places:
            c = self.f.world(xy)[0]
            disc = g.lines([(c - [.8, 0], c + [.8, 0])], width=round(1.6 / g.cell))
            self.busy |= disc
            self.hard |= disc
        r = max(self.U(.6), 2.0)
        out = paths('route', [subpath(simplify(l, self.tol), False) for l in lines])
        out += [f'<circle class="waypoint" cx="{num(t[0])}" cy="{num(t[1])}" r="{num(round(r * 10))}"/>' for t in tenths(places)] if places else []
        self.report['routeEdges'] = len(segs)
        self.report['waypoints'] = len(places)
        return out

    def grid_lines(self):
        x0, y0, W, H = self.f.viewbox
        corners = self.f.world(np.array([[x0, y0], [x0 + W, y0], [x0 + W, y0 + H], [x0, y0 + H]]))
        lo, hi = corners.min(0), corners.max(0)
        step = 10.0
        while (hi - lo).max() / step > 60:
            step *= 2
        sub = []
        for x in np.arange(math.ceil(lo[0] / step) * step, hi[0] + 1e-6, step):
            sub.append(subpath(self.f.xy(np.array([[x, lo[1]], [x, hi[1]]])), False))
        for z in np.arange(math.ceil(lo[1] / step) * step, hi[1] + 1e-6, step):
            sub.append(subpath(self.f.xy(np.array([[lo[0], z], [hi[0], z]])), False))
        self.grid_step = step
        return paths('grid', sub)

    def title(self, world_name):
        """Border plus title block in the emptiest corner."""
        x0, y0, W, H = self.f.viewbox
        g = self.w.grid
        inset = min(W, H) * .015
        bw, bh = W * .40, H * .12
        bw = max(bw, min(W, H) * .38)
        bh = max(bh, bw * .30)
        best = None
        for cx, cy in ((x0 + W - inset - bw, y0 + H - inset - bh), (x0 + inset, y0 + H - inset - bh),
                       (x0 + W - inset - bw, y0 + inset), (x0 + inset, y0 + inset)):
            box = self.f.world(np.array([[cx, cy], [cx + bw, cy + bh]]))
            lo, hi = box.min(0), box.max(0)
            xs = np.linspace(lo[0], hi[0], 24)
            zs = np.linspace(lo[1], hi[1], 12)
            pts = np.array([[x, z] for x in xs for z in zs])
            cover = g.sample(self.floor, pts).mean()
            if best is None or cover < best[0] - 1e-9:
                best = (cover, cx, cy)
        _, bx, by = best
        r, c = g.index(self.f.world(np.array([[bx, by], [bx + bw, by + bh]])))
        R0, R1 = np.clip([min(r), max(r) + 1], 0, g.H)
        C0, C1 = np.clip([min(c), max(c) + 1], 0, g.W)
        for keep_out in (self.busy, self.hard):
            keep_out[R0:R1, C0:C1] = True
        T = lambda v: num(round(v * 10))
        out = [f'<rect class="outline" x="{T(x0 + inset)}" y="{T(y0 + inset)}" width="{T(W - 2 * inset)}" height="{T(H - 2 * inset)}"/>',
               f'<rect class="outline" x="{T(bx)}" y="{T(by)}" width="{T(bw)}" height="{T(bh)}"/>']
        pad = bh * .1
        big, small = bh * .2, bh * .12
        lvl = self.level
        out.append(f'<text class="label" x="{T(bx + pad)}" y="{T(by + pad + big)}" font-size="{T(big)}" font-family="sans-serif" font-weight="bold">{text_safe(world_name.upper())}</text>')
        sub_title = getattr(self, 'title_note', None) or f'{text_safe(lvl["name"])} ({self.index + 1}/{self.count})'
        out.append(f'<text class="label" x="{T(bx + pad)}" y="{T(by + pad + big + small * 1.5)}" font-size="{T(small)}" font-family="sans-serif">'
                   f'{sub_title}</text>')
        out.append(f'<text class="label" x="{T(bx + pad)}" y="{T(by + pad + big + small * 2.9)}" font-size="{T(small * .85)}" font-family="sans-serif">'
                   f'FEET {lvl["minY"]:g} TO {lvl["maxY"]:g} M / GRID {self.grid_step:g} M</text>')
        # Scale bar: a round length near a quarter of the block.
        target = bw * .45 / self.f.scale
        bar = max([v for v in (1, 2, 5, 10, 20, 25, 50, 100, 200, 500) if v <= target] or [1])
        L = bar * self.f.scale
        sx, sy = bx + pad, by + bh - pad
        tk = small * .5
        sub = [subpath(np.array([[sx, sy - tk], [sx, sy], [sx + L, sy], [sx + L, sy - tk]]), False),
               subpath(np.array([[sx + L / 2, sy], [sx + L / 2, sy - tk * .6]]), False)]
        # North arrow: world -Z in this frame.
        nv = self.f.vector([0, -1])
        nv = nv / np.linalg.norm(nv)
        rad = bh * .22
        nc = np.array([bx + bw - bh * .32, by + bh * .5]) - nv * small * .6
        side = np.array([-nv[1], nv[0]])
        tip, tail = nc + nv * rad, nc - nv * rad
        sub.append(subpath(np.array([tip, tail + side * rad * .55, nc - nv * rad * .45, tail - side * rad * .55]), True))
        out += paths('outline', sub)
        lab = nc + nv * (rad + small * .75) + np.array([0, small * .35])
        out.append(f'<text class="label" x="{T(lab[0])}" y="{T(lab[1])}" font-size="{T(small)}" font-family="sans-serif" text-anchor="middle">N</text>')
        out.append(f'<text class="label" x="{T(sx + L + small * .4)}" y="{T(sy)}" font-size="{T(small * .85)}" font-family="sans-serif">{bar:g} M</text>')
        return out

    def svg(self, world_name):
        x0, y0, W, H = self.f.viewbox
        body = self.grid_lines()
        floors = self.floors()
        stairs = self.stairs()
        walls = self.walls()
        openings = self.openings()
        anchors = self.anchors()
        self.hard = self.busy.copy()       # keep-out without routes
        routes = self.routes()
        title = self.title(world_name)
        areas, labels = self.area_parts()
        body += floors + stairs + areas + walls + openings + anchors + routes + labels + title
        vb = ' '.join(f'{v:g}' for v in self.f.viewbox)
        return f'<svg xmlns="{SVG_NS}" viewBox="{vb}">\n' + '\n'.join(body) + '\n</svg>\n'


# ------------------------------------------------------------- derive ------
def load_world(package, create_map=False):
    """(World, Frame, created) of a package, building its navmesh. Without a
    package map, create_map=True derives a com.hyprune.map frame
    (created=True); otherwise that is an error."""
    import gltf_io, navmesh_io
    navmesh_io.require_helper()
    scene = gltf_io.load(package)
    m = scene.manifest
    try:
        frame, _ = map_frame(package, m)
    except BlueprintError:
        ext = m.get('extensions', {})
        if 'com.hyprune.map' in ext or LEGACY_MAP in ext or not create_map:
            raise BlueprintError('the package has no usable map (com.hyprune.map 0.1); '
                                 '--create-map derives one from the navmesh') from None
        frame = None
    tri = navmesh_io.collision_triangles(scene)
    pts = [{'id': 's:' + s['id'], 'p': s['pose']['position'], 'h': [.15, .6, .15]} for s in m['spawns']]
    pts += [{'id': 'n:' + n['id'], 'p': n['position'], 'h': [.15, .6, .15]} for n in namespace(m, '.routes').get('nodes', [])]
    nav = navmesh_io.build(tri, PHYSICAL_SLOPE, points=pts)
    keep = {q['hit']['island'] for q in nav['points'] if q['hit']}
    world = World(package, m, tri, nav, keep)
    if frame is None:
        return world, new_frame(world), True
    return world, frame, False


MAP_WIDTH, MAP_MARGIN = 1000, 6.0    # created map: viewBox width, metres around the walkable extent


def new_frame(world):
    """A north-up com.hyprune.map frame over the walkable extent plus a margin
    (plus spawns and route nodes): viewBox 0 0 1000 H at one scale."""
    pts = [world.lo[[0, 2]], world.hi[[0, 2]]] + [p[[0, 2]] for p in world.spawns.values()]
    pts += [np.array(n['position'], float)[[0, 2]] for n in world.nodes.values()]
    lo, hi = np.min(pts, 0) - MAP_MARGIN, np.max(pts, 0) + MAP_MARGIN
    wx = hi[0] - lo[0]
    H = int(min(max(round(MAP_WIDTH * (hi[1] - lo[1]) / wx), 100), 4 * MAP_WIDTH))
    wz = wx * H / MAP_WIDTH
    cz = (lo[1] + hi[1]) / 2
    lo[1], hi[1] = cz - wz / 2, cz + wz / 2
    lo, hi = np.round(lo, 3), np.round(hi, 3)
    wx, wz = hi[0] - lo[0], hi[1] - lo[1]
    frame = Frame((0, 0, MAP_WIDTH, H), (1 / wx, 0, 0, 1 / wz, -lo[0] / wx, -lo[1] / wz), 'created')
    frame.bounds = [float(lo[0]), float(lo[1]), float(hi[0]), float(hi[1])]
    return frame


# Baked colours of the overview map.svg written with --create-map (the
# plain map SVG subset has no class): fill, stroke, stroke width in metres.
BAKED = {'grid': (None, '#1d3a58', .04), 'floor': ('#173b5c', '#3d6d98', .05), 'stair': ('#22507a', '#9cc9ee', .04),
         'void': ('#05101c', None, 0), 'wall': (None, '#eef5fc', .12), 'opening': (None, '#f3b24a', .12),
         'screen': (None, '#4fe3cf', .35), 'mount': ('#f3b24a', '#0b1e33', .05), 'area': (None, '#7fa6cc', .06),
         'label': ('#dbe9f7', None, 0), 'route': (None, '#ffcf5a', .18), 'waypoint': ('#ffcf5a', '#0b1e33', .08),
         'outline': (None, '#a9c8e6', .08)}
INK = '#0b1e33'


def bake(svg, frame):
    """Class-themed SVG -> plain map SVG with the blueprint palette."""
    floor_px = min(frame.viewbox[2], frame.viewbox[3]) / 1000

    def attrs(m):
        fill, stroke, width = BAKED[m.group(1)]
        out = f' fill="{fill or "none"}"'
        if stroke:
            out += f' stroke="{stroke}" stroke-width="{num(round(max(width * frame.scale, floor_px) * 10))}"'
            out += ' stroke-linecap="round" stroke-linejoin="round"'
        return out
    x0, y0, W, H = frame.viewbox
    head, rest = svg.split('>', 1)
    body = re.sub(r' class="([a-z]+)"', attrs, rest)
    return f'{head}>\n<rect x="{x0:g}" y="{y0:g}" width="{W:g}" height="{H:g}" fill="{INK}"/>{body}'


def derive(world, frame, levels='auto', budget=(LEVEL_BYTES, TOTAL_BYTES), create_map=False):
    """{'levels': [...extension levels], 'svgs': {id: text}, 'report': {...}}
    plus 'map' ({extension, svg}) when create_map (a created frame)."""
    bands = detect_levels(world, levels)
    named = name_levels(world, bands)
    for lvl in named:
        lvl['path'] = f'blueprint/{lvl["id"]}.svg'
    tol = max(.05 * frame.scale, .15)
    tries = []
    name = world.m.get('name', world.m['id'])
    while True:
        svgs, reports = {}, {}
        for k, (lvl, band) in enumerate(zip(named, bands)):
            plan = Plan(world, frame, lvl, band[2], k, len(named), tol)
            svgs[lvl['id']] = plan.svg(name)
            reports[lvl['id']] = plan.report | {'bytes': len(svgs[lvl['id']].encode()), 'floorHeights': [round(c[0], 2) for c in band[2]]}
        sizes = [len(s.encode()) for s in svgs.values()]
        overview = None
        if create_map:
            # The overview: every level flattened into one plan.
            whole = dict(id='overview', name='All levels', minY=named[0]['minY'], maxY=named[-1]['maxY'])
            plan = Plan(world, frame, whole, [c for b in bands for c in b[2]], 0, 1, tol)
            plan.title_note = 'ALL LEVELS'
            overview = bake(plan.svg(name), frame)
        tries.append({'toleranceUnits': round(tol, 3), 'bytes': sizes} | ({'mapBytes': len(overview.encode())} if overview else {}))
        if max(sizes) <= budget[0] and sum(sizes) <= budget[1] and (overview is None or len(overview.encode()) <= LEVEL_BYTES):
            break
        if tol > 1.0 * frame.scale:
            raise BlueprintError(f'blueprint over budget even at {tol / frame.scale:.2f} m simplification: {sizes} bytes '
                                 f'(limits {budget[0]} per level, {budget[1]} total)'
                                 + (f', map {len(overview.encode())} (limit {LEVEL_BYTES})' if overview else ''))
        tol *= 1.5
    result = {'levels': named, 'svgs': svgs,
              'report': {'frame': {'source': frame.source, 'viewBox': list(frame.viewbox), 'worldToMap': list(frame.w2m),
                                   'unitsPerMetre': round(frame.scale, 3)},
                         'simplification': tries, 'levels': [l | reports[l['id']] for l in named],
                         'totalBytes': sum(sizes)}}
    if overview is not None:
        result['map'] = {'extension': {'version': '0.1', 'path': 'map.svg', 'projection': 'xz', 'north': [0, 0, -1],
                                       'bounds': frame.bounds, 'worldToMap': list(frame.w2m)},
                         'svg': overview}
        result['report']['createdMap'] = result['map']['extension'] | {'bytes': len(overview.encode())}
    return result


def write_in_place(package, result):
    package = Path(package)
    out = package / 'blueprint'
    out.mkdir(exist_ok=True)
    keep = set()
    for lvl in result['levels']:
        (package / lvl['path']).write_text(result['svgs'][lvl['id']])
        keep.add((package / lvl['path']).name)
    for old in out.glob('*.svg'):
        if old.name not in keep:
            old.unlink()
    wj = package / 'world.json'
    m = json.loads(wj.read_text())
    ext = m.setdefault('extensions', {})
    if 'map' in result:
        (package / result['map']['extension']['path']).write_text(result['map']['svg'])
        ext['com.hyprune.map'] = result['map']['extension']
    ext['com.hyprune.blueprint'] = {
        'version': '0.1', 'levels': [{k: l[k] for k in ('id', 'name', 'minY', 'maxY', 'path')} for l in result['levels']]}
    wj.write_text(json.dumps(m, indent=2, ensure_ascii=False) + '\n')


# ------------------------------------------------------------- validate ----
def check_svg(text, viewbox=None, allow_class=True):
    """Errors of one level SVG against the blueprint subset (core's map SVG
    rules plus `class`)."""
    errors = []
    data = text.encode()
    if not data or len(data) > LEVEL_BYTES:
        errors.append(f'{len(data)} bytes (limit {LEVEL_BYTES})')
    if '<!' in text or '<?' in text:
        errors.append('declarations, comments or processing instructions are forbidden')
        return errors
    try:
        root = ET.fromstring(text)
    except ET.ParseError as e:
        return errors + [f'invalid XML: {e}']
    if root.tag != f'{{{SVG_NS}}}svg':
        errors.append('root must be <svg> in the SVG namespace')
    count = [0]
    bad_value = re.compile(r'url|href|://', re.I)

    def walk(el, depth):
        count[0] += 1
        if depth > MAX_DEPTH:
            errors.append('nesting deeper than 32')
            return
        tag = el.tag
        if not tag.startswith(f'{{{SVG_NS}}}') or tag.split('}', 1)[1] not in ELEMENTS:
            errors.append(f'element {tag} not allowed')
        for k, v in el.attrib.items():
            if k.startswith('{') or (k not in ATTRIBUTES and not (allow_class and k == 'class')):
                errors.append(f'attribute {k} not allowed')
            if len(v) > MAX_VALUE or any(ch in v for ch in '&<>') or bad_value.search(v):
                errors.append(f'unsafe value for {k} ({len(v)} chars)')
            if k == 'class' and v not in CLASSES:
                errors.append(f'class {v!r} not in the vocabulary')
        if el.text:
            count[0] += 1
        for child in el:
            walk(child, depth + 1)
            if child.tail:
                count[0] += 1
    walk(root, 0)
    if count[0] > MAX_NODES:
        errors.append(f'{count[0]} nodes (limit {MAX_NODES})')
    if viewbox is not None:
        try:
            vb = [float(x) for x in re.split(r'[\s,]+', root.get('viewBox', '').strip())]
        except ValueError:
            vb = None
        if vb is None or len(vb) != 4 or any(abs(a - b) > 1e-6 for a, b in zip(vb, viewbox)):
            errors.append(f'viewBox {root.get("viewBox")!r} differs from the map frame {list(viewbox)}')
    # Dedupe while keeping order.
    return list(dict.fromkeys(errors))


def check_package(package):
    """(errors, info) of a package's com.hyprune.blueprint extension."""
    package = Path(package)
    m = json.loads((package / 'world.json').read_text())
    ext = m.get('extensions', {})
    errors, info = [], {}
    bp = ext.get('com.hyprune.blueprint')
    if bp is None:
        return ['no com.hyprune.blueprint extension'], info
    if not isinstance(bp, dict) or set(bp) != {'version', 'levels'} or bp.get('version') != '0.1':
        errors.append('extension must be exactly {version: "0.1", levels}')
    levels = bp.get('levels') if isinstance(bp, dict) else None
    if not isinstance(levels, list) or not 1 <= len(levels) <= 6:
        return errors + ['levels must be an array of 1..6 entries'], info
    try:
        frame, _ = map_frame(package, m)
        info['frame'] = frame.source
        if frame.source == LEGACY_MAP:
            info['note'] = 'frame from the legacy com.hyprune.switchyard.map adapter (RFC-0004); no com.hyprune.map 0.1'
        else:
            mp = ext['com.hyprune.map']
            nums = lambda v, n: isinstance(v, list) and len(v) == n and all(isinstance(x, (int, float)) and not isinstance(x, bool) and math.isfinite(x) for x in v)
            if mp.get('projection') != 'xz' or mp.get('north') != [0, 0, -1] or not nums(mp.get('bounds'), 4) or not nums(mp.get('worldToMap'), 6):
                errors.append('com.hyprune.map 0.1 needs projection xz, north [0,0,-1], 4 bounds and 6 worldToMap numbers')
            mpath = mp.get('path', '')
            if not isinstance(mpath, str) or not SAFE_PATH.fullmatch(mpath):
                errors.append('com.hyprune.map path must be a package-relative safe .svg path')
            else:
                for e in check_svg((package / mpath).read_text(encoding='utf-8'), allow_class=False):
                    errors.append(f'{mpath} (map): {e}')
    except (BlueprintError, OSError, ET.ParseError, ValueError) as e:
        errors.append(str(e))
        frame = None
    ids, total, prev = set(), 0, None
    info['levels'] = []
    for k, lvl in enumerate(levels):
        where = f'levels[{k}]'
        if not isinstance(lvl, dict) or set(lvl) != {'id', 'name', 'minY', 'maxY', 'path'}:
            errors.append(f'{where}: must have exactly id, name, minY, maxY, path')
            continue
        if not isinstance(lvl['id'], str) or not ID.fullmatch(lvl['id']) or lvl['id'] in ids:
            errors.append(f'{where}: id must be a unique slug [a-z][a-z0-9-]{{0,31}}')
        ids.add(lvl['id'])
        if not isinstance(lvl['name'], str) or not 1 <= len(lvl['name']) <= 64:
            errors.append(f'{where}: name must be 1..64 characters')
        lo, hi = lvl['minY'], lvl['maxY']
        if not all(isinstance(v, (int, float)) and not isinstance(v, bool) and math.isfinite(v) for v in (lo, hi)) or not lo < hi:
            errors.append(f'{where}: minY < maxY (finite numbers) required')
            continue
        if prev is not None and (lo < prev[0] or lo < prev[1]):
            errors.append(f'{where}: levels must be sorted by minY and not overlap (maxY[i] <= minY[i+1])')
        prev = (lo, hi)
        path = lvl['path']
        if not isinstance(path, str) or len(path) > 200 or not SAFE_PATH.fullmatch(path):
            errors.append(f'{where}: path must be a package-relative safe .svg path')
            continue
        f = package / path
        if f.is_symlink() or not f.is_file() or package.resolve() not in f.resolve().parents:
            errors.append(f'{where}: {path} missing or not a regular file inside the package')
            continue
        text = f.read_text(encoding='utf-8')
        total += len(text.encode())
        for e in check_svg(text, frame.viewbox if frame else None):
            errors.append(f'{path}: {e}')
        info['levels'].append({'id': lvl['id'], 'minY': lo, 'maxY': hi, 'bytes': len(text.encode())})
    if total > TOTAL_BYTES:
        errors.append(f'all levels {total} bytes (limit {TOTAL_BYTES})')
    info['totalBytes'] = total
    # Every spawn and walking-graph place stands in some level band.
    if prev is not None:
        bands = [(l['minY'], l['maxY']) for l in levels if isinstance(l, dict) and isinstance(l.get('minY'), (int, float)) and isinstance(l.get('maxY'), (int, float))]
        feet = [('spawn ' + s['id'], s['pose']['position'][1]) for s in m.get('spawns', [])]
        feet += [('route node ' + n['id'], n['position'][1]) for n in namespace(m, '.routes').get('nodes', [])]
        for what, y in feet:
            if not any(lo <= y < hi for lo, hi in bands):
                errors.append(f'{what} (feet y {y:g}) is outside every level band')
    return errors, info
