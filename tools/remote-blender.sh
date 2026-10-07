#!/usr/bin/env bash
# SPDX-License-Identifier: MIT
# Blender is deliberately available only through the mains-powered bake host.
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
HOST="${HYPRUNE_BAKE_HOST:-10.2.2.2}"
REMOTE="${HYPRUNE_BAKE_DIR:-hyprune-bake/worlds-switchyard}"
[[ "$HOST" != localhost && "$HOST" != 127.* && "$HOST" != ::1 ]] || { echo 'A remote bake host is required' >&2; exit 2; }
[[ "$REMOTE" =~ ^[a-zA-Z0-9_./-]+$ && "$REMOTE" != /* && "$REMOTE" != *..* ]] || exit 2
ssh -o BatchMode=yes "$HOST" "mkdir -p '$REMOTE'"
rsync -az --exclude '__pycache__' "$ROOT/switchyard" "$ROOT/tools" "$ROOT/LICENSE" "$HOST:$REMOTE/"
ARGS=""
for arg in "$@"; do ARGS+=" $(printf '%q' "$arg")"; done
status=0
ssh -o BatchMode=yes "$HOST" "cd '$REMOTE' && flock .blender.lock blender$ARGS" || status=$?
mkdir -p "$ROOT/dist" "$ROOT/artifacts"
rsync -az "$HOST:$REMOTE/dist/" "$ROOT/dist/" || true
rsync -az --exclude 'film-frames' "$HOST:$REMOTE/artifacts/" "$ROOT/artifacts/" || true
exit "$status"
