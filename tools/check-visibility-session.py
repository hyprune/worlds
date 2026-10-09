#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Paired Intel 4K visibility measurements in core's verified, flocked nested harness."""
import argparse,fcntl,hashlib,importlib.util,inspect,json,math,os,shutil,statistics,subprocess,sys,time
from pathlib import Path
from types import SimpleNamespace
import numpy as np
from PIL import Image
ROOT=Path(__file__).resolve().parents[1]
p=argparse.ArgumentParser(description=__doc__);p.add_argument('--core',type=Path,default=ROOT.parent/'core');p.add_argument('--output',type=Path,default=ROOT/'artifacts/visibility-0.6.1/nested');p.add_argument('--samples',type=int,default=32);p.add_argument('--quick',action='store_true');p.add_argument('--world',choices=['lumen-reach','switchyard']);p.add_argument('--view',action='append');p.add_argument('--no-probes',action='store_true');a=p.parse_args();a.output=a.output.resolve();a.output.mkdir(parents=True,exist_ok=True)
sys.path.insert(0,str(a.core/'dev/nested'));import session,authoring
spec=importlib.util.spec_from_file_location('visibility_audit',ROOT/'tools/check-visibility.py');audit=importlib.util.module_from_spec(spec);spec.loader.exec_module(audit)
report={'status':'RUNNING','coreCommit':subprocess.check_output(['git','-C',str(a.core),'rev-parse','HEAD'],text=True).strip(),'coreDirty':subprocess.check_output(['git','-C',str(a.core),'status','--short'],text=True).splitlines(),'method':'Intel legacy preset maps to Low; native 4K, fixed 0.5 internal scale, offload off. ABBA culling states, warm-up before each block. No owner-session control.','measurements':[],'views':[],'probes':[]}
def pose(position,target):
 x,y,z=position;tx,ty,tz=target;d=[tx-x,tz-z,y-ty];length=math.sqrt(sum(v*v for v in d));yaw=math.atan2(d[0],-d[2]);pitch=math.asin(d[1]/length)
 sy=math.sin(-yaw/2);cy=math.cos(-yaw/2);sp=math.sin(pitch/2);cp=math.cos(pitch/2)
 return {'position':[x,z,-y],'orientation':[cy*sp,sy*cp,-sy*sp,cy*cp],'fov':60,'renderScale':.5}
def save(): (a.output/'report.json').write_text(json.dumps(report,indent=2)+'\n')
def acceptance(client,children,args,shell_token,socketpath):
 loaded=max(session.STATE.glob('hyprune-*.so'),key=lambda p:p.stat().st_mtime_ns);report['loadedPluginSHA256']=hashlib.sha256(loaded.read_bytes()).hexdigest();report['protocol']=client.hello['protocol']
 session.ctl('eval','hl.config({misc={disable_watchdog_warning=true},cursor={inactive_timeout=1}})');session.ctl('eval','hl.dispatch(hl.dsp.focus({ monitor = "HEADLESS-1" }))')
 for wi,name in enumerate([n for n in ['lumen-reach','switchyard'] if not a.world or a.world==n]):
  package=ROOT/'dist'/('com.hyprune.'+name);manifest=json.loads((package/'world.json').read_text());scene=json.loads((package/manifest['scene']).read_text());areas=manifest['visibility']['areas'];owners=audit.validate(manifest,scene)
  roots=set()
  def walk(i):
   roots.add(i)
   for c in scene['nodes'][i].get('children',[]):walk(c)
  for i in scene['scenes'][scene.get('scene',0)]['nodes']:walk(i)
  counts={i:len(scene['meshes'][scene['nodes'][i]['mesh']]['primitives']) for i in roots if 'mesh' in scene['nodes'][i]};total=sum(counts.values())
  client.call('world.load',{'worldId':manifest['id']})
  if wi==0:session.ctl('eval','hl.plugin.hyprune.toggle("HEADLESS-1")')
  time.sleep(1)
  client.call('graphics.set',{'patch':{'quality':'low','offload':'off','dynamic_resolution':False,'outline':False,'visibility_culling':False}})
  report.setdefault('packages',{})[name]={'version':manifest['version'],'manifestSHA256':hashlib.sha256((package/'world.json').read_bytes()).hexdigest(),'sceneSHA256':hashlib.sha256((package/manifest['scene']).read_bytes()).hexdigest()}
  views=json.loads((ROOT/('artifacts/lumen-reach/views.json' if name=='lumen-reach' else 'switchyard/views.json')).read_text())['views']
  if name=='lumen-reach':
   views += [dict(id='court-east',position=[23,-9,1.7],target=[8,24,6]),dict(id='court-east-north',position=[23,-9,1.7],target=[50,89,2]),dict(id='court-east-service-sightline',position=[25,18,1.7],target=[38,83,2]),dict(id='court-roof-north',position=[8,24.5,17.7],target=[38,89,2]),dict(id='entry-through',position=[8,27,1.7],target=[8,45,7]),dict(id='descent-top',position=[30,52,1.7],target=[30,74,-4]),dict(id='descent-bottom',position=[30,74,-4.3],target=[38,88,-2]),dict(id='vault-looking-out',position=[38,79,-4.3],target=[8,40,8]),dict(id='vault-center-out',position=[38,89,-4.3],target=[8,40,8]),dict(id='ascent-bottom',position=[54,101,-4.1],target=[54,124,1.7]),dict(id='ascent-top',position=[54,124,1.7],target=[54,100,-4.3]),dict(id='outside-fallback',position=[110,90,40],target=[30,80,0])]
  else:
   for st in json.loads((ROOT/'switchyard/world.spec.json').read_text())['stations']:
    views.append(dict(id=st['id']+'-dock',position=[st['x']-2.67,st['y']-1,1.7],target=[st['x']+1.3,st['y']+.8,2.25]))
  if a.view:views=[v for v in views if v['id'] in a.view]
  for v in views:
   lens=pose(v['position'],v['target']);client.call('camera.photo',lens);time.sleep(.25)
   actual=client.call('camera.get',{});assert actual['held'] and max(abs(x-y) for x,y in zip(actual['position'],lens['position']))<1e-4
   active=audit.active_areas(areas,lens['position']);visible=audit.visible_areas(areas,lens['position']);expected=sum(n for i,n in counts.items() if i not in owners or owners[i] in visible)
   paired={};paths={}
   for enabled in [False,True]:
    client.call('graphics.set',{'patch':{'visibility_culling':enabled}});time.sleep(.5)
    t=client.call('graphics.get',{})['timings'];assert t['nativeSize']==[3840,2160] and t['renderScale']==.5,t
    assert 'Intel' in t['renderer'] and t['graphics']['quality']=='low',t
    assert t['visibility']=={'submitted':expected if enabled else total,'culled':total-expected if enabled else 0,'total':total},(v['id'],t['visibility'],expected)
    suffix='on' if enabled else 'off';path=a.output/(name+'-'+v['id']+'-'+suffix+'.png');subprocess.run([str(session.HERE/'ctl.py'),'shot',str(path)],check=True,stdout=subprocess.DEVNULL);paths[suffix]=str(path);paired[suffix]=t['visibility']
   off=np.array(Image.open(paths['off']).convert('RGB'),dtype=np.int16);on=np.array(Image.open(paths['on']).convert('RGB'),dtype=np.int16)
   # Ignore compositor cursor/HUD edges only; retain the entire central world viewport.
   delta=np.abs(off[100:-100,100:-100]-on[100:-100,100:-100]);fraction=float(np.mean(np.max(delta,axis=2)>8));mean=float(delta.mean())
   row={'world':name,'id':v['id'],'pose':lens,'sourceAreas':sorted(active),'visibility':paired,'changedPixelFraction':fraction,'meanAbsoluteChannelDifference':mean,'paths':paths};report['views'].append(row);save();print('VIEW',name,v['id'],paired['on'],'changed',round(fraction,6),flush=True)
   primary=(v['id'] in ['01-sun-court','02-array-hall','03-rime-vault','04-signal-rise','court-east'] if name=='lumen-reach' else v['id'] in ['01-concourse','03-build','04-route'])
   if primary and not a.quick:
    blocks=[]
    for enabled in [False,True,True,False]:
     client.call('graphics.set',{'patch':{'visibility_culling':enabled}});time.sleep(1)
     samples=[]
     for _ in range(a.samples):samples.append({**client.call('graphics.get',{})['timings'],'sampleMonotonic':time.monotonic()});time.sleep(.1)
     blocks.append({'culling':enabled,'samples':samples})
    def summary(enabled):
     s=[x for b in blocks if b['culling']==enabled for x in b['samples']]
     return {'submitted':s[-1]['visibility']['submitted'],'cpuRenderMs':statistics.median(x['cpuRenderMs'] for x in s),'gpuPassSumMs':statistics.median(sum(x['gpuPassMs']) for x in s if all(y is not None for y in x['gpuPassMs'])),'frameMs':statistics.median(x['frameMs'] for x in s)}
    item={'world':name,'view':v['id'],'off':summary(False),'on':summary(True),'blocks':blocks};report['measurements'].append(item);save();print('MEASURE',name,v['id'],item['off'],item['on'],flush=True)
  # Inclusive boundaries and every authored route point: renderer membership must match the contract.
  points=[]
  for ar in areas:
   lo,hi=ar['bounds']['min'],ar['bounds']['max'];center=[(l+h)/2 for l,h in zip(lo,hi)]
   points.append((ar['id']+' center',center))
   for axis in range(3):
    for val in [lo[axis],hi[axis]]:
     q=center.copy();q[axis]=val;points.append((ar['id']+' boundary',q))
  for pt in manifest['extensions']['com.hyprune.'+name+'.routes']['nodes']:
   q=pt['position'];points.append(('route '+pt['id'],[q[0],q[1]+1.7,q[2]]))
  client.call('graphics.set',{'patch':{'visibility_culling':True}})
  for label,pos in ([] if a.no_probes else points):
   client.call('camera.photo',{'position':pos,'orientation':[0,0,0,1],'fov':60,'renderScale':.5});time.sleep(.06)
   visible=audit.visible_areas(areas,pos);expected=sum(n for i,n in counts.items() if i not in owners or owners[i] in visible)
   t=client.call('graphics.get',{})['timings'];assert t['visibility']['submitted']==expected,(label,pos,t['visibility'],expected)
   report['probes'].append({'world':name,'label':label,'position':pos,'submitted':expected})
  client.call('camera.release',{});save()
 client.call('runtime.exit',{});losses=[(v['world'],v['id'],v['changedPixelFraction']) for v in report['views'] if v['changedPixelFraction']>0.00005];report['visualLosses']=losses;assert not losses,('visible geometry changed',losses);report['status']='PASS';save();print('PASS paired visibility capture and region boundary/route membership',flush=True)
authoring.acceptance=acceptance
state=a.output/'.nested-state';session.STATE=state;os.environ['HYPRUNE_NESTED_STATE_DIR']=str(state);os.environ['HYPRUNE_NESTED_4K']='1'
source=inspect.getsource(session.run);needle="STATE=HERE/'.m3b-state'";assert source.count(needle)==1;source=source.replace(needle,'STATE=pathlib.Path('+repr(str(state))+')');exec(compile(source,str(session.HERE/'session.py'),'exec'),session.__dict__)
with open('/tmp/worldshell-nested.lock','a') as lock:
 fcntl.flock(lock,fcntl.LOCK_EX)
 try:session.run(SimpleNamespace(serve=False,record=False,m1=False,m2=False,m3a=False,m3b=False,live=False,integration=False,visible=False,authoring=True))
 except Exception as e:report.update(status='FAIL',error=str(e));save();raise
