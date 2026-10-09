# SPDX-License-Identifier: MIT
SCHEMA_DIR ?= ../schema
GALLERY_DIR ?= ../../rick-the-alien/worldshell-gallery
VERSION := $(shell python3 -c "import json; print(json.load(open('switchyard/world.spec.json'))['version'])")
PACKAGE := dist/com.hyprune.switchyard
.PHONY: textures preview build stills film validate gallery release nested gltf-check compare engine-film film-start film-status film-fetch
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
	python3 tools/check-visibility.py $(PACKAGE)
	node $(SCHEMA_DIR)/bin/validate.mjs world $(PACKAGE)/world.json - 0.5
	python3 tools/check-package.py $(PACKAGE)
	python3 tools/check-lettering.py
	python3 tools/check-texel-density.py $(PACKAGE)
	python3 tools/check-coplanar.py $(PACKAGE)
	python3 tools/check-routes.py $(PACKAGE) artifacts/switchyard/spatial-authoring.json
gallery:
	mkdir -p $(GALLERY_DIR)/videos
	cp artifacts/switchyard/world-switchyard.mp4 artifacts/switchyard/world-switchyard.json $(GALLERY_DIR)/videos/
release: validate
	mkdir -p artifacts/releases
	tar --sort=name --mtime='UTC 2026-10-09' --owner=0 --group=0 --numeric-owner -I zstd -cf artifacts/releases/com.hyprune.switchyard-$(VERSION).tar.zst -C dist com.hyprune.switchyard
	sha256sum artifacts/releases/com.hyprune.switchyard-$(VERSION).tar.zst > artifacts/releases/SHA256SUMS

nested:
	python3 tools/check-nested.py
gltf-check:
	node tools/validate-gltf.mjs $(PACKAGE)

compare:
	python3 tools/compare-renders.py
engine-film:
	python3 tools/check-nested.py --record
film-start:
	./tools/remote-film.sh start
film-status:
	./tools/remote-film.sh status
film-fetch:
	./tools/remote-film.sh fetch

LUMEN_PACKAGE := dist/com.hyprune.lumen-reach
LUMEN_AREAS ?= 4
VISIBILITY_CORE ?= ../core
.PHONY: lumen-build lumen-validate lumen-nested lumen-tour lumen-release
lumen-build:
	python3 lumen-reach/materials/prepare.py
	./tools/remote-lumen.sh --areas $(LUMEN_AREAS) --samples 64
lumen-validate:
	python3 tools/check-visibility.py $(LUMEN_PACKAGE)
	node $(SCHEMA_DIR)/bin/validate.mjs world $(LUMEN_PACKAGE)/world.json - 0.5
	python3 tools/check-package.py $(LUMEN_PACKAGE) > lumen-reach/reports/package-check.json
	python3 tools/check-placement.py $(LUMEN_PACKAGE) --output lumen-reach/reports/placement-check.json
	python3 tools/check-walking.py $(LUMEN_PACKAGE) > lumen-reach/reports/walking-check.json
	python3 tools/check-coplanar.py $(LUMEN_PACKAGE) --emissive --fixtures $(LUMEN_PACKAGE)/fixture-audit.json > lumen-reach/reports/visibility-0.6.1/emissive-check.json
	python3 -c "import json; assert json.load(open('$(LUMEN_PACKAGE)/decal-audit.json'))['status']=='PASS'"
lumen-nested:
	python3 tools/check-lumen-session.py

lumen-tour:
	python3 tools/check-lumen-session.py --record
lumen-release: lumen-validate
	mkdir -p artifacts/releases
	tar --sort=name --mtime='UTC 2026-10-09' --owner=0 --group=0 --numeric-owner -I zstd -cf artifacts/releases/com.hyprune.lumen-reach-0.6.1.tar.zst -C dist com.hyprune.lumen-reach
	sha256sum artifacts/releases/com.hyprune.lumen-reach-0.6.1.tar.zst > artifacts/releases/LUMEN-SHA256SUMS

.PHONY: visibility-annotate visibility-validate visibility-nested
visibility-annotate:
	python3 tools/world_visibility.py $(LUMEN_PACKAGE)
	python3 tools/world_visibility.py $(PACKAGE)
visibility-validate:
	python3 tools/check-visibility.py $(LUMEN_PACKAGE)
	python3 tools/check-visibility.py $(PACKAGE)
visibility-nested:
	HYPRUNE_NESTED_4K=1 python3 tools/check-visibility-session.py --core $(VISIBILITY_CORE)
