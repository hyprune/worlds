#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Release-specific budget and compatibility checks for the Rime density pass."""
import argparse,json,sys
from pathlib import Path
from gltf_io import Scene
p=argparse.ArgumentParser();p.add_argument('before',type=Path);p.add_argument('after',type=Path);p.add_argument('before_report',type=Path);p.add_argument('after_report',type=Path);a=p.parse_args()
b=Scene(a.before);s=Scene(a.after);old=json.loads(a.before_report.read_text());new=json.loads(a.after_report.read_text())
assert b.manifest['version']=='0.5.0' and s.manifest['version']=='0.6.0'
assert b.manifest['anchors']==s.manifest['anchors'],'existing interactive mount contract changed'
for key in ['com.hyprune.lumen-reach.routes','com.hyprune.lumen-reach.stairs','com.hyprune.lumen-reach.placement']:
 assert b.manifest['extensions'][key]==s.manifest['extensions'][key],key
assert new['visualTriangles']<=old['visualTriangles']*1.30,'triangle budget growth exceeded'
assert new['drawCallEstimate']<=old['drawCallEstimate']*1.40,'draw estimate growth exceeded'
assert not new['untexturedPhysicalMaterials']
materials={s.doc['materials'][p['material']]['name'].split('--')[-1] for _,name,p,_,_ in s.primitives() if name=='Visual-rime-vault'}
assert {'vault-metal','condensation','rime-crust','ice-body','ice-rim'}<=materials
assert 'frost' not in materials,'mottled material survived in the Vault'
before_nodes={r['node']:r['triangles'] for r in old['UV1']};after_nodes={r['node']:r['triangles'] for r in new['UV1']}
unchanged=['Visual-sun-court','Visual-array-hall','Visual-signal-rise','Visual-foliage','Visual-connector-descent','Visual-connector-ascent']
assert all(before_nodes[n]==after_nodes[n] for n in unchanged)
print(json.dumps({'status':'PASS','anchorsUnchanged':len(s.manifest['anchors']),'routesStairsAndPlacementUnchanged':True,'unchangedGeometryChunks':unchanged,'triangleGrowthPercent':round(100*(new['visualTriangles']/old['visualTriangles']-1),2),'drawGrowthPercent':round(100*(new['drawCallEstimate']/old['drawCallEstimate']-1),2),'gpuGrowthPercent':round(100*(new['conservativeGpuBytes']/old['conservativeGpuBytes']-1),2),'rimeMaterials':sorted(materials),'rimeBeforeTriangles':before_nodes['Visual-rime-vault'],'rimeAfterTriangles':after_nodes['Visual-rime-vault']},indent=2))
