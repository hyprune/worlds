#!/usr/bin/env bash
# SPDX-License-Identifier: MIT
# Optimise built machine objects with the world optimiser and install them.
#   objects/machines/optimise.sh [id ...]      (default: every machine)
# dist/objects/machines/<id>/ is staged as a minimal package (world.json naming
# object.gltf, no lightmaps) so tools/remote-optimize.sh can run unchanged on
# the bake host: UASTC KTX2 textures, meshopt + quantised geometry, and
# verify.mjs (same nodes, meshes and materials by index and name). The result
# (object.gltf, object.bin, *.ktx2) plus object.json and thumbnail.png goes
# to objects/machines/<id>/.
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
IDS=("$@"); [[ ${#IDS[@]} -gt 0 ]] || IDS=(job-token ci-conveyor queue-stack server-rack deploy-lift build-monitor)
for id in "${IDS[@]}"; do
  [[ "$id" =~ ^[a-z][a-z0-9-]*$ ]] || exit 2
  src="$ROOT/dist/objects/machines/$id"; stage="$ROOT/build/machines-stage/machine-$id"; opt="$ROOT/build/machines-opt/$id"
  rm -rf "$stage"; mkdir -p "$stage"
  cp "$src"/object.gltf "$src"/object.bin "$src"/*.png "$stage"/; rm -f "$stage/thumbnail.png"
  printf '{"formatVersion": "0.8", "scene": "object.gltf", "lightmaps": [], "collision": []}\n' > "$stage/world.json"
  "$ROOT/tools/remote-optimize.sh" "$stage" "$opt" > /dev/null
  python3 -c "import json,sys; r=json.load(open(sys.argv[1])); assert r['status']=='PASS', r" "$opt.verify.json"
  dst="$ROOT/objects/machines/$id"
  find "$dst" -maxdepth 1 -type f ! -name build.py -delete
  cp "$opt"/object.gltf "$opt"/*.bin "$opt"/*.ktx2 "$src"/object.json "$dst"/
  [[ -f "$src/thumbnail.png" ]] && cp "$src/thumbnail.png" "$dst"/
  echo "$id: $(python3 -c "import json,sys; r=json.load(open(sys.argv[1])); print(r['status'], r['extensionsRequired'], r['counts'])" "$opt.verify.json")"
done
