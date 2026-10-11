# SPDX-License-Identifier: MIT
"""Concept-render scenarios for the machines (render.py).

A scenario is what a runtime would show for one set of input values:
  states   {slot: palette id} ('*' for every states slot)    emission {slot: factor}
  speeds   {node: animation speed} ('*' default 1)           positions {node: 0..1}
  counts   {stack: n}     toggles {toggle: visible}         labels {label: text}
  items    [(track, fraction, token state)]                  effects [effect ids]
  flow     {track: speed in fractions per second} moves items in turntables
  caption  the input values, as the sheet prints them
"""
import copy

LINEUP = ['ci-conveyor', 'queue-stack', 'server-rack', 'deploy-lift', 'build-monitor']


def at_time(sc, t):
    """A turntable frame t seconds into a scenario: items advance along their tracks."""
    sc = copy.deepcopy(sc)
    flow = sc.get('flow', {})
    sc['items'] = [(tr, min(f + flow.get(tr, 0) * t, .999), st) for tr, f, st in sc.get('items', [])]
    return sc


def stages(*s):
    return {f'stage-{i}-lamp': v for i, v in enumerate(s, 1)}


def spinning(*s):
    return {'*': 0, **{f'stage-{i}-spinner': 1 for i, v in enumerate(s, 1) if v == 'running'}}


CONVEYOR_IDLE = {'states': stages('idle', 'idle', 'idle', 'idle'), 'speeds': {'*': 0}, 'labels': {'label-title': 'main'},
                 'caption': 'stage.1-4 = idle · queued 0 · progress 0'}
CONVEYOR_RUN = {'states': stages('ok', 'running', 'idle', 'idle'), 'speeds': spinning('ok', 'running', 'idle', 'idle'),
                'counts': {'waiting': 7, 'progress': 4}, 'labels': {'label-title': 'main #5112'},
                'items': [('track', .05, 'queued'), ('track', .2, 'running'), ('track', .36, 'running')], 'flow': {'track': .035},
                'caption': 'stage.1 ok · stage.2 running · queued 7 · progress 0.4 · jobStarted'}
CONVEYOR_OK = {'states': stages('ok', 'ok', 'ok', 'ok'), 'speeds': {'*': 0}, 'counts': {'progress': 10}, 'labels': {'label-title': 'main #5112'},
               'items': [('track', .965, 'ok')], 'effects': ['success-fx'],
               'caption': 'stage.1-4 = ok · progress 1 · jobPassed → success-fx'}
CONVEYOR_FAIL = {'states': stages('ok', 'ok', 'fail', 'idle'), 'speeds': {'*': 0}, 'counts': {'progress': 6, 'waiting': 3},
                 'labels': {'label-title': 'main #5113'}, 'items': [('reject', .92, 'fail'), ('track', .2, 'running')], 'effects': ['fail-fx'],
                 'caption': 'stage.3 fail · jobFailed → reject-in + fail-fx'}

SHEETS = {
    'ci-conveyor': {
        'token': True, 'lens': 40, 'hero_view': (-30, 15), 'callout_view': (-18, 24), 'margin': 1.06, 'callout_margin': 1.22,
        'hero': {**CONVEYOR_RUN, 't': 0.6},
        'states': [CONVEYOR_IDLE, CONVEYOR_RUN, CONVEYOR_OK, CONVEYOR_FAIL],
        'callout': CONVEYOR_RUN,
        'turntable': [CONVEYOR_IDLE, CONVEYOR_RUN, CONVEYOR_OK, CONVEYOR_FAIL],
    },
}
