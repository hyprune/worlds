# Original Switchyard material library

The eight source PNGs were generated specifically for Hyprune using the built-in image generation tool. Each has its own prompt/provenance entry in `generation.json`; content is CC-BY-4.0, Hyprune contributors. No third-party or ripped textures are included.

Run `python3 switchyard/materials/prepare.py` from the repo root. It needs Pillow and NumPy and does not run Blender. It emits original albedo, OpenGL normal and ORM tiles, offset views and a 2×2-repeat contact sheet in ignored `tiles/`. Periodic Poisson boundary healing removes low-frequency seam mismatch; narrow edge collars match opposite boundary pixels exactly. Wrap-safe derivatives preserve seamless normal/roughness edges. Review repeat images as well as the numerical edge report: matching boundary pixels alone cannot prove a visually convincing repeat.

`transit-trim-albedo.png` contains eight 112px bands separated by 8px gutters; `transit-trim.json` records top-origin atlas rectangles. Blender's bottom-origin V coordinate is inverted when mapping the signage's brass band. UV0 carries real-world tiling; UV1 stays independent for lighting. Masters are retained in git because image generation itself is not reproducible. All derived maps/atlases are rebuildable and ignored.
