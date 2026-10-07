#!/usr/bin/env node
// SPDX-License-Identifier: MIT
// npm install --prefix /tmp/hyprune-gltf-audit gltf-validator@2.0.0-dev.3.10
// GLTF_VALIDATOR_DIR=/tmp/hyprune-gltf-audit/node_modules node tools/validate-gltf.mjs dist/com.hyprune.switchyard
import fs from 'node:fs/promises';
import path from 'node:path';
import {createRequire} from 'node:module';
const require=createRequire(import.meta.url);
const validator=process.env.GLTF_VALIDATOR_DIR?require(path.join(process.env.GLTF_VALIDATOR_DIR,'gltf-validator')):require('gltf-validator');
const root=path.resolve(process.argv[2]);
const report=await validator.validateBytes(new Uint8Array(await fs.readFile(path.join(root,'scene.gltf'))),{uri:'scene.gltf',externalResourceFunction:async uri=>new Uint8Array(await fs.readFile(path.join(root,uri)))});
console.log(JSON.stringify(report,null,2));
process.exitCode=report.issues.numErrors?1:0;
