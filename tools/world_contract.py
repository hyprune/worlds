# SPDX-License-Identifier: MIT
"""Workspace homes, mounts and placement zones from either world.json shape:
canonical (areas[], anchors[].mount, dataObjects, placementZones; Lumen Reach
>= 0.9.0) or the legacy com.hyprune.lumen-reach.mounts/.placement extensions.
Rows keep the legacy shape the checks were written against:
{anchorId, areaId, workspaceSlot, mountType, role: mounted-workspace|tool|data,
clearanceMeters}. RFC-0004 approach depths: 16 m primary standback, 4 m tool."""

ROLE = {'mounted-workspace': 'mounted-workspace', 'tool-mount': 'tool', 'data-object': 'data'}


def homes(m):
    ext = m.get('extensions', {})
    legacy = next((v for k, v in ext.items() if k.endswith('.mounts')), None)
    if legacy:
        zones = next((v for k, v in ext.items() if k.endswith('.placement')), {}).get('zones', [])
        return legacy['areas'], legacy['mounts'], zones
    areas = m.get('areas', [])
    owner = {}
    for a in areas:
        for key in ('primaryAnchor',):
            owner[a[key]] = a
        for key in ('toolAnchors', 'dataAnchors'):
            for i in a[key]:
                owner[i] = a
    rows = []
    for an in m.get('anchors', []):
        if 'mount' not in an or an['id'] not in owner:
            continue
        a = owner[an['id']];role = ROLE[an['mount']['role']]
        rows.append({'anchorId': an['id'], 'areaId': a['id'], 'workspaceSlot': a['workspaceSlot'], 'mountType': an['mount']['type'],
                     'role': role, 'clearanceMeters': 16 if role == 'mounted-workspace' else 4})
    return areas, rows, m.get('placementZones', [])
