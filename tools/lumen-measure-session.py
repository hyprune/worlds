#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Numeric nested measurements of world packages. Private flocked nested only;
never live-session IPC. Native 4K, Intel, HYPRUNE_CONTINUOUS_RENDER=1 so every
tick renders (render-on-demand idles would lower GPU clocks).

  ab       Packages A and B in one compositor, rounds alternate A/B so clock
           and thermal drift hit both. Per package: load time (world.load to
           upload done and a new frame), upload CPU ms, GPU MiB; per standard
           pose (core dev/nested/perf.py spawns) at a fixed render scale: GPU
           pass ms (30 frames, camera nudged so each is new); a held still
           per pose on round 0 for PSNR/deltaE.
  flicker  Same path walked in both packages with held photos every 1/60 s
           of 3.5 m/s walking; temporal shimmer = mean |second difference|
           of luminance in a far-floor screen band (smooth motion has small
           second differences, aliasing has large ones).
  gate     Scripted route capture: eye-height poses every 3 m along the
           route graph. Fixed scale: p50/p95 GPU frame ms; dynamic resolution
           (target 60): settled render scale per segment.
"""
import argparse,fcntl,hashlib,inspect,json,math,os,shutil,statistics,subprocess,sys,time
from pathlib import Path
from types import SimpleNamespace
import numpy as np
from PIL import Image
ROOT=Path(__file__).resolve().parents[1]
p=argparse.ArgumentParser(description=__doc__,formatter_class=argparse.RawDescriptionHelpFormatter)
p.add_argument('mode',choices=['ab','flicker','gate'])
p.add_argument('--core',type=Path,default=ROOT.parent/'core-optimise')
p.add_argument('--package',type=Path,action='append',required=True,help='A, then optionally B')
p.add_argument('--output',type=Path,required=True)
p.add_argument('--rounds',type=int,default=3);p.add_argument('--scale',type=float,default=.5)
p.add_argument('--quality',default='medium')
a=p.parse_args();a.output=a.output.resolve();a.output.mkdir(parents=True,exist_ok=True)
sys.path.insert(0,str(a.core/'dev/nested'));import session,authoring
POSES=[('arrival',[-8,1.7,12],0,0),('array-hall',[8,1.7,-34],0,0),('rime-vault',[38,-4.3,-79],0,0),('signal-rise',[54,1.7,-125],0,0)]
def q(yaw,pitch):
 sy=math.sin(-yaw/2);cy=math.cos(-yaw/2);sp=math.sin(pitch/2);cp=math.cos(pitch/2)
 return [cy*sp,sy*cp,-sy*sp,cy*cp]
packages=[(chr(65+i),pkg.resolve(),json.loads((pkg/'world.json').read_text())) for i,pkg in enumerate(a.package)]
report={'mode':a.mode,'status':'RUNNING','scale':a.scale,'quality':a.quality,'rounds':a.rounds,'coreCommit':subprocess.check_output(['git','-C',str(a.core),'rev-parse','HEAD'],text=True).strip(),
 'packages':{v:{'path':str(pkg),'version':m['version'],'formatVersion':m['formatVersion'],'manifestSHA256':hashlib.sha256((pkg/'world.json').read_bytes()).hexdigest()} for v,pkg,m in packages}}
def save():(a.output/'report.json').write_text(json.dumps(report,indent=1)+'\n')

def route_poses(m,step=3.0):
 """Deterministic depth-first walk of the route graph from the default spawn:
 eye-height poses every `step` metres, yaw along travel."""
 g=next(v for k,v in m['extensions'].items() if k.endswith('.routes'));nodes={n['id']:np.array(n['position'],float) for n in g['nodes']}
 adj={k:[] for k in nodes}
 for e in g['edges']:adj[e['from']].append(e['to']);adj[e['to']].append(e['from'])
 out=[];seen=set();done=set()
 def emit(u,v):
  A,B=nodes[u],nodes[v];d=B-A;n=max(1,int(float(np.linalg.norm(d))/step));yaw=math.atan2(d[0],-d[2])
  for k in range(n):out.append({'segment':f'{u}>{v}','position':(A+d*(k/n)+[0,1.7,0]).tolist(),'yaw':yaw})
 def walk(u):
  # Every edge there and back, depth first: the core route check's traversal.
  seen.add(u)
  for v in adj[u]:
   e=frozenset((u,v))
   if e in done:continue
   done.add(e);emit(u,v)
   if v not in seen:walk(v)
   emit(v,u)
 walk(m.get('defaultSpawn','arrival'));return out

def acceptance(client,children,args,shell_token,socketpath):
 loaded=max(session.STATE.glob('hyprune-*.so'),key=lambda p:p.stat().st_mtime_ns);report['pluginSHA256']=hashlib.sha256(loaded.read_bytes()).hexdigest()
 ids={}
 for v,pkg,m in packages:
  wid=m['id'] if v=='A' else m['id']+'.'+v.lower();target=session.STATE/'worlds'/wid;shutil.rmtree(target,ignore_errors=True);shutil.copytree(pkg,target)
  if wid!=m['id']:mm=json.loads((target/'world.json').read_text());mm['id']=wid;(target/'world.json').write_text(json.dumps(mm))
  ids[v]=wid
 timings=lambda:client.call('graphics.get',{})['timings']
 fixed={'quality':a.quality,'offload':'off','dynamic_resolution':False,'render_scale':a.scale,'outline':False,'visibility_culling':True}
 def enter(v,first=False):
  t0=time.monotonic();client.call('world.load',{'worldId':ids[v]});call=time.monotonic()-t0
  if first:
   session.ctl('eval','hl.config({misc={disable_watchdog_warning=true},cursor={inactive_timeout=1}})');session.ctl('eval','hl.dispatch(hl.dsp.focus({ monitor = "HEADLESS-1" }))');session.ctl('eval','hl.plugin.hyprune.toggle("HEADLESS-1")')
  while True:
   t=timings()
   if not t['upload']['pending'] and t['upload'].get('gpuBytes'):break
   if time.monotonic()-t0>120:raise RuntimeError('upload did not finish')
   time.sleep(.02)
  ready=time.monotonic()-t0;f=t['renderedFrames']
  while timings()['renderedFrames']<=f and time.monotonic()-t0<130:time.sleep(.01)
  return {'callMs':round(call*1000,1),'readyMs':round(ready*1000,1),'firstFrameMs':round((time.monotonic()-t0)*1000,1),'upload':{k:t['upload'][k] for k in ['gpuBytes','bytes','cpuMs','maxStepMs','steps']},'gpuMiB':round(t['upload']['gpuBytes']/2**20,2)}
 def shot(path):subprocess.run([str(session.HERE/'ctl.py'),'shot',str(path)],check=True,stdout=subprocess.DEVNULL)
 def photo(pos,yaw,pitch=0):
  client.call('camera.photo',{'position':pos,'orientation':q(yaw,pitch),'fov':60,'renderScale':a.scale});time.sleep(.12)
 def gpu_samples(n,pos,yaw,pitch=0):
  s=[]
  for k in range(n):
   client.call('camera.photo',{'position':pos,'orientation':q(yaw+(k%2)*1e-4,pitch),'fov':60,'renderScale':a.scale});time.sleep(.1);t=timings()
   if all(x is not None for x in t['gpuPassMs']):s.append(t)
  return s
 first=True
 if a.mode=='ab':
  report['loads']=[];report['poses']=[]
  for r in range(a.rounds):
   for v,_,_ in packages:
    row=enter(v,first);first=False;client.call('graphics.set',{'patch':fixed});time.sleep(2);row.update(variant=v,round=r);report['loads'].append(row);save();print('LOAD',json.dumps(row),flush=True)
    for name,pos,yaw,pitch in POSES:
     photo(pos,yaw,pitch);time.sleep(1.2);s=gpu_samples(30,pos,yaw,pitch)
     item={'variant':v,'round':r,'pose':name,'gpuTotalMs':statistics.median(sum(x['gpuPassMs']) for x in s),'gpuMs':{k:statistics.median(x['gpuEffectsMs'][k] for x in s if x['gpuEffectsMs'][k] is not None) for k in s[-1]['gpuEffectsMs'] if s[-1]['gpuEffectsMs'][k] is not None},'cpuRenderMs':statistics.median(x['cpuRenderMs'] for x in s),'internal':s[-1]['internalSize'],'n':len(s)}
     if r==0:photo(pos,yaw,pitch);time.sleep(.4);item['still']=str(a.output/f'{v}-{name}.png');shot(item['still'])
     report['poses'].append(item);save();print('POSE',json.dumps({k:item[k] for k in ['variant','round','pose','gpuTotalMs']}),flush=True)
 elif a.mode=='flicker':
  # Long open floors at eye height, looking along them, pitched slightly down
  # so the 15-60 m floor band fills the middle of the frame.
  paths=[('court-north',[-2,1.7,10],0.0,-.10),('rise-north',[57,1.7,-114],0.0,-.10),('hall-north',[8,1.7,-33],0.0,-.12)]
  report['paths']=[]
  for v,_,_ in packages:
   enter(v,first);first=False;client.call('graphics.set',{'patch':fixed});time.sleep(2)
   for name,start,yaw,pitch in paths:
    frames=[]
    for k in range(24):
     pos=[start[0]+math.sin(yaw)*k*3.5/60,start[1],start[2]-math.cos(yaw)*k*3.5/60];photo(pos,yaw,pitch);time.sleep(.25)
     path=a.output/f'{v}-{name}-{k:02d}.png';shot(path);frames.append(str(path))
    report['paths'].append({'variant':v,'path':name,'frames':frames});save();print('FLICKER',v,name,flush=True)
 else:
  poses=route_poses(packages[0][2]);report['routePoses']=len(poses);report['runs']={};pool={v:([],[]) for v,_,_ in packages}
  segs={}
  for pz in poses:segs.setdefault(pz['segment'],[]).append(pz)
  for r in range(a.rounds):
   for v,_,_ in packages:
    enter(v,first);first=False;fixed_ms,scales=pool[v]
    client.call('graphics.set',{'patch':fixed});time.sleep(2)
    for pz in poses:fixed_ms+=[sum(x['gpuPassMs']) for x in gpu_samples(4,pz['position'],pz['yaw'])]
    client.call('graphics.set',{'patch':{**fixed,'dynamic_resolution':True,'render_scale':'auto','target_fps':60}});time.sleep(2)
    for seg,ps in segs.items():
     for pz in ps:photo(pz['position'],pz['yaw']);time.sleep(.25)
     time.sleep(.6);scales.append(timings()['renderScale'])
    run={'gpuFrameMs':{'p50':float(np.percentile(fixed_ms,50)),'p95':float(np.percentile(fixed_ms,95)),'n':len(fixed_ms)},'settledScale':{'p50':float(np.percentile(scales,50)),'p05':float(np.percentile(scales,5)),'n':len(scales)},'rounds':r+1}
    report['runs'][v]=run;save();print('GATE',v,'round',r,json.dumps(run),flush=True)
 client.call('camera.release',{});client.call('runtime.exit',{})
 report['status']='DONE';save()

authoring.acceptance=acceptance
state=a.output/'.nested-state';session.STATE=state;os.environ['HYPRUNE_NESTED_STATE_DIR']=str(state);os.environ['HYPRUNE_NESTED_4K']='1';os.environ['HYPRUNE_CONTINUOUS_RENDER']='1'
os.environ['HYPRUNE_NESTED_PLUGIN']=str(a.core/'build/hyprune-core.so')
source=inspect.getsource(session.run);needle=next((n for n in ["STATE=STATE_ROOT/'.m3b-state'","STATE=HERE/'.m3b-state'"] if source.count(n)==1),None);assert needle;source=source.replace(needle,'STATE=pathlib.Path('+repr(str(state))+')');exec(compile(source,str(session.HERE/'session.py'),'exec'),session.__dict__)
with open('/tmp/worldshell-nested.lock','a') as lock:
 print('Waiting for private nested lock',flush=True);fcntl.flock(lock,fcntl.LOCK_EX)
 try:session.run(SimpleNamespace(serve=False,record=False,m1=False,m2=False,m3a=False,m3b=False,live=False,integration=False,visible=False,authoring=True))
 except Exception as e:report.update(status='FAIL',error=str(e));save();raise
