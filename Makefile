# SPDX-License-Identifier: MIT
SCHEMA_DIR ?= ../schema
# Review videos: HYPRUNE_VIDEO_DIR from the environment or ~/.config/hyprune/dev.env
# (tools/devenv.py warns and names its fallback when it isn't configured).
VIDEO_DIR ?= $(shell tools/devenv.py --videos)
VERSION := $(shell python3 -c "import json; print(json.load(open('switchyard/world.spec.json'))['version'])")
PACKAGE := dist/com.hyprune.switchyard
.PHONY: machines machines-install objects objects-check textures preview build blueprint stills film validate gallery release nested gltf-check compare engine-film film-start film-status film-fetch
textures:
	python3 switchyard/materials/prepare.py
# Reusable world objects (world format 0.8 objectAssets) in dist/objects/<id>/.
# Each is an RFC-0011 object directory: make objects renders its thumbnail, checks it with
# the shared validator (tools/object-check) and installs it into objects/<id>/.
objects:
	HYPRUNE_BAKE_DIR=hyprune-bake/worlds-objects HYPRUNE_BAKE_PROJECT=objects ./tools/remote-blender.sh -b --python-exit-code 1 -P objects/armillary/build.py
	HYPRUNE_BAKE_DIR=hyprune-bake/worlds-objects HYPRUNE_BAKE_PROJECT=objects ./tools/remote-blender.sh -b --factory-startup --python-exit-code 1 -P tools/object/thumbnail.py -- dist/objects/armillary/armillary.gltf dist/objects/armillary/thumbnail.png
	SCHEMA_DIR=$(SCHEMA_DIR) ./tools/object-check dist/objects/armillary
	cp dist/objects/armillary/armillary.gltf dist/objects/armillary/armillary.bin dist/objects/armillary/object.json dist/objects/armillary/thumbnail.png objects/armillary/
# Every committed object directory (objects/, objects/machines/, characters/).
objects-check:
	SCHEMA_DIR=$(SCHEMA_DIR) ./tools/object-check objects/armillary objects/machines/*/ characters/resident-*/
# Machine objects (RFC-0011/0013 drafts): build on the bake host into
# dist/objects/machines/<id>/, then optimise (KTX2 + meshopt) into objects/machines/<id>/.
MACHINES := job-token ci-conveyor queue-stack server-rack deploy-lift build-monitor
machines:
	test -f lumen-reach/materials/tiles/wood-albedo.png || python3 lumen-reach/materials/prepare.py
	for m in $(MACHINES); do HYPRUNE_BAKE_DIR=hyprune-bake/worlds-machines HYPRUNE_BAKE_PROJECT=objects ./tools/remote-blender.sh -b --python-exit-code 1 -P objects/machines/$$m/build.py || exit 1; done
machines-install:
	objects/machines/optimise.sh $(MACHINES)
preview: textures
	./tools/remote-blender.sh -b --python-exit-code 1 -P switchyard/build.py -- --stage preview
build: textures
	./tools/remote-blender.sh -b --python-exit-code 1 -P switchyard/build.py -- --stage build
	$(MAKE) blueprint
# Per-level blueprint plans (com.hyprune.blueprint) from the built package;
# needs `make navmesh-deps`. Report and copies in artifacts/.
blueprint:
	python3 tools/derive-blueprint.py $(PACKAGE) --in-place --output artifacts/switchyard/blueprint > /dev/null
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
	python3 tools/check-blueprint.py $(PACKAGE) --output switchyard/reports/blueprint-check.json > /dev/null
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
LUMEN_BLUEPRINT := artifacts/lumen-reach/blueprint
lumen-build:
	python3 lumen-reach/materials/prepare.py
	HYPRUNE_BAKE_DIR=hyprune-bake/worlds-lumen-reach HYPRUNE_BAKE_PROJECT=objects ./tools/remote-blender.sh -b --python-exit-code 1 -P objects/armillary/build.py
	./tools/remote-lumen.sh --areas $(LUMEN_AREAS) --samples 64
	python3 tools/derive-visibility.py $(LUMEN_PACKAGE) --output $(LUMEN_PVS) --in-place
	python3 tools/derive-blueprint.py $(LUMEN_PACKAGE) --in-place --output $(LUMEN_BLUEPRINT) > /dev/null
lumen-validate:
	python3 tools/check-any-angle.py $(LUMEN_PACKAGE) --output $(LUMEN_REPORTS)/geometry-check.json
	python3 tools/check-sky.py $(LUMEN_PACKAGE) --poses lumen-reach/review-poses-v7.json --enclosures lumen-reach/enclosures.json --output $(LUMEN_REPORTS)/sky-check.json
	python3 tools/check-route-clearance.py $(LUMEN_PACKAGE) --output $(LUMEN_REPORTS)/route-clearance.json
	python3 tools/check-frames-signs.py $(LUMEN_PACKAGE) --output $(LUMEN_REPORTS)/frames-signs.json
	python3 tools/check-visibility.py $(LUMEN_PACKAGE) --spec $(LUMEN_PVS)/visibility.generated.json
	cp $(LUMEN_PVS)/report.json $(LUMEN_REPORTS)/derived-visibility.json
	node $(SCHEMA_DIR)/bin/validate.mjs world $(LUMEN_PACKAGE)/world.json - 0.9
	python3 tools/check-residents.py $(LUMEN_PACKAGE) $(if $(NPC_CHECK),--npc-check $(NPC_CHECK)) --output $(LUMEN_REPORTS)/residents-check.json
	python3 tools/check-package.py $(LUMEN_PACKAGE) > lumen-reach/reports/package-check.json
	python3 tools/check-placement.py $(LUMEN_PACKAGE) --output lumen-reach/reports/placement-check.json
	python3 tools/check-walking.py $(LUMEN_PACKAGE) > lumen-reach/reports/walking-check.json
	python3 tools/check-navmesh.py $(LUMEN_PACKAGE) --allow lumen-reach/navmesh-allow.json --output $(LUMEN_REPORTS)/navmesh-check.json --svg $(LUMEN_REPORTS)/navmesh.svg
	python3 tools/check-blueprint.py $(LUMEN_PACKAGE) --output $(LUMEN_REPORTS)/blueprint-check.json > /dev/null
	python3 tools/check-coplanar.py $(LUMEN_PACKAGE) --emissive --fixtures $(LUMEN_PACKAGE)/fixture-audit.json > $(LUMEN_REPORTS)/emissive-check.json
	python3 -c "import json; assert json.load(open('$(LUMEN_PACKAGE)/decal-audit.json'))['status']=='PASS'"
lumen-nested:
	python3 tools/check-lumen-session.py

lumen-tour:
	python3 tools/check-lumen-session.py --record
# Since 0.8.0 the release package is the optimised (world format 0.7 assets) build of the
# validated source package, format 0.8 since 0.10.0 (placed objects): KTX2 material textures, meshopt + quantised
# geometry, PNG lightmaps, every world.json index verified (verify.mjs).
LUMEN_RELEASE_PACKAGE := dist-07/com.hyprune.lumen-reach
OPTIMISE_CORE ?= ../core-optimise
LUMEN_PERF_BASELINE ?=
# Residents (world format 0.9): core's character checker measures each resident's seat fit.
NPC_CHECK ?= $(wildcard $(OPTIMISE_CORE)/build/hyprune-npc-check)
.PHONY: lumen-release-check lumen-perf-gate lumen-residents-session
lumen-release-check:
	node $(SCHEMA_DIR)/bin/validate.mjs world $(LUMEN_RELEASE_PACKAGE)/world.json - 0.9
	python3 tools/check-residents.py $(LUMEN_RELEASE_PACKAGE) $(if $(NPC_CHECK),--npc-check $(NPC_CHECK)) --output $(LUMEN_REPORTS)/release-residents-check.json
	python3 tools/check-blueprint.py $(LUMEN_RELEASE_PACKAGE) > $(LUMEN_REPORTS)/release-blueprint-check.json
	$(OPTIMISE_CORE)/build/hyprune-world-check $(LUMEN_RELEASE_PACKAGE) > $(LUMEN_REPORTS)/release-core-world-check.json
	cp $(LUMEN_RELEASE_PACKAGE).verify.json $(LUMEN_REPORTS)/release-verify.json
	python3 -c "import json; assert json.load(open('$(LUMEN_REPORTS)/release-verify.json'))['status']=='PASS'"
# Nested route capture vs the previous release (tools/check-perf-gate.py).
lumen-perf-gate:
	python3 tools/check-perf-gate.py $(LUMEN_RELEASE_PACKAGE) --core $(OPTIMISE_CORE) $(if $(LUMEN_PERF_BASELINE),--baseline-package $(LUMEN_PERF_BASELINE)) --output $(LUMEN_REPORTS)/perf-gate --record
# Nested resident check (walk, sit, stops, say, waypoint, guide, frames out of view).
lumen-residents-session:
	$(OPTIMISE_CORE)/dev/nested/run.sh $(abspath tools/check-residents-session.py) --core $(abspath $(OPTIMISE_CORE)) --package $(abspath $(LUMEN_RELEASE_PACKAGE)) --output $(abspath $(LUMEN_REPORTS)/residents-session)
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
.PHONY: navmesh-deps navmesh-test blueprint-test
navmesh-deps:
	npm ci --prefix tools/navmesh --no-audit --no-fund
navmesh-test:
	python3 -m unittest tests/test_navmesh_check.py tests/test_devenv.py
# derive-blueprint.py / check-blueprint.py on synthetic packages (navmesh-deps).
blueprint-test:
	python3 -m unittest tests/test_blueprint.py

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

# Machine Yard: the test world for live machines (not part of build or release).
YARD_PACKAGE := dist/com.hyprune.machine-yard
YARD_BLENDER := HYPRUNE_BAKE_DIR=hyprune-bake/worlds-machine-yard HYPRUNE_BAKE_PROJECT=machine-yard ./tools/remote-blender.sh -b --python-exit-code 1 -P machine-yard/build.py
YARD_CORE ?= ../core
# The machines prototype's checker (a core build with HYPRUNE_MACHINES_PROTOTYPE support), if present.
YARD_MACHINES_CHECK ?= $(YARD_CORE)/build/machines-check
.PHONY: machine-yard machine-yard-stills machine-yard-check
YARD_MACHINES := ci-conveyor queue-stack server-rack deploy-lift build-monitor job-token
machine-yard:
	python3 lumen-reach/materials/prepare.py
	node machine-yard/decode-objects.mjs objects/machines machine-yard/import $(YARD_MACHINES)
	$(YARD_BLENDER) -- --stage build
machine-yard-stills:
	$(YARD_BLENDER) -- --stage stills
machine-yard-check:
	node $(SCHEMA_DIR)/bin/validate.mjs world $(YARD_PACKAGE)/world.json - 0.8
	$(YARD_CORE)/build/hyprune-world-check $(YARD_PACKAGE) > artifacts/machine-yard/world-check.json
	@if [ -x "$(YARD_MACHINES_CHECK)" ]; then $(YARD_MACHINES_CHECK) $(YARD_PACKAGE) $(YARD_PACKAGE)/machines.bindings.json > artifacts/machine-yard/machines-check.json; fi
