# SPDX-License-Identifier: MIT
"""Resolve authored region ownership by stable node name after each glTF export."""
import argparse
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def annotate(manifest, scene, spec_path=None):
    name = manifest['id'].removeprefix('com.hyprune.')
    spec = json.loads((spec_path or ROOT / name / 'visibility.json').read_text())
    names = {}
    for i, node in enumerate(scene['nodes']):
        names.setdefault(node.get('name'), []).append(i)
    areas = []
    for area in spec['areas']:
        nodes = []
        for name in area['nodeNames']:
            assert len(names.get(name, [])) == 1, ('missing or ambiguous visibility node', name)
            nodes.append(names[name][0])
        areas.append({k: area[k] for k in ['id', 'bounds', 'visibleFrom']} | {'nodes': nodes})
    manifest.update(formatVersion=spec['formatVersion'], version=spec['version'], visibility={'areas': areas})
    return manifest


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('package', type=Path)
    args = parser.parse_args()
    path = args.package / 'world.json'
    manifest = json.loads(path.read_text())
    scene = json.loads((args.package / manifest['scene']).read_text())
    annotate(manifest, scene)
    path.write_text(json.dumps(manifest, indent=2) + '\n')
    print(manifest['id'], manifest['version'], 'visibility regions:', len(manifest['visibility']['areas']))
