#!/usr/bin/env bash
# SPDX-License-Identifier: MIT
# World format 0.7 optimisation on the bake host (never locally: basisu and
# meshopt encoding are heavy batch work, AGENTS.md rule 3).
#   tools/remote-optimize.sh <package-dir> <out-dir>
# Builds basisu v2.1.0 (the commit core vendors as its transcoder) once in
# ~/opt/hyprune on the host, encodes material textures to UASTC KTX2 with
# mips, runs tools/gltf/optimize.mjs and verify.mjs there, and fetches the
# package plus <out-dir>.verify.json. Fails if verification fails.
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
SRC="$(cd "$1" && pwd)"; OUT="$2"; NAME="$(basename "$SRC")"
HOST="${HYPRUNE_BAKE_HOST:-10.2.2.2}"
REMOTE="${HYPRUNE_OPTIMIZE_DIR:-hyprune-bake/optimize}"
BASISU_COMMIT=45d5f41015eecd9570d5a3f89ab9cc0037a25063
BASISU_DIR='~/opt/hyprune/basisu-2.1.0'
[[ "$HOST" != localhost && "$HOST" != 127.* && "$HOST" != ::1 ]] || { echo 'A remote bake host is required' >&2; exit 2; }
[[ "$(ssh -o BatchMode=yes "$HOST" hostname)" != "$(hostname)" ]] || { echo 'Bake host resolves to this machine; refusing' >&2; exit 2; }
[[ "$NAME" =~ ^[a-zA-Z0-9_.-]+$ ]] || exit 2

ssh -o BatchMode=yes "$HOST" bash -s <<EOF
set -euo pipefail
D=$BASISU_DIR
if [[ ! -x \$D/src/bin/basisu || "\$(git -C \$D/src rev-parse HEAD)" != $BASISU_COMMIT ]]; then
  mkdir -p \$D; [[ -d \$D/src ]] || git clone -q https://github.com/BinomialLLC/basis_universal \$D/src
  git -C \$D/src fetch -q origin && git -C \$D/src checkout -q $BASISU_COMMIT
  cmake -S \$D/src -B \$D/build -DCMAKE_BUILD_TYPE=Release >/dev/null && nice cmake --build \$D/build -j 32 >/dev/null
fi
mkdir -p '$REMOTE/tools' '$REMOTE/work'
EOF
rsync -az --delete --exclude node_modules "$ROOT/tools/gltf/" "$HOST:$REMOTE/tools/gltf/"
rsync -az --delete "$SRC/" "$HOST:$REMOTE/work/src-$NAME/"
ssh -o BatchMode=yes "$HOST" bash -s <<EOF
set -euo pipefail
cd '$REMOTE'
B=$BASISU_DIR/src/bin/basisu
(cd tools/gltf && npm ci --no-audit --no-fund >/dev/null)
W=work; S=\$W/src-$NAME; K=\$W/ktx2-$NAME; O=\$W/out-$NAME
rm -rf \$K && mkdir -p \$K
node tools/gltf/optimize.mjs --plan \$S > \$W/plan-$NAME.json
# One basisu per texture, all cores: mode -> flags per the draft 0.7 rules.
node -e 'for(const i of JSON.parse(require("fs").readFileSync(process.argv[1])).items)console.log(i.mode, i.png)' \$W/plan-$NAME.json |
 while read -r mode png; do
  case \$mode in srgb) f='-srgb';; linear) f='-linear';; normal) f='-linear -normal_map -mip_renorm';; esac
  echo "\$B -uastc -ktx2 -mipmap \$f -no_multithreading -output_path \$K \$S/\$png"
 done | nice xargs -P "\$(nproc)" -I{} sh -c '{} >/dev/null'
node tools/gltf/optimize.mjs \$S \$O --ktx2 \$K
node tools/gltf/verify.mjs \$S \$O --output \$W/verify-$NAME.json >/dev/null || { cat \$W/verify-$NAME.json; exit 1; }
EOF
mkdir -p "$OUT"
rsync -az --delete "$HOST:$REMOTE/work/out-$NAME/" "$OUT/"
rsync -az "$HOST:$REMOTE/work/verify-$NAME.json" "$OUT.verify.json"
rsync -az "$HOST:$REMOTE/work/plan-$NAME.json" "$OUT.plan.json"
python3 -c "import json,sys;r=json.load(open(sys.argv[1]));print(json.dumps({k:r[k] for k in ['status','formatVersion','extensionsRequired','counts','maxCollisionErrorMeters','packageMiB']},indent=1))" "$OUT.verify.json"
