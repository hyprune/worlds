# Machine Yard demo shots

Camera keyframes and stills for the machines prototype's demo recorder in core
(`dev/machines/demo.py`, run by `dev/nested/run.sh --machines`; nested only).

| File | Use |
| --- | --- |
| `yard-walk.json` | An 86 s walk past all five machines (`keys` with look-at `target`s). |
| `ci-closeup.json` | 30 s along the CI conveyor. |
| `sheet-shots.json` + `sheet.bindings.json` | Stills of the build monitor and the CI conveyor in each state. The bindings file rebinds those two machines to a source the recorder publishes itself (`org.hyprune.nested.sheet`), so each state is set exactly. |

From a core checkout, with the built package in `PKG`:

```sh
RA=$(( $(date +%s) + 90 ))
ENV=$(dev/machines/plan-shifts.py $RA '{"queue": 20, "deploy": 66, "build": 6, "ci": 55}')
HYPRUNE_NESTED_4K=1 HYPRUNE_MACHINES_RECORD_AT=$RA HYPRUNE_MACHINES_SIM_ENV="$ENV" \
HYPRUNE_MACHINES_WORLD=$PKG HYPRUNE_MACHINES_DEMO=dev/machines/demo.py \
HYPRUNE_MACHINES_SHOTS=<this dir>/yard-walk.json HYPRUNE_MACHINES_OUT=/tmp/yard.mkv dev/nested/run.sh --machines
```

`plan-shifts.py` slides each simulator's story (`MACHINES_SIM_SHIFT`) so the queue
backlog, the lift's rise, a build success and a CI failure land while the camera is
at those machines. Stills: `HYPRUNE_MACHINES_BINDINGS=<this dir>/sheet.bindings.json
HYPRUNE_MACHINES_SHOTS=<this dir>/sheet-shots.json HYPRUNE_MACHINES_STILLS=<out dir>`.
