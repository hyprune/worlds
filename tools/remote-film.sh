#!/usr/bin/env bash
# SPDX-License-Identifier: MIT
# Resumable film job survives SSH interruption. Blender stays on the bake host.
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
REMOTE="${HYPRUNE_BAKE_DIR:-hyprune-bake/worlds-switchyard}"
[[ "$REMOTE" =~ ^[a-zA-Z0-9_./-]+$ && "$REMOTE" != /* && "$REMOTE" != *..* ]] || exit 2
source "$ROOT/tools/bake-host.sh"
case "${1:-status}" in
 start)
  # Check before rsync: never change a recipe underneath an active film job.
  on_host "cd '$REMOTE' && flock -n .blender.lock true"
  rsync -az --exclude '__pycache__' --exclude node_modules "$ROOT/switchyard" "$ROOT/tools" "$ROOT/LICENSE" "$(host_path "$REMOTE/")"
  on_host "cd '$REMOTE' && rm -f .film-exit && (nohup bash -c 'HYPRUNE_REMOTE_BLENDER=1 flock .blender.lock blender -b --python-exit-code 1 -P switchyard/build.py -- --stage film; result=\$?; printf \"%s\\n\" \"\$result\" > .film-exit; exit \"\$result\"' > artifacts/remote-film.log 2>&1 < /dev/null & echo \$! > .film-pid)"
  ;;
 status)
  on_host "cd '$REMOTE' && if test -f .film-exit; then cat .film-exit; else echo RUNNING; fi; tail -n 4 artifacts/remote-film.log"
  ;;
 fetch)
  on_host "cd '$REMOTE' && test -f .film-exit && test \"\$(cat .film-exit)\" = 0"
  rsync -az --exclude 'film-frames' "$(host_path "$REMOTE/artifacts/")" "$ROOT/artifacts/"
  ;;
 *) echo 'usage: remote-film.sh start|status|fetch' >&2;exit 2;;
esac
