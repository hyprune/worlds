#!/usr/bin/env bash
# SPDX-License-Identifier: MIT
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
export HYPRUNE_BAKE_PROJECT=lumen-reach
export HYPRUNE_BAKE_DIR=hyprune-bake/worlds-lumen-reach
exec "$ROOT/tools/remote-blender.sh" -b -t 12 --python-exit-code 1 --python lumen-reach/build.py -- "$@"
