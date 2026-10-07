#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Lumen Reach scenario in the same locked core nested harness as hyprune-dev.
Only ctl.py's verified nested PID/socket/config/controller may touch Wayland.
"""
import argparse,fcntl,hashlib,inspect,json,math,os,shutil,signal,subprocess,sys,time
from pathlib import Path
from types import SimpleNamespace
ROOT=Path(__file__).resolve().parents[1]
p=argparse.ArgumentParser();p.add_argument('--core',type=Path,default=ROOT.parent/'core');p.add_argument('--package',type=Path,default=ROOT/'dist/com.hyprune.lumen-reach');p.add_argument('--output',type=Path,default=ROOT/'artifacts/lumen-reach');p.add_argument('--record',action='store_true');p.add_argument('--gallery',action='store_true');a=p.parse_args();a.output.mkdir(parents=True,exist_ok=True)
sys.path.insert(0,str(a.core/'dev/nested'));import session,integration
from ctl import verified
report={'coreCommit':subprocess.check_output(['git','-C',str(a.core),'rev-parse','HEAD'],text=True).strip(),'pluginSHA256':hashlib.sha256((a.core/'build/hyprune-core.so').read_bytes()).hexdigest()}

def pose(position,target):
 x,y,z=position;tx,ty,tz=target;d=[tx-x,tz-z,y-ty];length=math.sqrt(sum(v*v for v in d));yaw=math.atan2(d[0],-d[2]);pitch=math.asin(d[1]/length)
 sy=math.sin(-yaw/2);cy=math.cos(-yaw/2);sp=math.sin(pitch/2);cp=math.cos(pitch/2)
 return {'position':[x,z,-y],'orientation':[cy*sp,sy*cp,-sy*sp,cy*cp]}
def capture(client,children,args,shell_token,socketpath):
 manifest=json.loads((a.package/'world.json').read_text());ident=manifest['id'];assert ident=='com.hyprune.lumen-reach'
 installed=session.STATE/'worlds'/ident
 if installed.exists():shutil.rmtree(installed)
 shutil.copytree(a.package,installed)
 report['load']=client.call('world.load',{'worldId':ident});sub=client.call('state.subscribe',{'topics':['state']})['subscriptionId']
 def state():return client.call('state.snapshot',{'subscriptionId':sub})['snapshot']['state']
 session.ctl('eval','hl.config({misc={disable_watchdog_warning=true},cursor={inactive_timeout=1}})')
 session.ctl('eval','hl.dispatch(hl.dsp.focus({ monitor = "HEADLESS-1" }))')
 session.ctl('eval','hl.plugin.hyprune.toggle("HEADLESS-1")');time.sleep(2)
 assert state()['runtime']['active'];report['camera']=session.camera()
 report['manifestSHA256']=hashlib.sha256((a.package/'world.json').read_bytes()).hexdigest();report['sceneSHA256']=hashlib.sha256((a.package/'scene.gltf').read_bytes()).hexdigest()
 # Real walk from default spawn, before any camera positioning.
 before=state()['movement']['position'];integration.keys('-P','w','-s','500','-p','w');time.sleep(.2);after=state()['movement']['position'];assert math.dist(before,after)>.3,(before,after);report['walk']={'before':before,'after':after}
 client.call('movement.set',{'modeId':'com.hyprune.fly'})
 report['views']=[];views=json.loads((a.output/'views.json').read_text())['views']
 for v in views:
  requested=pose(v['position'],v['target']);client.call('camera.set',requested);time.sleep(.8);actual=client.call('camera.get',{})
  assert max(abs(x-y) for x,y in zip(requested['position'],actual['position']))<.001
  assert abs(sum(x*y for x,y in zip(requested['orientation'],actual['orientation'])))>.99999
  path=a.output/('engine-'+v['id']+'.png');subprocess.run([str(session.HERE/'ctl.py'),'shot',str(path)],check=True);report['views'].append({'id':v['id'],'pose':actual,'verticalFovDegrees':60,'path':str(path)})
 if a.gallery:
  gallery=Path.home()/'workspace/rick-the-alien/worldshell-gallery/screenshots/release-world';gallery.mkdir(parents=True,exist_ok=True)
  for v in report['views']:shutil.copy2(v['path'],gallery/Path(v['path']).name)
 if a.record:record(client,children,state,shell_token,socketpath)
 client.call('runtime.exit',{});time.sleep(.3);assert not session.camera()['active'];report['status']='PASS';report['checks']=['package load','real spawn walking','matching 60 degree views','clean nested exit'];(a.output/'nested-report.json').write_text(json.dumps(report,indent=2)+'\n');print('PASS Lumen Reach nested capture',flush=True)

integration.first_session=capture
# A private nested startup config; the exact PID/config remains verified by ctl.
config=a.output.resolve()/'nested-hyprland.lua';config.write_text((session.HERE/'hyprland.lua').read_text()+'\nhl.config({misc={disable_watchdog_warning=true},cursor={inactive_timeout=1}})\n')
source=inspect.getsource(session.run);needle="config=str(HERE/'hyprland.lua')";assert source.count(needle)==1
source=source.replace(needle,'config='+repr(str(config)))
exec(compile(source,str(session.HERE/'session.py'),'exec'),session.__dict__)
with open('/tmp/worldshell-nested.lock','a') as lock:
 fcntl.flock(lock,fcntl.LOCK_EX)
 try:session.run(SimpleNamespace(serve=False,record=False,m1=False,m2=False,integration=True,visible=False))
 except Exception as e:report['status']='FAIL';report['error']=str(e);(a.output/'nested-report.json').write_text(json.dumps(report,indent=2)+'\n');raise
