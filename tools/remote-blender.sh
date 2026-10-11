#!/usr/bin/env bash
# SPDX-License-Identifier: MIT
# Blender is deliberately available only through the mains-powered bake host.
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
REMOTE="${HYPRUNE_BAKE_DIR:-hyprune-bake/worlds-switchyard}"
[[ "$REMOTE" =~ ^[a-zA-Z0-9_./-]+$ && "$REMOTE" != /* && "$REMOTE" != *..* ]] || exit 2
source "$ROOT/tools/bake-host.sh"
on_host "mkdir -p '$REMOTE'"
rsync -az --exclude '__pycache__' --exclude node_modules "$ROOT/lumen-reach" "$ROOT/switchyard" "$ROOT/objects" "$ROOT/tools" "$ROOT/LICENSE" "$(host_path "$REMOTE")/"
ARGS=""
for arg in "$@"; do ARGS+=" $(printf '%q' "$arg")"; done
status=0
on_host "cd '$REMOTE' && HYPRUNE_REMOTE_BLENDER=1 flock .blender.lock blender$ARGS" || status=$?
mkdir -p "$ROOT/dist" "$ROOT/artifacts"
if [[ "${HYPRUNE_BAKE_PROJECT:-switchyard}" == objects ]]; then
  mkdir -p "$ROOT/dist/objects"
  if [[ "$status" -eq 0 ]]; then rsync -az --delete "$(host_path "$REMOTE/dist/objects/")" "$ROOT/dist/objects/"; fi
  exit "$status"
fi
if [[ "${HYPRUNE_BAKE_PROJECT:-switchyard}" == lumen-reach ]]; then
  mkdir -p "$ROOT/dist/com.hyprune.lumen-reach" "$ROOT/artifacts/lumen-reach"
  if [[ "$status" -eq 0 ]]; then rsync -az --delete "$(host_path "$REMOTE/dist/com.hyprune.lumen-reach/")" "$ROOT/dist/com.hyprune.lumen-reach/"; fi
  rsync -az "$(host_path "$REMOTE/artifacts/lumen-reach/")" "$ROOT/artifacts/lumen-reach/" || true
  exit "$status"
fi
mkdir -p "$ROOT/dist/com.hyprune.switchyard"
if [[ "$status" -eq 0 ]]; then
  rsync -az --delete "$(host_path "$REMOTE/dist/com.hyprune.switchyard/")" "$ROOT/dist/com.hyprune.switchyard/"
fi
mkdir -p "$ROOT/artifacts/switchyard"
rsync -az --exclude 'film-frames' "$(host_path "$REMOTE/artifacts/switchyard/")" "$ROOT/artifacts/switchyard/" || true
exit "$status"
