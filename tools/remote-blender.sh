#!/usr/bin/env bash
# SPDX-License-Identifier: MIT
# Blender is deliberately available only through the mains-powered bake host.
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
HOST="${HYPRUNE_BAKE_HOST:-10.2.2.2}"
REMOTE="${HYPRUNE_BAKE_DIR:-hyprune-bake/worlds-switchyard}"
[[ "$HOST" != localhost && "$HOST" != 127.* && "$HOST" != ::1 ]] || { echo 'A remote bake host is required' >&2; exit 2; }
[[ "$REMOTE" =~ ^[a-zA-Z0-9_./-]+$ && "$REMOTE" != /* && "$REMOTE" != *..* ]] || exit 2
BAKE_MACHINE="$(ssh -o BatchMode=yes "$HOST" hostname)"
[[ "$BAKE_MACHINE" != "$(hostname)" ]] || { echo 'Bake host resolves to this machine; refusing local Blender' >&2; exit 2; }
ssh -o BatchMode=yes "$HOST" "mkdir -p '$REMOTE'"
rsync -az --exclude '__pycache__' "$ROOT/lumen-reach" "$ROOT/switchyard" "$ROOT/tools" "$ROOT/LICENSE" "$HOST:$REMOTE/"
ARGS=""
for arg in "$@"; do ARGS+=" $(printf '%q' "$arg")"; done
status=0
ssh -o BatchMode=yes "$HOST" "cd '$REMOTE' && HYPRUNE_REMOTE_BLENDER=1 flock .blender.lock blender$ARGS" || status=$?
mkdir -p "$ROOT/dist" "$ROOT/artifacts"
if [[ "${HYPRUNE_BAKE_PROJECT:-switchyard}" == lumen-reach ]]; then
  mkdir -p "$ROOT/dist/com.hyprune.lumen-reach" "$ROOT/artifacts/lumen-reach"
  if [[ "$status" -eq 0 ]]; then rsync -az --delete "$HOST:$REMOTE/dist/com.hyprune.lumen-reach/" "$ROOT/dist/com.hyprune.lumen-reach/"; fi
  rsync -az "$HOST:$REMOTE/artifacts/lumen-reach/" "$ROOT/artifacts/lumen-reach/" || true
  exit "$status"
fi
mkdir -p "$ROOT/dist/com.hyprune.switchyard"
if [[ "$status" -eq 0 ]]; then
  rsync -az --delete "$HOST:$REMOTE/dist/com.hyprune.switchyard/" "$ROOT/dist/com.hyprune.switchyard/"
fi
mkdir -p "$ROOT/artifacts/switchyard"
rsync -az --exclude 'film-frames' "$HOST:$REMOTE/artifacts/switchyard/" "$ROOT/artifacts/switchyard/" || true
exit "$status"
