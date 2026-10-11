# SPDX-License-Identifier: MIT
"""job-token: the item that rides machine tracks (RFC-0011 mover, item: true).

A small timber crate with dark corner bands and a glowing band whose palette
shows the job's state (queued, running, ok, fail). Origin at the base centre,
front +Z (the direction of travel).

    make machines        (Blender on the bake host)
"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import kit
from kit import Part

ID = 'job-token'
W, H = .30, .22


def main():
    kit.reset()
    body = Part('crate')
    body.box('timber', (0, 0, H / 2), (W, W, H), bevel=.016)
    for sx in (-1, 1):
        for sy in (-1, 1):
            body.box('metal-black', (sx * (W / 2 - .012), sy * (W / 2 - .012), H / 2), (.032, .032, H + .004))
    body.box('ivory', (0, -W / 2 - .003, H * .78), (.08, .006, .02))   # a front mark: the travel direction
    body.finish()
    kit.slot_material('band', 'token')
    band = Part('band', (0, 0, H * .45))
    band.box('band', (0, 0, H * .45), (W + .012, W + .012, .045))
    band.finish()
    proxy = None
    kit.recentre()
    m = kit.base_manifest(ID, 'Job token', 'A small crate that rides machine tracks; its band shows the job state.', ['item', 'job', 'crate'])
    m['traits'] = {'mover': {'speed': .6, 'accel': 1, 'pitch': 'follow', 'offset': [0, 0, 0], 'item': True}}
    m['slots'] = {'states': [kit.states_slot('band')]}
    kit.export(kit.out_dir(ID), m, proxy=proxy)


main()
