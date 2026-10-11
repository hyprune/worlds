#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Derive `com.hyprune.blueprint` 0.1 level plans of a built world package.

  derive-blueprint.py PACKAGE [--output DIR] [--in-place] [--levels auto|N]
                      [--svg-preview OUT.png] [--create-map]

Reads world format 0.6 source packages and 0.7 release packages (geometry
decoded by tools/gltf/decode.mjs). Builds the package's Recast navmesh
(tools/navmesh, `make navmesh-deps`), detects the levels, draws one SVG per
level in the map's frame and simplifies until every SVG fits 64 KiB and all
fit 256 KiB (fails otherwise). Prints a JSON report.

--output DIR    write DIR/<level>.svg and DIR/report.json (package untouched)
--in-place      write PACKAGE/blueprint/<level>.svg (stale ones removed) and
                add or replace the extension in PACKAGE/world.json
--svg-preview   render a dark blueprint preview (rsvg-convert): one sheet,
                or one PNG per level when the name contains {level}
--create-map    for a package with neither com.hyprune.map nor the legacy
                com.hyprune.switchyard.map: derive a north-up com.hyprune.map
                0.1 frame (walkable extent + 6 m, viewBox 0 0 1000 H) and an
                overview map.svg (all levels flattened, baked colours, plain
                map SVG subset, <= 64 KiB); with --in-place both go into the
                package. A package with a map keeps its frame.
Method and content rules: tools/blueprint.py.
"""
import argparse, json, sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))
import blueprint as B
import preview_blueprint


def main():
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument('package', type=Path)
    p.add_argument('--output', type=Path)
    p.add_argument('--in-place', action='store_true')
    p.add_argument('--levels', default='auto', help='auto or 1..6')
    p.add_argument('--svg-preview', type=Path)
    p.add_argument('--create-map', action='store_true', help='derive a com.hyprune.map when the package has none')
    a = p.parse_args()
    if a.levels != 'auto' and not a.levels.isdigit():
        p.error('--levels takes auto or a number 1..6')
    try:
        world, frame, created = B.load_world(a.package, create_map=a.create_map)
        result = B.derive(world, frame, a.levels, create_map=created)
    except B.BlueprintError as e:
        sys.exit(f'derive-blueprint: {e}')
    for lid, text in result['svgs'].items():
        errors = B.check_svg(text, frame.viewbox)
        if errors:
            sys.exit(f'derive-blueprint: generated {lid}.svg fails the blueprint rules: {errors}')
    report = {'package': str(a.package), 'world': world.m['id'], 'version': world.m.get('version')} | result['report']
    if 'map' in result:
        errors = B.check_svg(result['map']['svg'], frame.viewbox, allow_class=False)
        if errors:
            sys.exit(f'derive-blueprint: generated map.svg fails the map SVG rules: {errors}')
    elif a.create_map:
        report['createdMap'] = None      # the package's own map frame is kept
    if a.output:
        a.output.mkdir(parents=True, exist_ok=True)
        if 'map' in result:
            (a.output / 'map.svg').write_text(result['map']['svg'])
        for lid, text in result['svgs'].items():
            (a.output / f'{lid}.svg').write_text(text)
        (a.output / 'report.json').write_text(json.dumps(report, indent=1) + '\n')
    if a.in_place:
        B.write_in_place(a.package, result)
        errors, _ = B.check_package(a.package)
        if errors:
            sys.exit(f'derive-blueprint: package fails check-blueprint after writing: {errors}')
    if a.svg_preview:
        report['previews'] = preview_blueprint.render(result, frame, a.svg_preview, world.m.get('name', world.m['id']))
    print(json.dumps(report, indent=1))


if __name__ == '__main__':
    main()
