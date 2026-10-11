#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Validate a package's `com.hyprune.blueprint` 0.1 extension.

  check-blueprint.py PACKAGE [--output report.json] [--optional]

Enforces the RFC-0004 amendment and core's map SVG validator: extension
shape (version "0.1", 1..6 levels with exactly id/name/minY/maxY/path, slug
ids unique, names 1..64 characters, minY < maxY, sorted, maxY[i] <=
minY[i+1], package-relative safe .svg paths to regular files), byte budgets
(each SVG <= 65536, all <= 262144), the SVG subset (no '<!' or '<?', root
<svg> in the SVG namespace, elements svg g rect path circle ellipse line
polyline polygon text tspan, core's attribute allow-list plus `class` from
the role vocabulary, values <= 8192 characters without & < > url href ://,
<= 4096 nodes, depth <= 32), frame consistency (a com.hyprune.map 0.1 or
the legacy com.hyprune.switchyard.map adapter; every level's viewBox equals
the map's; a com.hyprune.map's own SVG passes the plain map rules), and
that every spawn and route node stands in some level band. Exit 1 on
failure. --optional passes a package without the extension.
"""
import argparse, json, sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))
import blueprint as B

p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
p.add_argument('package', type=Path)
p.add_argument('--output', type=Path)
p.add_argument('--optional', action='store_true')
a = p.parse_args()
manifest = json.loads((a.package / 'world.json').read_text())
if a.optional and 'com.hyprune.blueprint' not in manifest.get('extensions', {}):
    errors, info = [], {'note': 'no com.hyprune.blueprint extension (optional)'}
else:
    errors, info = B.check_package(a.package)
report = {'status': 'FAIL' if errors else 'PASS', 'package': str(a.package), 'world': manifest.get('id'),
          'version': manifest.get('version'), 'errors': errors} | info
text = json.dumps(report, indent=1) + '\n'
if a.output:
    a.output.parent.mkdir(parents=True, exist_ok=True)
    a.output.write_text(text)
print(text, end='')
sys.exit(1 if errors else 0)
