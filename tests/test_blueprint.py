# SPDX-License-Identifier: MIT
"""com.hyprune.blueprint: derived level plans and their validator.

Synthetic packages (boxes exported as glTF): a walled 24 x 18 m hall with
a doorway, optionally a 3 m deck over part of it reached by a ramp. Checks
level detection (one and two levels), content classes, the opening
heuristic, the frame, the byte budgets, --create-map and the SVG allow-list.
Derivation needs node and tools/navmesh/node_modules (`make navmesh-deps`);
the validator tests run without them.
"""
import json, subprocess, sys, tempfile, unittest
from pathlib import Path
import numpy as np
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'tools'))
import blueprint as B
FACES = [(0, 1, 2), (0, 2, 3), (4, 6, 5), (4, 7, 6), (0, 5, 1), (0, 4, 5), (1, 6, 2), (1, 5, 6), (2, 7, 3), (2, 6, 7), (3, 4, 0), (3, 7, 4)]
NAVMESH = (ROOT / 'tools/navmesh/node_modules/recast-navigation').exists()
MAP_SVG = '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 560 440"><rect width="560" height="440" fill="#123"/></svg>\n'
# Bounds [-14, -11, 14, 11] over the 560 x 440 viewBox: 20 units per metre.
MAP = {'version': '0.1', 'path': 'map.svg', 'projection': 'xz', 'north': [0, 0, -1], 'bounds': [-14, -11, 14, 11],
       'worldToMap': [1 / 28, 0, 0, 1 / 22, .5, .5]}


def box(lo, hi):
    (x0, y0, z0), (x1, y1, z1) = lo, hi
    return [[x0, y0, z0], [x1, y0, z0], [x1, y0, z1], [x0, y0, z1], [x0, y1, z0], [x1, y1, z0], [x1, y1, z1], [x0, y1, z1]]


def ramp(xtop, xfoot, z0, z1, rise):
    """Solid wedge rising along -x from 0 at xfoot to `rise` at xtop."""
    c = box([xtop, -.2, z0], [xfoot, 0, z1])
    c[4][1] = c[7][1] = rise
    return c


def hall(deck=False):
    """Floor, four 3.5 m walls, a wall across z = 0 with a 1.4 m doorway."""
    s = [box([-12, -.2, -9], [12, 0, 9]), box([-12.3, 0, -9.3], [12.3, 3.5, -9]), box([-12.3, 0, 9], [12.3, 3.5, 9.3]),
         box([-12.3, 0, -9], [-12, 3.5, 9]), box([12, 0, -9], [12.3, 3.5, 9]),
         box([-12, 0, -.15], [-.7, 3.5, .15]), box([.7, 0, -.15], [12, 3.5, .15])]
    if deck:
        # A 3 m deck over the north-west corner (x -12..-7, z -9..-4), a
        # 10 m ramp (slope 0.3) along the north wall up to it.
        s += [box([-12, 2.8, -9], [-7, 3, -4]), ramp(-7, 3, -9, -7, 3)]
    return s


def package(root, solids, map_ext=True, routes=True):
    root.mkdir(parents=True, exist_ok=True)
    pts = np.array([v for s in solids for v in s], '<f4')
    idx = np.array([FACES for _ in solids], '<u4').reshape(-1)
    (root / 'scene.bin').write_bytes(pts.tobytes() + idx.tobytes())
    acc, meshes, nodes = [], [], []
    for i in range(len(solids)):
        acc += [{'bufferView': 0, 'byteOffset': i * 96, 'componentType': 5126, 'count': 8, 'type': 'VEC3'},
                {'bufferView': 1, 'byteOffset': i * 144, 'componentType': 5125, 'count': 36, 'type': 'SCALAR'}]
        meshes.append({'primitives': [{'attributes': {'POSITION': 2 * i}, 'indices': 2 * i + 1}]})
        nodes.append({'mesh': i, 'name': f'Collision-{i}'})
    doc = {'asset': {'version': '2.0'}, 'buffers': [{'uri': 'scene.bin', 'byteLength': pts.nbytes + idx.nbytes}],
           'bufferViews': [{'buffer': 0, 'byteLength': pts.nbytes}, {'buffer': 0, 'byteOffset': pts.nbytes, 'byteLength': idx.nbytes}],
           'accessors': acc, 'meshes': meshes, 'nodes': nodes, 'scenes': [{'nodes': list(range(len(nodes)))}]}
    (root / 'scene.gltf').write_text(json.dumps(doc))
    ext = {}
    if map_ext:
        ext['com.hyprune.map'] = MAP
        (root / 'map.svg').write_text(MAP_SVG)
    if routes:
        ext['test.routes'] = {'nodes': [{'id': 'south', 'position': [0, 0, 5]}, {'id': 'north', 'position': [0, 0, -5]}],
                              'edges': [{'from': 'south', 'to': 'north'}]}
    world = {'id': 'test.blueprint', 'name': 'Test Hall', 'version': '0', 'scene': 'scene.gltf', 'defaultSpawn': 'a',
             'spawns': [{'id': 'a', 'pose': {'position': [-8, 0, 6], 'rotation': [0, 0, 0, 1]}}],
             'anchors': [{'id': 'wall-screen', 'pose': {'position': [6, 1.8, 8.9], 'rotation': [0, 1, 0, 0]}, 'size': [4, 2.25]}],
             'zones': [{'id': 'south-hall', 'name': 'South Hall', 'bounds': {'min': [-12, 0, 0], 'max': [12, 4, 9]}}],
             'collision': [{'node': i, 'shape': 'mesh', 'layer': 'static'} for i in range(len(nodes))], 'extensions': ext}
    (root / 'world.json').write_text(json.dumps(world, indent=2))
    return root


def classes(svg):
    import re
    return set(re.findall(r'class="([a-z]+)"', svg))


@unittest.skipUnless(NAVMESH, 'needs tools/navmesh/node_modules (make navmesh-deps)')
class Derive(unittest.TestCase):
    def setUp(self):
        t = tempfile.TemporaryDirectory()
        self.addCleanup(t.cleanup)
        self.tmp = Path(t.name)

    def run_tool(self, root, *args):
        r = subprocess.run([sys.executable, str(ROOT / 'tools/derive-blueprint.py'), str(root), *args], capture_output=True, text=True)
        self.assertEqual(r.returncode, 0, r.stderr)
        return json.loads(r.stdout)

    def check(self, root):
        r = subprocess.run([sys.executable, str(ROOT / 'tools/check-blueprint.py'), str(root)], capture_output=True, text=True)
        return r.returncode, json.loads(r.stdout)

    def test_one_level(self):
        root = package(self.tmp / 'one', hall())
        report = self.run_tool(root, '--in-place')
        self.assertEqual([l['id'] for l in report['levels']], ['ground'])
        lvl = report['levels'][0]
        self.assertEqual(lvl['openings'], 1, lvl)
        self.assertEqual(lvl['screens'], 1)
        self.assertEqual(lvl['areas'], 1)
        svg = (root / 'blueprint/ground.svg').read_text()
        self.assertTrue({'floor', 'wall', 'opening', 'screen', 'route', 'waypoint', 'grid', 'outline', 'label', 'area'} <= classes(svg), classes(svg))
        self.assertIn('viewBox="0 0 560 440"', svg)
        m = json.loads((root / 'world.json').read_text())
        self.assertEqual(m['extensions']['com.hyprune.map'], MAP)           # map untouched
        self.assertEqual(m['extensions']['com.hyprune.blueprint']['levels'][0]['path'], 'blueprint/ground.svg')
        code, rep = self.check(root)
        self.assertEqual(code, 0, rep['errors'])
        # The doorway (x -0.7..0.7 on z = 0) is drawn there: 20 units/m around (280, 220).
        frame = B.Frame((0, 0, 560, 440), MAP['worldToMap'], 'test')
        self.assertTrue(np.allclose(frame.xy([0, 0])[0], [280, 220]))

    def test_two_levels(self):
        root = package(self.tmp / 'two', hall(deck=True))
        report = self.run_tool(root, '--in-place')
        levels = report['levels']
        self.assertEqual([l['id'] for l in levels], ['ground', 'level-1'])
        self.assertLessEqual(levels[0]['maxY'], levels[1]['minY'])
        self.assertTrue(levels[0]['minY'] < 0 < levels[0]['maxY'] <= 3 < levels[1]['maxY'], levels)
        self.assertIn('stair', classes((root / 'blueprint/ground.svg').read_text()) | classes((root / 'blueprint/level-1.svg').read_text()))
        self.assertGreater(levels[1]['floorM2'], 20)
        code, rep = self.check(root)
        self.assertEqual(code, 0, rep['errors'])
        # Forced: one level only.
        self.assertEqual(len(self.run_tool(root, '--levels', '1')['levels']), 1)

    def test_budget_enforced(self):
        root = package(self.tmp / 'budget', hall())
        world, frame, _ = B.load_world(root)
        with self.assertRaises(B.BlueprintError) as e:
            B.derive(world, frame, budget=(1500, 3000))
        self.assertIn('over budget', str(e.exception))

    def test_create_map(self):
        root = package(self.tmp / 'nomap', hall(deck=True), map_ext=False)
        r = subprocess.run([sys.executable, str(ROOT / 'tools/derive-blueprint.py'), str(root), '--in-place'], capture_output=True, text=True)
        self.assertEqual(r.returncode, 1)
        self.assertIn('--create-map', r.stderr)
        report = self.run_tool(root, '--in-place', '--create-map')
        made = report['createdMap']
        a, b, c, d, e, f = made['worldToMap']
        self.assertTrue(b == c == 0 and abs(a * 1000 / (d * float(report['frame']['viewBox'][3])) - 1) < 1e-3)  # one scale
        m = json.loads((root / 'world.json').read_text())
        self.assertEqual(m['extensions']['com.hyprune.map']['path'], 'map.svg')
        svg = (root / 'map.svg').read_text()
        self.assertNotIn('class=', svg)
        self.assertEqual(B.check_svg(svg, allow_class=False), [])
        code, rep = self.check(root)
        self.assertEqual(code, 0, rep['errors'])
        # A package with a map keeps it.
        root2 = package(self.tmp / 'withmap', hall())
        self.assertIsNone(self.run_tool(root2, '--create-map')['createdMap'])


class Validator(unittest.TestCase):
    GOOD = ('<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 560 440">\n<path class="wall" d="M1 1l2 2"/>\n'
            '<text class="label" x="5" y="5" font-size="9">Hall</text>\n</svg>\n')

    def test_allow_list(self):
        self.assertEqual(B.check_svg(self.GOOD, (0, 0, 560, 440)), [])
        bad = {
            'script': self.GOOD.replace('<path', '<script/><path'),
            'style attribute': self.GOOD.replace('<path class="wall"', '<path style="fill:red"'),
            'href': self.GOOD.replace('<path class="wall"', '<path fill="url(#a)"'),
            'class vocabulary': self.GOOD.replace('class="wall"', 'class="door"'),
            'doctype': '<!DOCTYPE svg>' + self.GOOD,
            'comment': self.GOOD.replace('<path', '<!-- x --><path'),
            'xml declaration': '<?xml version="1.0"?>' + self.GOOD,
            'namespace': self.GOOD.replace('http://www.w3.org/2000/svg', 'http://example.org/x'),
            'ampersand': self.GOOD.replace('Hall', 'A &amp; B').replace('font-size="9"', 'font-size="9&amp;"'),
            'long value': self.GOOD.replace('M1 1l2 2', 'M1 1' + 'l1 1' * 2100),
            'nodes': self.GOOD.replace('<path', '<g/>' * 4100 + '<path'),
            'stroke-dasharray': self.GOOD.replace('<path class="wall"', '<path stroke-dasharray="2 2"'),
            'viewBox': self.GOOD.replace('0 0 560 440', '0 0 500 440'),
            'bytes': self.GOOD + ' ' * 70000,
        }
        for what, svg in bad.items():
            self.assertTrue(B.check_svg(svg, (0, 0, 560, 440)), f'{what} accepted')
        self.assertTrue(B.check_svg(self.GOOD, allow_class=False), 'class accepted in a plain map SVG')

    def package(self, levels, files=None):
        t = tempfile.TemporaryDirectory()
        self.addCleanup(t.cleanup)
        root = Path(t.name)
        (root / 'blueprint').mkdir()
        for name, text in (files or {}).items():
            (root / name).write_text(text)
        (root / 'map.svg').write_text(MAP_SVG)
        world = {'id': 't', 'spawns': [{'id': 'a', 'pose': {'position': [0, 0, 0]}}],
                 'extensions': {'com.hyprune.map': MAP, 'com.hyprune.blueprint': {'version': '0.1', 'levels': levels}}}
        (root / 'world.json').write_text(json.dumps(world))
        return root

    def test_extension_shape(self):
        lvl = lambda i, lo, hi, **kw: {'id': i, 'name': i.title(), 'minY': lo, 'maxY': hi, 'path': f'blueprint/{i}.svg'} | kw
        files = {f'blueprint/{i}.svg': self.GOOD for i in ('ground', 'upper')}
        ok = self.package([lvl('ground', -1, 3), lvl('upper', 3, 9)], files)
        self.assertEqual(B.check_package(ok)[0], [])
        cases = {
            'overlap': [lvl('ground', -1, 4), lvl('upper', 3, 9)],
            'unsorted': [lvl('upper', 3, 9), lvl('ground', -1, 3)],
            'empty band': [lvl('ground', 3, 3)],
            'bad id': [lvl('Ground', -1, 3)],
            'duplicate id': [lvl('ground', -1, 3), lvl('ground', 3, 9)],
            'unsafe path': [lvl('ground', -1, 3, path='../ground.svg')],
            'missing file': [lvl('ground', -1, 3, path='blueprint/none.svg')],
            'extra key': [lvl('ground', -1, 3, extra=1)],
            'spawn outside': [lvl('upper', 3, 9)],
            'seven levels': [lvl(f'l{k}', k, k + 1) for k in range(7)],
        }
        for what, levels in cases.items():
            self.assertTrue(B.check_package(self.package(levels, files))[0], f'{what} accepted')
        # No map frame at all.
        root = self.package([lvl('ground', -1, 3)], files)
        m = json.loads((root / 'world.json').read_text())
        del m['extensions']['com.hyprune.map']
        (root / 'world.json').write_text(json.dumps(m))
        self.assertTrue(any('map' in e for e in B.check_package(root)[0]))

    def test_legacy_frame(self):
        frame = B.Frame((0, 0, 900, 1000), (19 / 900, 0, 0, -18 / 1000, 450 / 900, 200 / 1000), B.LEGACY_MAP)
        self.assertTrue(np.allclose(frame.xy([[0, 0], [10, -10]]), [[450, 200], [640, 380]]))

    def test_path_writer(self):
        self.assertEqual(B.subpath(np.array([[1.04, 2], [3, 2], [3, 2.01], [3, 4]]), False), 'M1 2l2 0 0 2')
        self.assertEqual(B.num(-5), '-.5')
        parts = B.paths('wall', ['M0 0l1 1' * 600] * 3)
        self.assertTrue(len(parts) >= 3 and all(len(p) < B.MAX_VALUE + 40 for p in parts))


if __name__ == '__main__':
    unittest.main()
