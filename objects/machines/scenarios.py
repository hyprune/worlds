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
                 'view': (145, 24),
                 'caption': 'stage.3 fail · jobFailed → reject-in + fail-fx'}

SHEETS = {
    'ci-conveyor': {
        'token': True, 'lens': 40, 'hero_view': (-30, 15), 'callout_view': (-18, 24), 'margin': 1.06, 'callout_margin': 1.1,
        'tile': (1500, 820), 'callout_res': (1700, 1100),
        'hero': {**CONVEYOR_RUN, 't': 0.6},
        'states': [CONVEYOR_IDLE, CONVEYOR_RUN, CONVEYOR_OK, CONVEYOR_FAIL],
        'callout': CONVEYOR_RUN,
        'turntable': [CONVEYOR_IDLE, CONVEYOR_RUN, CONVEYOR_OK, CONVEYOR_FAIL],
    },
}


def queue(depth, level, name='ingest'):
    import math
    return {'states': {'level': level}, 'counts': {'crates': min(48, math.ceil(depth / 10))}, 'toggles': {'alarm-flag': level != 'ok'},
            'labels': {'label-count': f'{depth}', 'label-name': name}, 'caption': f'depth {depth} · level {level}'}


QUEUE = [queue(0, 'ok'), queue(64, 'ok'), queue(230, 'warn'), queue(500, 'fail')]


def rack(health, load, name='rack-a'):
    h = {f'unit-{i}-light': s for i, s in enumerate(health, 1)}
    off = all(s == 'off' for s in health)
    return {'states': h, 'speeds': {'*': 0 if off else .15 + load * 3.85}, 'labels': {'label-name': name},
            'caption': ('health.1-8 off' if off else 'health ' + ' '.join(s[0] for s in health)) + f' · load {load}'}


RACK = [rack(['off'] * 8, 0), rack(['ok'] * 8, .25), rack(['ok', 'ok', 'warn', 'ok', 'ok', 'fail', 'ok', 'ok'], .7),
        rack(['ok', 'ok', 'ok', 'ok', 'warn', 'ok', 'ok', 'ok'], 1.0)]


def lift(status, progress, env='production'):
    order = ['queued', 'building', 'rolling', 'live']
    st = {}
    for k, p in enumerate(order, 1):
        if status == 'idle':
            st[f'phase-lamp-{k}'] = 'off'
        elif status == 'failed':
            st[f'phase-lamp-{k}'] = 'fail'
        else:
            j = order.index(status) + 1
            st[f'phase-lamp-{k}'] = 'active' if j == k else ('done' if j > k else 'off')
    st['beacon'] = {'queued': 'active', 'building': 'active', 'rolling': 'active', 'live': 'live', 'failed': 'fail'}.get(status, 'off')
    return {'states': st, 'positions': {'platform': progress}, 'toggles': {'gate': status != 'live'},
            'speeds': {'*': 1 if status in ('building', 'rolling') else (2 if status == 'failed' else 0)},
            'labels': {'label-env': env}, 'effects': ['burst-fx'] if status == 'live' else [],
            'caption': f'status {status} · progress {progress}'}


LIFT = [lift('queued', 0), lift('building', .33), lift('rolling', .66), lift('live', 1.0), lift('failed', .45)]


def monitor(status, progress=0.0):
    return {'states': {'face': status, 'ring-glow': status}, 'emission': {'ring-glow': .35 + progress * 1.25},
            'speeds': {'*': 1 if status == 'running' else 0},
            'toggles': {'glyph-ok': status == 'ok', 'glyph-fail': status == 'fail', 'glyph-run': status == 'running'},
            'effects': ['burst-fx'] if status == 'ok' else [], 'caption': f'status {status}' + (f' · progress {progress}' if status == 'running' else '')}


MONITOR = [monitor('idle'), monitor('running', .5), monitor('ok', 1.0), monitor('fail')]

SHEETS.update({
    'queue-stack': {'tile': (1000, 950), 'hero': QUEUE[2], 'states': QUEUE, 'callout': QUEUE[2], 'turntable': QUEUE, 'hero_view': (-30, 14), 'callout_view': (-22, 16)},
    'server-rack': {'tile': (900, 1100), 'hero': RACK[2], 'states': RACK, 'callout': RACK[2], 'turntable': RACK, 'hero_view': (-34, 10), 'callout_view': (-18, 10),
                    'lens': 50},
    'deploy-lift': {'tile': (900, 1200), 'hero': lift('rolling', .66), 'states': LIFT, 'callout': lift('building', .33), 'turntable': LIFT, 'hero_view': (-32, 12),
                    'callout_view': (-24, 12)},
    'build-monitor': {'tile': (900, 1000), 'hero': monitor('running', .6), 'states': MONITOR, 'callout': monitor('running', .6), 'turntable': MONITOR,
                      'hero_view': (-30, 8), 'callout_view': (-20, 8), 'lens': 50},
})

TOKEN = [{'states': {'band': s}, 'caption': f'band {s}'} for s in ('queued', 'running', 'ok', 'fail')]
SHEETS['job-token'] = {'hero': TOKEN[1], 'states': TOKEN, 'callout': TOKEN[1], 'turntable': TOKEN, 'hero_view': (-35, 25), 'lens': 70, 'margin': 1.3}
