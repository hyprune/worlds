#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Reuse a measured view only when the final manifest selects exactly the same nodes."""
import argparse,copy,hashlib,importlib.util,json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location('audit',Path(__file__).with_name('check-visibility.py'));audit=importlib.util.module_from_spec(spec);spec.loader.exec_module(audit)
p=argparse.ArgumentParser(description=__doc__);p.add_argument('base',type=Path);p.add_argument('correction',type=Path);p.add_argument('output',type=Path);a=p.parse_args()
def read(p):return json.loads(p.read_text())
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
base=read(a.base/'report.json');fix=read(a.correction/'report.json')
assert fix['status']=='PASS' and not fix['visualLosses']
assert base['status']=='FAIL' and base.get('visualLosses') and base['error'].startswith("('visible geometry changed'")
assert base['coreCommit']==fix['coreCommit'] and base['loadedPluginSHA256']==fix['loadedPluginSHA256']
changed={(v['world'],v['id']):v for v in fix['views']}
assert all((world,ident) in changed for world,ident,_ in base['visualLosses']), 'unresolved failed view'
models={};packages={}
for world,oldinfo in base['packages'].items():
 current=ROOT/'dist'/('com.hyprune.'+world);old=a.base/'.nested-state/worlds'/('com.hyprune.'+world)
 assert sha(old/'world.json')==oldinfo['manifestSHA256']
 oldm=read(old/'world.json');newm=read(current/'world.json');oldplain=copy.deepcopy(oldm);newplain=copy.deepcopy(newm)
 oldplain.pop('visibility');newplain.pop('visibility');assert oldplain==newplain, 'non-visibility change'
 assert sha(current/'scene.gltf')==oldinfo['sceneSHA256']==sha(old/'scene.gltf')
 scene=read(current/'scene.gltf');owners=audit.validate(newm,scene);assert owners==audit.validate(oldm,scene), 'ownership changed'
 visible=set()
 def visit(i):
  visible.add(i)
  for c in scene['nodes'][i].get('children',[]):visit(c)
 for i in scene['scenes'][scene.get('scene',0)]['nodes']:visit(i)
 meshes={i for i in visible if 'mesh' in scene['nodes'][i]}
 models[world]=(oldm,newm,owners,meshes)
 packages[world]={**oldinfo,'manifestSHA256':sha(current/'world.json')}
 if world in fix['packages']:assert packages[world]==fix['packages'][world]

def selected(world,point,old=False):
 before,after,owners,meshes=models[world];regions=(before if old else after)['visibility']['areas'];allowed=audit.visible_areas(regions,point)
 return {i for i in meshes if i not in owners or owners[i] in allowed}

views=[];reused=[]
for v in base['views']:
 key=(v['world'],v['id'])
 if key in changed:
  replacement=copy.deepcopy(changed[key]);assert replacement['pose']==v['pose'];replacement['measuredManifestSHA256']=fix['packages'][v['world']]['manifestSHA256'];replacement['measurementPhase']='correction';views.append(replacement)
 else:
  assert selected(v['world'],v['pose']['position'],old=True)==selected(v['world'],v['pose']['position']), ('changed submission set requires recapture',key)
  replacement=copy.deepcopy(v);replacement['measuredManifestSHA256']=base['packages'][v['world']]['manifestSHA256'];replacement['measurementPhase']='base';replacement['finalSubmissionSetIdentical']=True;views.append(replacement);reused.append(key)
assert len(views)==len(base['views']) and all(v['changedPixelFraction']<=.00005 for v in views)
newmeasure={(x['world'],x['view']):x for x in fix['measurements']};measurements=[]
for m in base['measurements']:
 key=(m['world'],m['view']);phase='correction' if key in newmeasure else 'base';item=copy.deepcopy(newmeasure.get(key,m));item['measurementPhase']=phase;item['measuredManifestSHA256']=(fix if phase=='correction' else base)['packages'][m['world']]['manifestSHA256'];measurements.append(item)
assert all((m['world'],m['view']) in newmeasure for m in base['measurements'] if (m['world'],m['view']) in changed), 'changed measured view needs new samples'
probes=[x for x in base['probes'] if x['world'] not in fix['packages']]+fix['probes']
assert len(probes)==len(base['probes'])
out={**base,'status':'PASS','error':None,'packages':packages,'views':views,'measurements':measurements,'probes':probes,'visualLosses':[], 'phases':[{'path':str(a.base/'report.json'),'status':base['status'],'packages':base['packages']},{'path':str(a.correction/'report.json'),'status':fix['status'],'packages':fix['packages']}],'reuseAudit':{'status':'PASS','unchangedSceneAndOwnership':True,'identicalFinalSubmissionSets':reused,'correctedViews':[list(k) for k in changed]}}
a.output.mkdir(parents=True,exist_ok=True);(a.output/'report.json').write_text(json.dumps(out,indent=2)+'\n');print('PASS final visibility evidence:',len(views),'views,',len(probes),'probes,',len(measurements),'paired measurements')
