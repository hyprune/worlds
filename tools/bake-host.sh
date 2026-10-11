# SPDX-License-Identifier: MIT
# Sourced by tools/remote-*.sh (needs ROOT). HYPRUNE_BAKE_HOST comes from the
# environment or ~/.config/hyprune/dev.env: an SSH host with Blender, or "local"
# on the bake host itself. There is no default: Blender never runs by accident on
# a machine that isn't the bake host.
HOST="$("$ROOT/tools/devenv.py" HYPRUNE_BAKE_HOST | cut -d= -f2-)"
[[ -n "$HOST" ]] || { echo 'Set HYPRUNE_BAKE_HOST (environment or ~/.config/hyprune/dev.env): an SSH bake host, or "local" on the bake host itself' >&2; exit 2; }
BAKE_LOCAL=; [[ "$HOST" == local ]] && BAKE_LOCAL=1
if [[ -z "$BAKE_LOCAL" ]]; then
  [[ "$HOST" != localhost && "$HOST" != 127.* && "$HOST" != ::1 ]] || { echo 'A remote bake host is required (HYPRUNE_BAKE_HOST=local only on the bake host itself)' >&2; exit 2; }
  [[ "$(ssh -o BatchMode=yes "$HOST" hostname)" != "$(hostname)" ]] || { echo 'The bake host resolves to this machine: set HYPRUNE_BAKE_HOST=local here instead' >&2; exit 2; }
fi
# on_host CMD: run a shell command on the bake host, from its home directory (like ssh).
on_host() { if [[ -n "$BAKE_LOCAL" ]]; then (cd ~ && bash -c "$1"); else ssh -o BatchMode=yes "$HOST" "$1"; fi; }
# on_host_script: run a bash script from stdin there.
on_host_script() { if [[ -n "$BAKE_LOCAL" ]]; then (cd ~ && bash -s); else ssh -o BatchMode=yes "$HOST" bash -s; fi; }
# host_path PATH: an rsync location for PATH (relative to the bake host's home).
host_path() { if [[ -n "$BAKE_LOCAL" ]]; then printf '%s/%s' "$HOME" "$1"; else printf '%s:%s' "$HOST" "$1"; fi; }
