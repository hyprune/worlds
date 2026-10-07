# Lumen Reach

Hyprune's connected release world. Sun Court, Array Hall, Rime Vault and Signal
Rise are four workspace homes; each owns one wall workspace and its tool mounts.
See IDENTITY.md for the settlement's original language and symbols.

Build ONLY on the remote bake host:

```sh
python3 lumen-reach/materials/prepare.py
./tools/remote-lumen.sh --areas 1 --samples 64
```

`--areas 1` produces the first milestone; 2/3/4 include successive homes and
connecting paths. Source geometry is original procedural Blender Python.
Generated material masters/prompts/provenance are committed; distributable
scenes, PBR derivatives, bake atlases, renders and recordings remain in ignored
`dist/` and `artifacts/`. The dedicated runner refuses the local machine.
The test world's source and entrypoint remain intact.

World format 0.2, standard tiled UV0 and independent normalized UV1 irradiance.
Physical mount frames and the optional `com.hyprune.lumen-reach.mounts` extension
encode area/slot ownership. Free-placement volumes are declared in the optional
placement extension and continuously swept against exported visual triangles.
Unknown extensions are optional. Static screen UI is labeled authored artwork;
live applications come from core's actual window capture.
