# Companions

Optional companion characters (RFC-0010 companions amendment, object format 0.10): the
official library `com.hyprune.companions` ("Hyprune companions", `libraries/hyprune-companions.json`,
GitHub releases `hyprune-companions-v<version>`). Each is an RFC-0011 object directory with a
`character` trait (its own `idle`, `walk` and `run`) and a `companion` block (name, follow
distance, lines it says when you talk to it).

| Companion | Name | Size | Triangles | Bones | Walk / run |
| --- | --- | --- | --- | --- | --- |
| `neon-cyber-muse` | Muse | 2.97 MB | 8,000 | 27 | 1.37 / 4.53 m/s |
| `skeptical-ember` | Ember | 2.99 MB | 7,999 | 27 | 1.33 / 4.50 m/s |
| `starlit-stretch` | Starlit | 2.89 MB | 7,999 | 27 | 1.35 / 4.49 m/s |

All three share the `mixamo-v1` skeleton, so the shared clip library (RFC-0010 amendment
"Shared clip library") gives them every clip of an installed motion pack they lack: the
starter kit's `starter-motion` (styled walks and runs, idles, sit and stand, talk reactions)
and the library's own `companion-moves` (`motion/companion-moves/`: fourteen dances, role
`dance`). With dances bound, a companion offers Dance in its E menu (a chosen or random
dance) and now and then dances briefly while idle. The packs stay separate: a companion
library ships its own clips; the starter motions come with the starter kit.

Content: CC-BY-4.0, Hyprune contributors (see ATTRIBUTION.md and LICENSE). Scripts: MIT.
