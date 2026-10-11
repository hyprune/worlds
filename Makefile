# SPDX-License-Identifier: MIT
SCHEMA_DIR ?= ../schema
# Review videos: HYPRUNE_VIDEO_DIR from the environment or ~/.config/hyprune/dev.env
# (tools/devenv.py warns and names its fallback when it isn't configured).
VIDEO_DIR ?= $(shell tools/devenv.py --videos)
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
	python3 tools/check-navmesh.py $(PACKAGE) --allow switchyard/navmesh-allow.json --output switchyard/reports/navmesh-check.json --svg switchyard/reports/navmesh.svg
gallery:
	cp artifacts/switchyard/world-switchyard.mp4 artifacts/switchyard/world-switchyard.json $(VIDEO_DIR)/
release: validate budgets
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
LUMEN_VERSION = $(shell python3 -c "import json; print(json.load(open('$(LUMEN_PACKAGE)/world.json'))['version'])")
LUMEN_REPORTS = lumen-reach/reports/any-angle-$(LUMEN_VERSION)
VISIBILITY_CORE ?= ../core
.PHONY: lumen-build lumen-validate lumen-nested lumen-tour lumen-release
LUMEN_PVS := artifacts/lumen-reach/pvs
lumen-build:
	python3 lumen-reach/materials/prepare.py
	./tools/remote-lumen.sh --areas $(LUMEN_AREAS) --samples 64
	python3 tools/derive-visibility.py $(LUMEN_PACKAGE) --output $(LUMEN_PVS) --in-place
lumen-validate:
	python3 tools/check-any-angle.py $(LUMEN_PACKAGE) --output $(LUMEN_REPORTS)/geometry-check.json
	python3 tools/check-sky.py $(LUMEN_PACKAGE) --poses lumen-reach/review-poses-v7.json --enclosures lumen-reach/enclosures.json --output $(LUMEN_REPORTS)/sky-check.json
	python3 tools/check-route-clearance.py $(LUMEN_PACKAGE) --output $(LUMEN_REPORTS)/route-clearance.json
	python3 tools/check-frames-signs.py $(LUMEN_PACKAGE) --output $(LUMEN_REPORTS)/frames-signs.json
	python3 tools/check-visibility.py $(LUMEN_PACKAGE) --spec $(LUMEN_PVS)/visibility.generated.json
	cp $(LUMEN_PVS)/report.json $(LUMEN_REPORTS)/derived-visibility.json
	node $(SCHEMA_DIR)/bin/validate.mjs world $(LUMEN_PACKAGE)/world.json - 0.6
	python3 tools/check-package.py $(LUMEN_PACKAGE) > lumen-reach/reports/package-check.json
	python3 tools/check-placement.py $(LUMEN_PACKAGE) --output lumen-reach/reports/placement-check.json
	python3 tools/check-walking.py $(LUMEN_PACKAGE) > lumen-reach/reports/walking-check.json
	python3 tools/check-navmesh.py $(LUMEN_PACKAGE) --allow lumen-reach/navmesh-allow.json --output $(LUMEN_REPORTS)/navmesh-check.json --svg $(LUMEN_REPORTS)/navmesh.svg
	python3 tools/check-coplanar.py $(LUMEN_PACKAGE) --emissive --fixtures $(LUMEN_PACKAGE)/fixture-audit.json > $(LUMEN_REPORTS)/emissive-check.json
	python3 -c "import json; assert json.load(open('$(LUMEN_PACKAGE)/decal-audit.json'))['status']=='PASS'"
lumen-nested:
	python3 tools/check-lumen-session.py

lumen-tour:
	python3 tools/check-lumen-session.py --record
# Since 0.8.0 the release package is the world format 0.7 build of the
# validated source package: KTX2 material textures, meshopt + quantised
# geometry, PNG lightmaps, every world.json index verified (verify.mjs).
LUMEN_RELEASE_PACKAGE := dist-07/com.hyprune.lumen-reach
OPTIMISE_CORE ?= ../core-optimise
LUMEN_PERF_BASELINE ?=
.PHONY: lumen-release-check lumen-perf-gate
lumen-release-check:
	node $(SCHEMA_DIR)/bin/validate.mjs world $(LUMEN_RELEASE_PACKAGE)/world.json - 0.7
	$(OPTIMISE_CORE)/build/hyprune-world-check $(LUMEN_RELEASE_PACKAGE) > $(LUMEN_REPORTS)/release-core-world-check.json
	cp $(LUMEN_RELEASE_PACKAGE).verify.json $(LUMEN_REPORTS)/release-verify.json
	python3 -c "import json; assert json.load(open('$(LUMEN_REPORTS)/release-verify.json'))['status']=='PASS'"
# Nested route capture vs the previous release (tools/check-perf-gate.py).
lumen-perf-gate:
	python3 tools/check-perf-gate.py $(LUMEN_RELEASE_PACKAGE) --core $(OPTIMISE_CORE) $(if $(LUMEN_PERF_BASELINE),--baseline-package $(LUMEN_PERF_BASELINE)) --output $(LUMEN_REPORTS)/perf-gate --record
lumen-release: lumen-validate lumen-optimize lumen-release-check lumen-perf-gate lumen-budgets
	mkdir -p artifacts/releases
	tar --sort=name --mtime='UTC 2026-10-09' --owner=0 --group=0 --numeric-owner -I zstd -cf artifacts/releases/com.hyprune.lumen-reach-$(LUMEN_VERSION).tar.zst -C dist-07 com.hyprune.lumen-reach
	sha256sum artifacts/releases/com.hyprune.lumen-reach-$(LUMEN_VERSION).tar.zst > artifacts/releases/LUMEN-SHA256SUMS

.PHONY: visibility-annotate visibility-validate visibility-nested
# Lumen Reach derives its regions in lumen-build (since 0.9.0).
visibility-annotate:
	python3 tools/world_visibility.py $(PACKAGE)
visibility-validate:
	python3 tools/check-visibility.py $(LUMEN_PACKAGE) --spec $(LUMEN_PVS)/visibility.generated.json
	python3 tools/check-visibility.py $(PACKAGE)
visibility-nested:
	HYPRUNE_NESTED_4K=1 python3 tools/check-visibility-session.py --core $(VISIBILITY_CORE)

# glTF-Transform inspect() budgets (triangles, draws, GPU MiB incl. mips) for
# the release record. LUMEN_BASELINE=<previous package dir> adds deltas.
LUMEN_BASELINE ?=
.PHONY: gltf-deps budgets lumen-budgets
gltf-deps:
	npm ci --prefix tools/gltf --no-audit --no-fund
budgets:
	node tools/gltf/budgets.mjs $(PACKAGE) --output switchyard/reports/budgets.json > /dev/null
lumen-budgets:
	node tools/gltf/budgets.mjs $(LUMEN_RELEASE_PACKAGE) $(if $(LUMEN_BASELINE),--baseline $(LUMEN_BASELINE)) --output $(LUMEN_REPORTS)/budgets.json > /dev/null

# Recast/Detour (recast-navigation-js, pinned by package-lock.json) for check-navmesh.
.PHONY: navmesh-deps navmesh-test
navmesh-deps:
	npm ci --prefix tools/navmesh --no-audit --no-fund
navmesh-test:
	python3 -m unittest tests/test_navmesh_check.py tests/test_devenv.py

# World format 0.7 optimisation (KHR_texture_basisu KTX2 + EXT_meshopt_compression
# + KHR_mesh_quantization) on the bake host. Lumen's release build since 0.8.0;
# Switchyard's stays behind HYPRUNE_FORMAT_07=1. The Python checks read the
# source package; verify.mjs proves the optimised copy equivalent (dist-07/).
.PHONY: lumen-optimize optimize
lumen-optimize:
	tools/remote-optimize.sh $(LUMEN_PACKAGE) $(LUMEN_RELEASE_PACKAGE)
optimize:
	@[ "$(HYPRUNE_FORMAT_07)" = 1 ] || { echo 'world format 0.7 is not merged yet; HYPRUNE_FORMAT_07=1 builds a test package in dist-07/' >&2; exit 2; }
	tools/remote-optimize.sh $(PACKAGE) dist-07/com.hyprune.switchyard
	node tools/gltf/budgets.mjs dist-07/com.hyprune.switchyard --baseline $(PACKAGE) --output dist-07/com.hyprune.switchyard.budgets.json > /dev/null
