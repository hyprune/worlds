# SPDX-License-Identifier: MIT
"""Blender (bake host): dump each Lumen lightmap group's triangulated world-space
mesh with its baked UV1, and time a fresh smart_project + pack_islands on a copy
using bake_pipeline.join_groups()'s exact parameters.
blender -b <lumen-reach.blend> -P dump_groups.py -- <out-dir> <bake-report.json>"""
import bpy,json,math,sys,time
from pathlib import Path
import numpy as np
out=Path(sys.argv[sys.argv.index('--')+1]);out.mkdir(parents=True,exist_ok=True)
report={r['group']:r for r in json.loads(Path(sys.argv[sys.argv.index('--')+2]).read_text())}
rows=[]
for name,r in report.items():
 o=bpy.data.objects['Visual-'+name];me=o.data;M=np.array(o.matrix_world)
 co=np.empty(len(me.vertices)*3);me.vertices.foreach_get('co',co);co=co.reshape(-1,3);co=co@M[:3,:3].T+M[:3,3]
 loops=np.empty(len(me.loops),dtype=np.int64);me.loops.foreach_get('vertex_index',loops)
 uv=np.empty(len(me.loops)*2);me.uv_layers['UV1'].data.foreach_get('uv',uv);uv=uv.reshape(-1,2)
 sizes=np.empty(len(me.polygons),dtype=np.int64);me.polygons.foreach_get('loop_total',sizes);assert (sizes==3).all(),name
 np.savez_compressed(out/f'{name}.npz',positions=co[loops].reshape(-1,3,3),uv=uv.reshape(-1,3,2))
 # Time Blender's unwrap on a copy, same parameters as the build.
 c=o.copy();c.data=o.data.copy();bpy.context.collection.objects.link(c)
 for x in bpy.context.selected_objects:x.select_set(False)
 c.select_set(True);bpy.context.view_layer.objects.active=c;c.data.uv_layers.active=c.data.uv_layers['UV1']
 t=time.time();bpy.ops.object.mode_set(mode='EDIT');bpy.ops.mesh.select_all(action='SELECT')
 bpy.ops.uv.smart_project(angle_limit=math.radians(30),island_margin=.003,margin_method='FRACTION',scale_to_bounds=True)
 bpy.ops.uv.pack_islands(rotate=True,scale=True,margin_method='FRACTION',margin=r['marginPixels']/r['resolution'])
 bpy.ops.object.mode_set(mode='OBJECT');seconds=time.time()-t
 bpy.data.objects.remove(c)
 rows.append({'group':name,'triangles':int(len(sizes)),'resolution':r['resolution'],'margin':r['marginPixels'],'blenderUnwrapSeconds':round(seconds,2),'bakeSeconds':r['seconds']})
 print('DUMP',json.dumps(rows[-1]),flush=True)
(out/'groups.json').write_text(json.dumps(rows,indent=2)+'\n')
