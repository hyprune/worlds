#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Seeded all-angle review in private, flocked core nested. Never live-session IPC."""
import argparse,fcntl,hashlib,inspect,json,math,os,random,shutil,statistics,subprocess,sys,time
from pathlib import Path
from types import SimpleNamespace
import numpy as np
from PIL import Image,ImageDraw
ROOT=Path(__file__).resolve().parents[1]
p=argparse.ArgumentParser(description=__doc__);p.add_argument('--core',type=Path,default=ROOT.parent/'core-visibility-bench');p.add_argument('--package',type=Path,default=ROOT/'dist/com.hyprune.lumen-reach');p.add_argument('--output',type=Path,required=True);p.add_argument('--owners-only',action='store_true');p.add_argument('--view',action='append');p.add_argument('--no-pairs',action='store_true');a=p.parse_args();a.output=a.output.resolve();a.output.mkdir(parents=True,exist_ok=True)
sys.path.insert(0,str(a.core/'dev/nested'));import session,authoring
manifest=json.loads((a.package/'world.json').read_text())
report={'status':'RUNNING','seed':7009,'worldVersion':manifest['version'],'coreCommit':subprocess.check_output(['git','-C',str(a.core),'rev-parse','HEAD'],text=True).strip(),'manifestSHA256':hashlib.sha256((a.package/'world.json').read_bytes()).hexdigest(),'sceneSHA256':hashlib.sha256((a.package/'scene.gltf').read_bytes()).hexdigest(),'method':'Private native-4K Intel nested; Medium fixed 0.5 scale; held photos. Owner poses, deterministic route samples, elevated random views to 60m, pole/seam and roof inspection. Culling on/off image comparison. Streak scores are candidates for review, not semantic proof.','views':[]}
def q(yaw,pitch):
 sy=math.sin(-yaw/2);cy=math.cos(-yaw/2);sp=math.sin(pitch/2);cp=math.cos(pitch/2)
 return [cy*sp,sy*cp,-sy*sp,cy*cp]
def look(pos,target):
 d=np.array(target)-pos;return q(math.atan2(d[0],-d[2]),math.asin(d[1]/np.linalg.norm(d)))
views=[]
for v in json.loads((ROOT/'lumen-reach/review-poses-v7.json').read_text())['owner']:
 views.append({'id':v['id'],'kind':'owner','position':v['position'],'orientation':q(v['yaw'],v['pitch'])})
for v in json.loads((ROOT/'lumen-reach/views.json').read_text())['views']:
 if v['id'] not in ['01-sun-court','02-array-hall','03-rime-vault','04-signal-rise']:continue
 pos=[v['position'][0],v['position'][2],-v['position'][1]];target=[v['target'][0],v['target'][2],-v['target'][1]]
 views.append({'id':v['id'],'kind':'home','position':pos,'orientation':look(pos,target)})
for name,pos,target in [('court-60-down',[4,60,-8],[4,0,-8]),('court-60-north',[4,60,-8],[30,10,-120]),('sky-seam',[4,30,-8],[4,35,100]),('sky-zenith',[4,60,-8],[4,160,-8.01]),('hall-roof',[2,38,-45],[9,0,-46]),('vault-roof',[65,35,-68],[38,0,-88]),('rise-60',[57,60,-143],[57,0,-143]),('rise-exterior',[110,60,-170],[57,35,-147]),('stair-soffit',[-17,1.7,-28],[-21.5,7,-35]),('cascade-model',[-32,15,-28],[-57,6,-63]),('spire-model',[-2,26,-67],[12,24,-94]),('rise-zenith',[57,1.7,-132],[57,100,-132.01]),('rise-corner-se',[84.3,1.7,-112.6],[70,1.7,-100]),('rise-corner-sw',[29.7,1.7,-112.6],[57,8,-160]),('stair-tunnel-up',[54,-3.3,-104],[54,1.7,-124]),('court-day-seam',[4,45,-8],[109,155,-318]),('roof-ramp-foot',[-12.5,20.5,-8.5],[-12,12.2,-21]),('roof-ramp-foot-eye',[-18.6,13.7,-19.3],[-11.7,13.4,-21.2]),('roof-bridge-eye',[-9.8,17.7,-36.0],[-3,17.5,-36.0])]:
 views.append({'id':name,'kind':'targeted','position':pos,'orientation':look(pos,target)})
if not a.owners_only:
 rng=random.Random(7009);routes=manifest['extensions']['com.hyprune.lumen-reach.routes'];nodes={n['id']:np.array(n['position']) for n in routes['nodes']}
 for i in range(32):
  e=rng.choice(routes['edges']);t=rng.uniform(.12,.88);pos=nodes[e['from']]*(1-t)+nodes[e['to']]*t;pos[1]+=1.7
  if i>=16:pos[1]=rng.uniform(25,60)
  yaw=rng.uniform(-math.pi,math.pi);pitch=rng.uniform(-1.35,1.15)
  views.append({'id':f'random-{i:02d}','kind':'walkable' if i<16 else 'elevated','route':[e['from'],e['to'],t],'position':pos.tolist(),'orientation':q(yaw,pitch)})
if a.view:views=[v for v in views if v['id'] in a.view]
def save():(a.output/'report.json').write_text(json.dumps(report,indent=2)+'\n')
def streak_score(path):
 # Vertical edge smear: columns with horizontal detail, almost no vertical
 # detail, persisting over a tall window. Flat sky is excluded by dx threshold.
 a=np.array(Image.open(path).convert('RGB').resize((960,540)),dtype=float)/255
 scores=[]
 for y in range(80,440,40):
  b=a[y:y+100,20:-20];dx=np.mean(abs(np.diff(b,axis=1)),axis=(0,2));dy=np.mean(abs(np.diff(b,axis=0)),axis=(0,2))
  n=min(len(dx),len(dy));mask=(dx[:n]>.012)&(dy[:n]<.0015)
  scores.append(float(mask.mean()))
 return max(scores)
def sheet():
 cols=4;w,h=640,360;rows=math.ceil(len(report['views'])/cols);im=Image.new('RGB',(cols*w,rows*(h+30)),(16,22,29));d=ImageDraw.Draw(im)
 for i,v in enumerate(report['views']):
  x=i%cols*w;y=i//cols*(h+30);pic=Image.open(v['path']).convert('RGB');pic.thumbnail((w,h));im.paste(pic,(x,y));d.text((x+8,y+h+7),v['id']+' / '+v['kind'],fill='white')
 im.save(a.output/'contact-sheet.jpg',quality=91)
def acceptance(client,children,args,shell_token,socketpath):
 loaded=max(session.STATE.glob('hyprune-*.so'),key=lambda p:p.stat().st_mtime_ns);report['pluginSHA256']=hashlib.sha256(loaded.read_bytes()).hexdigest()
 target=session.STATE/'worlds'/manifest['id'];shutil.rmtree(target);shutil.copytree(a.package,target)
 client.call('world.load',{'worldId':manifest['id']});session.ctl('eval','hl.config({misc={disable_watchdog_warning=true},cursor={inactive_timeout=1}})');session.ctl('eval','hl.dispatch(hl.dsp.focus({ monitor = "HEADLESS-1" }))');session.ctl('eval','hl.plugin.hyprune.toggle("HEADLESS-1")')
 client.call('graphics.set',{'patch':{'quality':'medium','offload':'off','dynamic_resolution':False,'outline':False,'visibility_culling':True}});time.sleep(6)
 for v in views:
  lens={k:v[k] for k in ['position','orientation']};lens.update(fov=60,renderScale=.5)
  client.call('camera.photo',lens);time.sleep(.3);actual=client.call('camera.get',{});assert actual['held'] and math.dist(actual['position'],v['position'])<1e-4;assert abs(sum(x*y for x,y in zip(actual['orientation'],v['orientation'])))>.99999
  client.call('graphics.set',{'patch':{'visibility_culling':True}});time.sleep(.35)
  t=client.call('graphics.get',{})['timings'];assert t['nativeSize']==[3840,2160] and t['renderScale']==.5,t;assert 'Intel' in t['renderer'] and t['graphics']['quality']=='medium',t
  path=a.output/(v['id']+'.png');subprocess.run([str(session.HERE/'ctl.py'),'shot',str(path)],check=True,stdout=subprocess.DEVNULL)
  row={**v,'pose':actual,'path':str(path),'timings':t,'verticalStreakCandidateFraction':streak_score(path)}
  if not a.no_pairs:
   client.call('graphics.set',{'patch':{'visibility_culling':False}});time.sleep(.35);offpath=a.output/(v['id']+'-unculled.png');subprocess.run([str(session.HERE/'ctl.py'),'shot',str(offpath)],check=True,stdout=subprocess.DEVNULL)
   on=np.array(Image.open(path).convert('RGB'),dtype=np.int16)[100:-100,100:-100];off=np.array(Image.open(offpath).convert('RGB'),dtype=np.int16)[100:-100,100:-100];delta=abs(on-off);row['cullingChangedPixelFraction']=float(np.mean(delta.max(axis=2)>8));row['unculledPath']=str(offpath)
  if v['kind']=='home':
   client.call('graphics.set',{'patch':{'visibility_culling':True}});time.sleep(1);samples=[]
   for _ in range(32):samples.append(client.call('graphics.get',{})['timings']);time.sleep(.08)
   row['performanceSamples']=samples;row['performance']={k:statistics.median(x[k] for x in samples) for k in ['cpuRenderMs','frameMs']};row['performance']['gpuPassSumMs']=statistics.median(sum(x['gpuPassMs']) for x in samples if all(y is not None for y in x['gpuPassMs']))
  report['views'].append(row);save();print('VIEW',v['id'],'streak',round(row['verticalStreakCandidateFraction'],4),'culling delta',row.get('cullingChangedPixelFraction'),flush=True)
 client.call('camera.release',{})
 if not a.owners_only:
  import integration
  report['boundaryProbes']=[]
  for name,pos,yaw,axis,sign,limit in [('court-east',[25.2,1.7,0],math.pi/2,0,1,26),('court-south',[0,1.7,15.2],math.pi,2,1,16),('court-west',[-23.2,1.7,10],-math.pi/2,0,-1,-24),('hall-west',[-12.2,1.7,-34],-math.pi/2,0,-1,-13),('rise-east',[84.2,1.7,-120],math.pi/2,0,1,85),('rise-south',[70,1.7,-112.8],math.pi,2,1,-112)]:
   client.call('movement.set',{'modeId':'com.hyprune.walk'});client.call('camera.set',{'position':pos,'orientation':q(yaw,0)});time.sleep(.2)
   integration.keys('-P','w','-s','1000','-p','w');time.sleep(.2);end=client.call('camera.get',{})['position']
   row={'id':name,'start':pos,'end':end,'axis':axis,'outwardSign':sign,'limit':limit,'inside':sign*(end[axis]-limit)<-.20};report['boundaryProbes'].append(row);save();assert row['inside'],row
  # Repeated jumps still stop at the walk-height backstop (court-east top 3.5m).
  client.call('movement.set',{'modeId':'com.hyprune.walk'});client.call('camera.set',{'position':[25.2,1.7,0],'orientation':q(math.pi/2,0)});time.sleep(.2)
  integration.keys('-P','w','-P','space','-s','1500','-p','space','-p','w');time.sleep(.6)
  report['jumpBoundaryWitness']=client.call('camera.get',{})['position'];save();assert report['jumpBoundaryWitness'][0]<25.8,report['jumpBoundaryWitness']
  # Ordinary fly (collision on, not noclip) passes over it at 6m eye height.
  client.call('movement.set',{'modeId':'com.hyprune.fly'});client.call('camera.set',{'position':[25.2,6,0],'orientation':q(math.pi/2,0)});integration.keys('-P','w','-s','1000','-p','w');time.sleep(.2)
  report['flyBoundaryWitness']=client.call('camera.get',{})['position'];save();assert report['flyBoundaryWitness'][0]>26.5,report['flyBoundaryWitness']
 client.call('runtime.exit',{});sheet()
 report['cullingLosses']=[v['id'] for v in report['views'] if v.get('cullingChangedPixelFraction',0)>.00005]
 report['status']='PASS' if not report['cullingLosses'] else 'FAIL';save();assert report['status']=='PASS',report['cullingLosses']
authoring.acceptance=acceptance
state=a.output/'.nested-state';session.STATE=state;os.environ['HYPRUNE_NESTED_STATE_DIR']=str(state);os.environ['HYPRUNE_NESTED_4K']='1'
source=inspect.getsource(session.run);needle="STATE=HERE/'.m3b-state'";assert source.count(needle)==1;source=source.replace(needle,'STATE=pathlib.Path('+repr(str(state))+')');exec(compile(source,str(session.HERE/'session.py'),'exec'),session.__dict__)
with open('/tmp/worldshell-nested.lock','a') as lock:
 print('Waiting for private nested lock',flush=True);fcntl.flock(lock,fcntl.LOCK_EX)
 try:session.run(SimpleNamespace(serve=False,record=False,m1=False,m2=False,m3a=False,m3b=False,live=False,integration=False,visible=False,authoring=True))
 except Exception as e:report.update(status='FAIL',error=str(e));save();raise
