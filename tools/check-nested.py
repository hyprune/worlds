#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Exercise this package using core's verified, disposable nested harness.
Uses the same global flock as core. No outer-session hyprctl invocation.
Core must already be built; its sources/binaries are not modified.
"""
import argparse,fcntl,hashlib,inspect,json,math,shutil,subprocess,sys,time
from pathlib import Path
from types import SimpleNamespace
p=argparse.ArgumentParser();p.add_argument('--core',type=Path,default=Path(__file__).resolve().parents[2]/'core');p.add_argument('--package',type=Path,default=Path(__file__).resolve().parents[1]/'dist/com.hyprune.switchyard');p.add_argument('--record',action='store_true');p.add_argument('--output',type=Path,default=Path(__file__).resolve().parents[1]/'artifacts/switchyard');args=p.parse_args();args.output.mkdir(parents=True,exist_ok=True)
sys.path.insert(0,str(args.core/'dev/nested'));import session
report={'pluginSHA256':hashlib.sha256((args.core/'build/hyprune-core.so').read_bytes()).hexdigest(),'coreCommit':subprocess.check_output(['git','-C',str(args.core),'rev-parse','HEAD'],text=True).strip()}
def smoke(client,children,ignored):
 manifest=json.loads((args.package/'world.json').read_text());ident=manifest['id'];assert ident=='com.hyprune.switchyard'
 installed=session.STATE/'worlds'/ident
 if installed.exists():shutil.rmtree(installed)
 shutil.copytree(args.package,installed)
 report['load']=client.call('world.load',{'worldId':ident});print('LOAD',report['load'],flush=True)
 sub=client.call('state.subscribe',{'topics':['state']})['subscriptionId']
 # Toggle only the verified nested headless output; ctl refuses outer identities.
 session.ctl('eval','hl.config({misc={disable_watchdog_warning=true}})')
 session.ctl('eval','hl.plugin.hyprune.toggle("HEADLESS-1")');time.sleep(2)
 state=client.call('state.snapshot',{'subscriptionId':sub})['snapshot']['state'];report['snapshot']=state
 c=session.camera();report['camera']=c;assert c['active'] and c['frames']>0,c
 report['manifestSHA256']=hashlib.sha256((args.package/'world.json').read_bytes()).hexdigest()
 report['sceneSHA256']=hashlib.sha256((args.package/'scene.gltf').read_bytes()).hexdigest()
 subprocess.run([str(session.HERE/'ctl.py'),'shot',str(args.output/'nested-arrival.png')],check=True)
 before=state['movement']['position'];subprocess.run([str(session.HERE/'ctl.py'),'env','wtype','-P','w','-s','650','-p','w'],check=True);time.sleep(.2)
 after=client.call('state.snapshot',{'subscriptionId':sub})['snapshot']['state']['movement']['position'];assert abs(after[2]-before[2])>.3,(before,after);report['walk']={'before':before,'after':after}
 # Shared camera poses and fixed core 60-degree vertical FOV; fly prevents gravity.
 client.call('movement.set',{'modeId':'com.hyprune.fly'})
 views=json.loads((Path(__file__).resolve().parents[1]/'switchyard/views.json').read_text())
 report['views']=[]
 def pose(position,target):
  x,by,bz=position;tx,ty,tz=target
  d=[tx-x,tz-bz,-ty+by];length=math.sqrt(sum(v*v for v in d))
  yaw=math.atan2(d[0],-d[2]);pitch=math.asin(d[1]/length)
  sy=math.sin(-yaw/2);cy=math.cos(-yaw/2);sp=math.sin(pitch/2);cp=math.cos(pitch/2)
  return {'position':[x,bz,-by],'orientation':[cy*sp,sy*cp,-sy*sp,cy*cp]}
 for view in views['views']:
  requested=pose(view['position'],view['target']);client.call('camera.set',requested);time.sleep(.6)
  actual=client.call('camera.get',{});assert abs(sum(a*b for a,b in zip(actual['orientation'],requested['orientation'])))>.99999
  assert max(abs(a-b) for a,b in zip(actual['position'],requested['position']))<.001
  path=args.output/('engine-'+view['id']+'.png');subprocess.run([str(session.HERE/'ctl.py'),'shot',str(path)],check=True)
  report['views'].append({'id':view['id'],'requested':requested,'actual':actual,'verticalFovDegrees':60,'path':str(path)})
 if args.record:
  record_walk(client,sub,pose)
 client.call('runtime.exit',{});time.sleep(.2);assert not session.camera()['active']
 report['status']='PASS';report['checks']=['world.load','snapshot','active nested rendering','walk at spawn','five matching IPC 0.2 camera poses and 60-degree vertical FOV','runtime.exit'];(args.output/'nested-report.json').write_text(json.dumps(report,indent=2)+'\n');print('PASS Switchyard nested load/render/walk/exit',flush=True)
def record_walk(client,subscription,pose):
 """Real M1 collision-checked walking; only turns set the camera orientation."""
 import signal
 sys.path.insert(0,str(Path(__file__).resolve().parent));import devenv
 gallery=devenv.video_dir()  # HYPRUNE_VIDEO_DIR (environment or dev.env); warns if unset
 output=gallery/'world-switchyard-engine.mp4';raw=args.output/'engine-walk-raw.mkv'
 client.call('movement.set',{'modeId':'com.hyprune.walk'})
 client.call('camera.set',pose([0,-10,1.7],[0,20,4.8]));time.sleep(.3)
 log=open(args.output/'engine-recorder.log','w')
 recorder=session.envrun('wf-recorder','-o','HEADLESS-1','-r','30','-D','--no-dmabuf','-c','libx264','-p','preset=ultrafast','-p','crf=20','-x','yuv420p','-f',str(raw),stdout=log,stderr=subprocess.STDOUT)
 started=time.monotonic();samples=[]
 def sample():
  state=client.call('state.snapshot',{'subscriptionId':subscription})['snapshot']['state']
  samples.append({'seconds':round(time.monotonic()-started,3),'position':state['movement']['position'],'autodrive':state['location']['autodrive']})
  return state
 def pause(seconds):
  until=time.monotonic()+seconds
  while time.monotonic()<until:sample();time.sleep(.10)
 def turn(yaw0,yaw1,pitch=.055):
  # Camera.set changes only orientation at the current, capsule-resolved position.
  start=time.monotonic()
  while time.monotonic()-start<1.0:
   t=min(1,time.monotonic()-start);t=t*t*(3-2*t);yaw=yaw0*(1-t)+yaw1*t
   current=client.call('camera.get',{});sy=math.sin(-yaw/2);cy=math.cos(-yaw/2);sp=math.sin(pitch/2);cp=math.cos(pitch/2)
   current['orientation']=[cy*sp,sy*cp,-sy*sp,cy*cp];client.call('camera.set',current);time.sleep(.05)
 def walk(target):
  client.call('route.set',{'points':[{'position':target}]});client.call('autodrive.start',{'speed':2.1})
  while time.monotonic()-started<26.3:
   time.sleep(.10)
   if not sample()['location']['autodrive']:break
 try:
  pause(.6);walk([0,1.7,4.5]);turn(0,-math.pi/4);walk([-14.67,1.7,4.5]);turn(-math.pi/4,0);walk([-14.67,1.7,-14]);turn(0,.43,.13)
  client.call('autodrive.stop',{})
  remaining=27.0-(time.monotonic()-started)
  if remaining>0:pause(remaining)
 finally:
  client.call('autodrive.stop',{});recorder.send_signal(signal.SIGINT);recorder.wait(timeout=15);log.close()
 subprocess.run(['ffmpeg','-y','-loglevel','error','-i',str(raw),'-an','-vf','scale=1920:1080:flags=lanczos:in_range=pc:out_range=tv','-r','30','-c:v','libx264','-preset','medium','-crf','22','-pix_fmt','yuv420p','-color_range','tv','-movflags','+faststart',str(output)],check=True)
 probe=json.loads(subprocess.check_output(['ffprobe','-v','error','-show_streams','-show_format','-of','json',str(output)]));v=probe['streams'][0]
 assert v['codec_name']=='h264' and v['pix_fmt']=='yuv420p' and v['width']==1920 and v['height']==1080
 assert 20<=float(probe['format']['duration'])<=30 and output.stat().st_size<40_000_000,probe['format']
 distance=sum(math.dist(a['position'],b['position']) for a,b in zip(samples,samples[1:]));assert distance>20,(distance,'walk did not progress')
 report['engineWalk']={'path':str(output),'bytes':output.stat().st_size,'distanceMeters':round(distance,3),'durationSeconds':float(probe['format']['duration']),'samples':samples,'method':'IPC 0.2 collision-checked route/autodrive, camera orientation turns, no position interpolation'}
 (args.output/'engine-video-probe.json').write_text(json.dumps(probe,indent=2)+'\n')
 (gallery/'world-switchyard-engine.json').write_text(json.dumps({'title':'World: Switchyard / in-engine walk','tag':'world','notes':'Actual core M1 GLES3 rendering in a verified, isolated nested Hyprland. 27-second collision-checked walk from arrival through the concourse to the Studio approach, with a settled dock view. Same original CC-BY-4.0 Switchyard 0.1.1 package as the matching Cycles beauty views. No composited Blender imagery or simulated telemetry.'},indent=2)+'\n')
 shutil.copy2(output,args.output/output.name);shutil.copy2(gallery/'world-switchyard-engine.json',args.output/'world-switchyard-engine.json')
 print('PASS engine walk video',output,round(distance,2),'m',flush=True)

session.smoke=smoke
session.m1=lambda *unused:None
# Package smoke does not run core's separate client-crash fault-injection suite.
if hasattr(session,'failures'):session.failures=lambda *unused:None
# Give the existing harness a private startup config; do not edit core's config.
# Its verified ctl still checks the exact launched config/PID/start time/signature.
config=args.output.resolve()/'nested-hyprland.lua'
config.write_text((session.HERE/'hyprland.lua').read_text()+'\nhl.config({misc={disable_watchdog_warning=true},cursor={inactive_timeout=1}})\n')
source=inspect.getsource(session.run);needle="config=str(HERE/'hyprland.lua')";assert source.count(needle)==1,'core harness config API changed'
source=source.replace(needle,'config='+repr(str(config)))
exec(compile(source,str(session.HERE/'session.py'),'exec'),session.__dict__)
with open('/tmp/worldshell-nested.lock','a') as lock:
 fcntl.flock(lock,fcntl.LOCK_EX)
 try:session.run(SimpleNamespace(serve=False,record=False,m1=True))
 except Exception as e:
  report['status']='FAIL';report['error']=str(e);(args.output/'nested-report.json').write_text(json.dumps(report,indent=2)+'\n');raise
