# Motion packs

Shared clip library (RFC-0010 amendment "Shared clip library"): clips on the `mixamo-v1`
skeleton that every character on it can play. Each pack is `motion/<id>/` with `motion.json`
(motion format 0.1, `@hyprune/schema` `motion/v0.1`) and clips-only glTF rigs (a skeleton and
its animations, no mesh). Core binds a pack's clips to a character at load, retargeted through
both rest poses with the hips and the clip speed scaled by hip height; a character's own clips
win. Packs come from the world package, installed libraries and the user's motion folder.

| Pack | Library | Clips | Size |
| --- | --- | --- | --- |
| `starter-motion` | `com.hyprune.starter` | 30: idle and walk/run, styled walks (confident, groovy, stumble, stylish, swing, stroll, stagger), runs (steady, fast, loose), idles (fidget, calm x3, preen, sway x3), wave (+ big), sit, seated idle (+ clap), stand (+ quick), talk reactions (shrug, puzzled) | 3.1 MB |

Built by `tools/gltf/motion-pack.mjs` from the characters' source exports (30 fps, hips-only
translation, travel removed; walk and run speeds from the planted feet; the sit from the end of
a walk-to-sit take, the seated idle its held end pose). Sources and their specs are not part of
this repository. Content: CC-BY-4.0, see each `motion.json` (attribution) and LICENSE.
