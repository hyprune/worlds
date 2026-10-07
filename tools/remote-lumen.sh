#!/usr/bin/env bash
# SPDX-License-Identifier: MIT
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
HOST="${HYPRUNE_BAKE_HOST:-10.2.2.2}"
REMOTE=hyprune-bake/worlds-lumen-reach
[[ "$HOST" != localhost && "$HOST" != 127.* && "$HOST" != ::1 ]] || exit 2
[[ "$(ssh -o BatchMode=yes "$HOST" hostname)" != "$(hostname)" ]] || exit 2
ssh -o BatchMode=yes "$HOST" "mkdir -p '$REMOTE'"
rsync -az --exclude __pycache__ "$ROOT/lumen-reach" "$ROOT/tools" "$ROOT/switchyard" "$ROOT/LICENSE" "$HOST:$REMOTE/"
ARGS=""
for arg in "$@"; do ARGS+=" $(printf '%q' "$arg")"; done
status=0
ssh -o BatchMode=yes "$HOST" "cd '$REMOTE' && HYPRUNE_REMOTE_BLENDER=1 flock .blender.lock blender -b -t 12 --python-exit-code 1 --python lumen-reach/build.py --$ARGS" || status=$?
mkdir -p "$ROOT/dist/com.hyprune.lumen-reach" "$ROOT/artifacts/lumen-reach"
rsync -az --delete "$HOST:$REMOTE/dist/com.hyprune.lumen-reach/" "$ROOT/dist/com.hyprune.lumen-reach/" || true
rsync -az "$HOST:$REMOTE/artifacts/lumen-reach/" "$ROOT/artifacts/lumen-reach/" || true
exit "$status"
