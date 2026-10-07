# SPDX-License-Identifier: MIT
SCHEMA_DIR ?= ../schema
GALLERY_DIR ?= ../../rick-the-alien/worldshell-gallery
PACKAGE := dist/com.hyprune.switchyard
.PHONY: textures preview build stills film validate gallery release nested gltf-check
textures:
	python3 switchyard/materials/prepare.py
preview: textures
	./tools/remote-blender.sh -b --python-exit-code 1 -P switchyard/build.py -- --stage preview
build: textures
	./tools/remote-blender.sh -b --python-exit-code 1 -P switchyard/build.py -- --stage build
stills:
	./tools/remote-blender.sh -b --python-exit-code 1 -P switchyard/build.py -- --stage stills
film:
	./tools/remote-blender.sh -b --python-exit-code 1 -P switchyard/build.py -- --stage film
validate:
	node $(SCHEMA_DIR)/bin/validate.mjs world $(PACKAGE)/world.json
	python3 tools/check-package.py $(PACKAGE)
	python3 tools/check-coplanar.py $(PACKAGE)
	python3 tools/check-routes.py $(PACKAGE) artifacts/switchyard/spatial-authoring.json
gallery:
	mkdir -p $(GALLERY_DIR)/videos
	cp artifacts/switchyard/world-switchyard.mp4 artifacts/switchyard/world-switchyard.json $(GALLERY_DIR)/videos/
release: validate
	mkdir -p artifacts/releases
	tar --sort=name --mtime='UTC 2026-10-07' --owner=0 --group=0 --numeric-owner -I zstd -cf artifacts/releases/com.hyprune.switchyard-0.1.0.tar.zst -C dist com.hyprune.switchyard
	sha256sum artifacts/releases/com.hyprune.switchyard-0.1.0.tar.zst > artifacts/releases/SHA256SUMS

nested:
	python3 tools/check-nested.py
gltf-check:
	node tools/validate-gltf.mjs $(PACKAGE)
