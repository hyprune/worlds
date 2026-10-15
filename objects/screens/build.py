# SPDX-License-Identifier: MIT
"""Workspace screens: four starter objects that show a workspace (object format 0.11, the
`mount` trait's mounted-workspace anchor; RFC-0011 amendment "workspace screens").

    python3 objects/screens/build.py [OUT]          (default objects/screens)

Writes OUT/<id>/object.glb and object.json for
  workspace-screen-wall-16x9   a slim bezel that hangs on a wall, screen 3.2 x 1.8 m
  workspace-screen-wall-21x9   the same at 21:9, screen 4.2 x 1.8 m
  workspace-screen-stand-16x9  the 16:9 bezel on two legs with feet, for the floor
  workspace-screen-stand-21x9  the 21:9 bezel on its legs
Thumbnails come from tools/object/thumbnail.py (Blender, bake host):
  tools/remote-blender.sh -b --factory-startup -P tools/object/thumbnail.py -- \\
      objects/screens/<id>/object.glb objects/screens/<id>/thumbnail.png

Plain boxes, no textures: a dark metal frame 0.08 m wide and deep, the panel recessed to
0.05 m, a cyan accent strip on the lower bezel and, for the stands, square legs inset from the
frame's ends standing on flat feet. The screen rectangle (the anchor) sits 0.01 m in front of
the panel. The collision proxy (outside the glTF scene, so never drawn) is the frame's back
slab plus the legs and feet: it stays behind the screen plane, so aiming at the screen finds
the workspace. Asset space: glTF (+Y up), metres; wall screens are centred on the origin with
their back on z = 0 (movable surface `wall`), stands put their feet on y = 0 (surface `floor`).
Original procedural geometry, CC-BY-4.0, Hyprune contributors.
"""
import json, pathlib, struct, sys

HERE = pathlib.Path(__file__).resolve().parent
SIZES = {'16x9': (3.2, 1.8), '21x9': (4.2, 1.8)}
BORDER, DEPTH, PANEL_DEPTH, SCREEN_Z = .08, .08, .05, .06
STAND_FRAME_BOTTOM = .82  # the stand's frame lower edge above the floor
LEG, LEG_INSET, FOOT = .1, .46, (.12, .05, .7)  # leg side, inset from the frame end, foot w/h/depth
MATERIALS = [
    {'name': 'frame', 'pbrMetallicRoughness': {'baseColorFactor': [.045, .05, .056, 1], 'roughnessFactor': .38, 'metallicFactor': .7}},
    {'name': 'panel', 'pbrMetallicRoughness': {'baseColorFactor': [.008, .009, .011, 1], 'roughnessFactor': .25, 'metallicFactor': 0}},
    {'name': 'accent', 'pbrMetallicRoughness': {'baseColorFactor': [.25, .85, 1.0, 1], 'roughnessFactor': .4, 'metallicFactor': 0},
     'emissiveFactor': [.25, .85, 1.0]},
]


def box(lo, hi):
    """36 vertices (position, normal) of an axis-aligned box, outward faces."""
    (x0, y0, z0), (x1, y1, z1) = lo, hi
    faces = [((1, 0, 0), [(x1, y0, z0), (x1, y1, z0), (x1, y1, z1), (x1, y0, z1)]),
             ((-1, 0, 0), [(x0, y0, z1), (x0, y1, z1), (x0, y1, z0), (x0, y0, z0)]),
             ((0, 1, 0), [(x0, y1, z1), (x1, y1, z1), (x1, y1, z0), (x0, y1, z0)]),
             ((0, -1, 0), [(x0, y0, z0), (x1, y0, z0), (x1, y0, z1), (x0, y0, z1)]),
             ((0, 0, 1), [(x0, y0, z1), (x1, y0, z1), (x1, y1, z1), (x0, y1, z1)]),
             ((0, 0, -1), [(x1, y0, z0), (x0, y0, z0), (x0, y1, z0), (x1, y1, z0)])]
    return [(p, n) for n, q in faces for p in (q[0], q[1], q[2], q[0], q[2], q[3])]


def screen(kind, ratio):
    """Meshes {name: [(triangles, material)]}, the screen centre height and size."""
    w, h = SIZES[ratio]
    cy = 0.0 if kind == 'wall' else round(STAND_FRAME_BOTTOM + BORDER + h / 2, 4)
    W, H = w / 2 + BORDER, h / 2 + BORDER
    frame = (box((-W, cy + h / 2, 0), (W, cy + H, DEPTH)) + box((-W, cy - H, 0), (W, cy - h / 2, DEPTH)) +
             box((-W, cy - h / 2, 0), (-w / 2, cy + h / 2, DEPTH)) + box((w / 2, cy - h / 2, 0), (W, cy + h / 2, DEPTH)))
    accent = box((-.15 * w, cy - H + .022, DEPTH), (.15 * w, cy - H + .036, DEPTH + .005))
    panel = box((-w / 2, cy - h / 2, 0), (w / 2, cy + h / 2, PANEL_DEPTH))
    proxy = box((-W, cy - H, 0), (W, cy + H, PANEL_DEPTH))
    if kind == 'stand':
        legs = []
        for side in (-1, 1):
            x = side * (W - LEG_INSET)
            zc = DEPTH / 2
            legs += box((x - LEG / 2, FOOT[1], zc - LEG / 2), (x + LEG / 2, cy - H, zc + LEG / 2))
            legs += box((x - FOOT[0] / 2, 0, zc - FOOT[2] / 2), (x + FOOT[0] / 2, FOOT[1], zc + FOOT[2] / 2))
        frame += legs
        proxy += legs
    return {'bezel': [(frame, 0), (accent, 2)], 'panel': [(panel, 1)], 'proxy': [(proxy, None)]}, cy, (w, h)


def glb(meshes):
    blob, views, accessors, out_meshes, nodes = bytearray(), [], [], [], []

    def add(data, target, count, kind, extra):
        views.append({'buffer': 0, 'byteOffset': len(blob), 'byteLength': len(data), 'target': target})
        blob.extend(data)
        accessors.append({'bufferView': len(views) - 1, 'componentType': 5125 if kind == 'SCALAR' else 5126,
                          'count': count, 'type': kind, **extra})
        return len(accessors) - 1

    for name, primitives in meshes.items():
        prims = []
        for triangles, material in primitives:
            n = len(triangles)
            pos = [round(c, 6) for p, _ in triangles for c in p]
            nor = [float(c) for _, v in triangles for c in v]
            axes = [[p[k] for p, _ in triangles] for k in range(3)]
            prim = {'attributes': {
                'POSITION': add(struct.pack(f'<{3 * n}f', *pos), 34962, n, 'VEC3',
                                {'min': [round(min(a), 6) for a in axes], 'max': [round(max(a), 6) for a in axes]}),
                'NORMAL': add(struct.pack(f'<{3 * n}f', *nor), 34962, n, 'VEC3', {})},
                'indices': add(struct.pack(f'<{n}I', *range(n)), 34963, n, 'SCALAR', {})}
            if material is not None:
                prim['material'] = material
            prims.append(prim)
        out_meshes.append({'name': name, 'primitives': prims})
        nodes.append({'name': name, 'mesh': len(out_meshes) - 1})
    doc = {'asset': {'version': '2.0', 'generator': 'hyprune worlds objects/screens/build.py'}, 'scene': 0,
           'scenes': [{'nodes': [i for i, n in enumerate(nodes) if n['name'] != 'proxy']}],  # the proxy is never drawn
           'nodes': nodes, 'meshes': out_meshes, 'materials': MATERIALS, 'accessors': accessors,
           'bufferViews': views, 'buffers': [{'byteLength': len(blob)}]}
    text = json.dumps(doc, separators=(',', ':')).encode()
    text += b' ' * (-len(text) % 4)
    blob += b'\0' * (-len(blob) % 4)
    return (struct.pack('<III', 0x46546C67, 2, 28 + len(text) + len(blob)) + struct.pack('<II', len(text), 0x4E4F534A) + text +
            struct.pack('<II', len(blob), 0x004E4942) + bytes(blob))


def manifest(kind, ratio, cy, size, meshes):
    w, h = size
    points = [p for name, prims in meshes.items() if name != 'proxy' for tris, _ in prims for p, _ in tris]
    lo = [round(min(p[k] for p in points), 4) for k in range(3)]
    hi = [round(max(p[k] for p in points), 4) for k in range(3)]
    aspect = ratio.replace('x', ':')
    wall = kind == 'wall'
    return {
        'formatVersion': '0.11', 'id': f'workspace-screen-{kind}-{ratio}', 'version': '1.0.0',
        'name': f"{'Wall' if wall else 'Stand'} screen {aspect}",
        'description': ('A slim bezel that hangs on a wall and shows a workspace.' if wall else
                        'A screen on two legs that stands on the floor and shows a workspace.'),
        'category': 'signage', 'tags': ['screen', 'workspace', 'display', 'widescreen' if ratio == '16x9' else 'ultrawide'],
        'scene': 'object.glb', 'license': 'CC-BY-4.0',
        'attribution': [{'path': '.', 'author': 'Hyprune contributors', 'license': 'CC-BY-4.0', 'source': 'https://github.com/hyprune/worlds'}],
        'bounds': {'min': lo, 'max': hi}, 'thumbnail': 'thumbnail.png', 'lighting': {'mode': 'probe'},
        'traits': {
            'mount': {'anchors': [{'id': 'screen', 'role': 'mounted-workspace', 'mountType': 'hanging-wall' if wall else 'kiosk-pillar',
                                   'pose': {'position': [0, cy, SCREEN_Z], 'rotation': [0, 0, 0, 1]}, 'size': [w, h],
                                   'screenType': 'com.hyprune.window', 'frameNode': 'bezel'}]},
            'collidable': {'node': 'proxy'},
            'movable': {'surfaces': ['wall' if wall else 'floor'], 'scale': [.5, 2]}}}


def main(out):
    for kind in ('wall', 'stand'):
        for ratio in SIZES:
            meshes, cy, size = screen(kind, ratio)
            folder = out / f'workspace-screen-{kind}-{ratio}'
            folder.mkdir(parents=True, exist_ok=True)
            (folder / 'object.glb').write_bytes(glb(meshes))
            (folder / 'object.json').write_text(json.dumps(manifest(kind, ratio, cy, size, meshes), indent=1) + '\n')
            print(folder)


if __name__ == '__main__':
    main(pathlib.Path(sys.argv[1]) if len(sys.argv) > 1 else HERE)
