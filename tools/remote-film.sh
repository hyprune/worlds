#!/usr/bin/env bash
# SPDX-License-Identifier: MIT
# Resumable film job survives SSH interruption. Blender stays on the bake host.
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
HOST="${HYPRUNE_BAKE_HOST:-10.2.2.2}"
REMOTE="${HYPRUNE_BAKE_DIR:-hyprune-bake/worlds-switchyard}"
[[ "$HOST" != localhost && "$HOST" != 127.* && "$HOST" != ::1 ]] || exit 2
[[ "$REMOTE" =~ ^[a-zA-Z0-9_./-]+$ && "$REMOTE" != /* && "$REMOTE" != *..* ]] || exit 2
[[ "$(ssh -o BatchMode=yes "$HOST" hostname)" != "$(hostname)" ]] || exit 2
case "${1:-status}" in
 start)
  # Check before rsync: never change a recipe underneath an active film job.
  ssh "$HOST" "cd '$REMOTE' && flock -n .blender.lock true"
  rsync -az --exclude '__pycache__' "$ROOT/switchyard" "$ROOT/tools" "$ROOT/LICENSE" "$HOST:$REMOTE/"
  ssh "$HOST" "cd '$REMOTE' && rm -f .film-exit && (nohup bash -c 'HYPRUNE_REMOTE_BLENDER=1 flock .blender.lock blender -b --python-exit-code 1 -P switchyard/build.py -- --stage film; result=\$?; printf \"%s\\n\" \"\$result\" > .film-exit; exit \"\$result\"' > artifacts/remote-film.log 2>&1 < /dev/null & echo \$! > .film-pid)"
  ;;
 status)
  ssh "$HOST" "cd '$REMOTE' && if test -f .film-exit; then cat .film-exit; else echo RUNNING; fi; tail -n 4 artifacts/remote-film.log"
  ;;
 fetch)
  ssh "$HOST" "cd '$REMOTE' && test -f .film-exit && test \"\$(cat .film-exit)\" = 0"
  rsync -az --exclude 'film-frames' "$HOST:$REMOTE/artifacts/" "$ROOT/artifacts/"
  ;;
 *) echo 'usage: remote-film.sh start|status|fetch' >&2;exit 2;;
esac
