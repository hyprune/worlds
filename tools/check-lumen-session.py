#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Lumen Reach scenario in the same locked core nested harness as hyprune-dev.
Only ctl.py's verified nested PID/socket/config/controller may touch Wayland.
"""
import argparse,fcntl,hashlib,inspect,json,math,os,shutil,signal,subprocess,sys,time
from pathlib import Path
from types import SimpleNamespace
ROOT=Path(__file__).resolve().parents[1]
p=argparse.ArgumentParser();p.add_argument('--core',type=Path,default=ROOT.parent/'core');p.add_argument('--package',type=Path,default=ROOT/'dist/com.hyprune.lumen-reach');p.add_argument('--output',type=Path,default=ROOT/'artifacts/lumen-reach');p.add_argument('--record',action='store_true');p.add_argument('--profile',action='store_true');p.add_argument('--release-review',action='store_true');p.add_argument('--diagnose',action='store_true');p.add_argument('--routes',action='store_true');p.add_argument('--gallery',action='store_true');p.add_argument('--vault-clip',action='store_true');a=p.parse_args();
if a.diagnose:a.record=True
if a.record and a.routes:p.error('Run --routes and --record in separate fresh sessions; shell launch grants expire after 30 seconds.')
a.output.mkdir(parents=True,exist_ok=True)
sys.path.insert(0,str(a.core/'dev/nested'));import session
session.STATE=a.output.resolve()/'.nested-state';os.environ['HYPRUNE_NESTED_STATE_DIR']=str(session.STATE)
import integration
from ctl import verified
report={'coreDirty':subprocess.check_output(['git','-C',str(a.core),'status','--short'],text=True).splitlines(),'coreDiffSHA256':hashlib.sha256(subprocess.check_output(['git','-C',str(a.core),'diff','HEAD'])).hexdigest(),'coreCommit':subprocess.check_output(['git','-C',str(a.core),'rev-parse','HEAD'],text=True).strip(),'pluginSHA256':hashlib.sha256((a.core/'build/hyprune-core.so').read_bytes()).hexdigest()}

gpu_next=0
def gpu_sample():
 global gpu_next
 if time.monotonic()<gpu_next:return
 gpu_next=time.monotonic()+1;verified_state,_=verified();seen=set();total=0;resident=0
 def size(value):
  bits=value.split();return float(bits[0])*{'KiB':1024,'MiB':1024**2,'GiB':1024**3}.get(bits[1] if len(bits)>1 else '',1)
 for fd in Path(f'/proc/{verified_state['pid']}/fdinfo').iterdir():
  try:fields=dict(line.split(':',1) for line in fd.read_text().splitlines() if ':' in line)
  except OSError:continue
  cid=fields.get('drm-client-id')
  if not cid or cid in seen:continue
  seen.add(cid);total+=size(fields.get('drm-total-gtt','0'));resident+=size(fields.get('drm-resident-gtt','0'))
 peak=report.setdefault('gpuSampling',{'method':'unique nested DRM client IDs, fdinfo GTT, at most one sample per second','samples':0,'peakTotalGttBytes':0,'peakResidentGttBytes':0})
 peak['samples']+=1;peak['peakTotalGttBytes']=max(peak['peakTotalGttBytes'],int(total));peak['peakResidentGttBytes']=max(peak['peakResidentGttBytes'],int(resident))

def pose(position,target):
 x,y,z=position;tx,ty,tz=target;d=[tx-x,tz-z,y-ty];length=math.sqrt(sum(v*v for v in d));yaw=math.atan2(d[0],-d[2]);pitch=math.asin(d[1]/length)
 sy=math.sin(-yaw/2);cy=math.cos(-yaw/2);sp=math.sin(pitch/2);cp=math.cos(pitch/2)
 return {'position':[x,z,-y],'orientation':[cy*sp,sy*cp,-sy*sp,cy*cp]}
def capture(client,children,args,shell_token,socketpath):
 manifest=json.loads((a.package/'world.json').read_text());ident=manifest['id'];assert ident=='com.hyprune.lumen-reach'
 report['coreCommit']=subprocess.check_output(['git','-C',str(a.core),'rev-parse','HEAD'],text=True).strip()
 loaded=max(session.STATE.glob('hyprune-*.so'),key=lambda p:p.stat().st_mtime_ns)
 report['loadedPluginSHA256']=hashlib.sha256(loaded.read_bytes()).hexdigest();report['protocol']=client.hello['protocol']
 installed=session.STATE/'worlds'/ident
 if installed.exists():shutil.rmtree(installed)
 shutil.copytree(a.package,installed)
 report['load']=client.call('world.load',{'worldId':ident});sub=client.call('state.subscribe',{'topics':['state']})['subscriptionId']
 def state():
  result=client.call('state.snapshot',{'subscriptionId':sub})['snapshot']['state']
  if a.record:gpu_sample()
  return result
 session.ctl('eval','hl.config({misc={disable_watchdog_warning=true},cursor={inactive_timeout=1}})')
 session.ctl('eval','hl.dispatch(hl.dsp.focus({ monitor = "HEADLESS-1" }))')
 quality='medium'
 try:session.ctl('eval','hl.plugin.hyprune.config({graphics={quality="medium",render_scale="auto",target_fps=60}})')
 except subprocess.CalledProcessError:
  quality='intel';session.ctl('eval','hl.plugin.hyprune.config({graphics={quality="intel",render_scale="auto",target_fps=60}})')
 session.ctl('eval','hl.plugin.hyprune.toggle("HEADLESS-1")');time.sleep(2)
 assert state()['runtime']['active'];report['camera']=session.camera()
 if quality=='medium':assert report['camera']['timings']['graphics']['quality']=='medium','Medium preset did not take effect'
 report['graphicsRequest']={'quality':quality,'render_scale':'auto','target_fps':60}
 report['manifestSHA256']=hashlib.sha256((a.package/'world.json').read_bytes()).hexdigest();report['sceneSHA256']=hashlib.sha256((a.package/'scene.gltf').read_bytes()).hexdigest()
 # Real walk from default spawn, before any camera positioning.
 before=state()['movement']['position'];integration.keys('-P','w','-s','500','-p','w');time.sleep(.2);after=state()['movement']['position'];assert math.dist(before,after)>.3,(before,after);report['walk']={'before':before,'after':after}
 client.call('movement.set',{'modeId':'com.hyprune.fly'});time.sleep(1)
 report['views']=[];views=json.loads((a.output/'views.json').read_text())['views']
 for v in views:
  if a.record and v['id'].count('-')>2:continue # shell launch grant has a 30-second lifetime
  requested=pose(v['position'],v['target']);client.call('camera.set',requested);time.sleep(.8);actual=client.call('camera.get',{})
  assert max(abs(x-y) for x,y in zip(requested['position'],actual['position']))<.001,(v['id'],requested,actual)
  assert abs(sum(x*y for x,y in zip(requested['orientation'],actual['orientation'])))>.99999
  if a.profile and v['id'].count('-')==2:
   time.sleep(2);samples=[]
   for _ in range(30):samples.append({**session.camera()['timings'],'sampleMonotonic':time.monotonic()});time.sleep(.07)
   report.setdefault('performanceViews',[]).append({'id':v['id'],'samples':samples})
  path=a.output/('engine-'+v['id']+'.png');subprocess.run([str(session.HERE/'ctl.py'),'shot',str(path)],check=True);report['views'].append({'renderer':session.camera().get('timings',{}),'id':v['id'],'pose':actual,'verticalFovDegrees':60,'path':str(path)})
 if a.gallery:
  gallery=Path.home()/'workspace/rick-the-alien/worldshell-gallery/screenshots/release-world-v2';gallery.mkdir(parents=True,exist_ok=True)
  for v in report['views']:shutil.copy2(v['path'],gallery/Path(v['path']).name)
 if a.vault_clip:vault_clip(client,manifest)
 if a.routes:route_check(client,state,manifest)
 if a.record:record(client,children,state,shell_token,socketpath)
 verified_state,_=verified();gpu=[];seen=set()
 for fd in Path(f'/proc/{verified_state["pid"]}/fdinfo').iterdir():
  try:fields=dict(line.split(':',1) for line in fd.read_text().splitlines() if ':' in line)
  except OSError:continue
  cid=fields.get('drm-client-id')
  if cid and cid not in seen:
   seen.add(cid);gpu.append({k:v.strip() for k,v in fields.items() if k.startswith('drm-')})
 report['nestedDrmClients']=gpu
 client.call('runtime.exit',{});time.sleep(.3);assert not session.camera()['active'];report['status']='PASS';report['checks']=['package load','real spawn walking','matching 60 degree views','clean nested exit'];(a.output/'nested-report.json').write_text(json.dumps(report,indent=2)+'\n');print('PASS Lumen Reach nested capture',flush=True)

def vault_clip(client,manifest):
 """Short real engine camera motion for a matched before/after comparison."""
 import tempfile
 staging=Path(tempfile.mkdtemp(prefix='rime-v3-',dir='/tmp'))
 raw=staging/'vault.mkv';encoded=staging/'vault.mp4'
 views=json.loads((a.output/'views.json').read_text())['views']
 ids=['03-rime-vault','03-rime-vault-services','03-rime-vault-platform']
 selected=[next(v for v in views if v['id']==ident) for ident in ids]
 client.call('movement.set',{'modeId':'com.hyprune.fly'})
 client.call('camera.set',pose(selected[0]['position'],selected[0]['target']));time.sleep(1)
 with (a.output/'vault-recorder.log').open('w') as log:
  rec=session.envrun('wf-recorder','-o','HEADLESS-1','-r','30','-D','--no-dmabuf','-c','libx264','-p','preset=ultrafast','-p','crf=19','-x','yuv420p','-f',str(raw),stdout=log,stderr=subprocess.STDOUT)
  try:
   started=time.monotonic()
   for v in selected:
    phase=time.monotonic()
    while time.monotonic()-phase<7:
     t=min(1,(time.monotonic()-phase)/7);position=list(v['position']);position[0]+=.20*math.sin(t*math.pi)
     client.call('camera.set',pose(position,v['target']));time.sleep(.05)
   elapsed=time.monotonic()-started
  finally:rec.send_signal(signal.SIGINT);rec.wait(timeout=15)
 subprocess.run(['ffmpeg','-y','-v','error','-i',str(raw),'-an','-vf','scale=1920:1080:in_range=pc:out_range=tv','-r','30','-c:v','libx264','-preset','medium','-crf','20','-pix_fmt','yuv420p','-color_range','tv','-movflags','+faststart',str(encoded)],check=True)
 probe=json.loads(subprocess.check_output(['ffprobe','-v','error','-show_format','-of','json',str(encoded)]))
 assert 20<=float(probe['format']['duration'])<=25
 shutil.move(str(encoded),a.output/'vault.mp4')
 report['vaultClip']={'version':manifest['version'],'views':ids,'duration':probe['format']['duration'],'encodedIn':str(staging),'motion':'20cm sine pan over seven seconds per fixed target','elapsedSeconds':elapsed}
 print('PASS matched Vault motion clip',flush=True)

def route_check(client,state,manifest):
 """Traverse every graph branch and authored alternate stair in real walk mode."""
 ext=manifest['extensions'];graph=ext['com.hyprune.lumen-reach.routes'];nodes={n['id']:n['position'] for n in graph['nodes']};adj={n:[] for n in nodes}
 for e in graph['edges']:adj[e['from']].append(e['to']);adj[e['to']].append(e['from'])
 traversed=[];seen={'arrival'};order=[]
 def visit(node):
  for other in adj[node]:
   if other not in seen:seen.add(other);order.append((node,other));visit(other);order.append((other,node))
 visit('arrival');assert len(seen)==len(nodes)
 client.call('movement.set',{'modeId':'com.hyprune.walk'});eye=lambda p:[p[0],p[1]+1.7,p[2]]
 def drive(start,end,label):
  client.call('route.set',{'points':[{'position':eye(start)},{'position':eye(end)}]});client.call('autodrive.start',{'speed':10})
  integration.wait_for(lambda:not state()['location']['autodrive'],20)
  actual=state()['movement']['position'];assert math.dist(actual,eye(end))<.15,('blocked real walking path',label,actual,eye(end));traversed.append({'path':label,'end':actual})
 client.call('camera.set',{'position':eye(nodes['arrival']),'orientation':[0,0,0,1]})
 for i,(left,right) in enumerate(order):
  drive(nodes[left],nodes[right],left+' -> '+right)
  if i%20==0:print('Route audit',i+1,'/',len(order),flush=True)
 for flight in ext.get('com.hyprune.lumen-reach.stairs',{}).get('paths',[]):
  client.call('camera.set',{'position':eye(flight['from']),'orientation':[0,0,0,1]});drive(flight['from'],flight['to'],flight['id'])
 report['routeTraversal']={'status':'PASS','nodes':len(seen),'directedGraphTraversals':len(order),'alternateStairs':len(traversed)-len(order),'traversed':traversed}
 print('PASS real graph branches and stair flights',flush=True)


def record(client,children,state,shell_token,socketpath):
 """Real applications and HUD, followed by capsule-checked route traversal."""
 import tempfile
 recording_dir=Path(tempfile.mkdtemp(prefix='lumen-tour-v2-',dir='/tmp'))
 output=recording_dir/'release-world-tour-v2.mp4';raw=recording_dir/'release-world-tour-v2.mkv'
 manifest=json.loads((a.package/'world.json').read_text());areas=manifest['extensions']['com.hyprune.lumen-reach.mounts']['areas']
 mounts=manifest['extensions']['com.hyprune.lumen-reach.mounts']['mounts'];terminals=[]
 def wait(check,timeout=20):return integration.wait_for(check,timeout)
 def pause(seconds):
  end=time.monotonic()+seconds
  while time.monotonic()<end:state();time.sleep(.1)
 # Launch actual authenticated shell child, exactly as core's first-session harness.
 read,write=os.pipe();os.write(write,(shell_token+'\n').encode());os.close(write)
 _,environment=verified();environment.update(HYPRUNE_TOKEN_FD=str(read),HYPRUNE_PROTOCOL='0.7',HYPRUNE_SOCKET=str(socketpath),HYPRUNE_OUTPUT_SCREEN='HEADLESS-1',HYPRUNE_DEV_AUTOMATION='1')
 log=open(a.output/'tour-shell.log','w');shell=subprocess.Popen(['python3',str(a.core.parent/'shell/bridge/launch.py'),'--protocol','0.7'],env=environment,pass_fds=(read,),stdout=log,stderr=subprocess.STDOUT);os.close(read);children.append(shell)
 def childpid():
  assert shell.poll() is None,'shell failed; see tour-shell.log'
  return next((int(p) for p in Path(f'/proc/{shell.pid}/task/{shell.pid}/children').read_text().split() if Path(f'/proc/{p}/comm').read_text().strip()=='qs'),None)
 pid=wait(childpid)
 def ui(command,*values):
  verified();assert pid in list(map(int,Path(f'/proc/{shell.pid}/task/{shell.pid}/children').read_text().split()))
  return subprocess.check_output([str(session.HERE/'ctl.py'),'env','qs','ipc','--pid',str(pid),'call','preview',command,*map(str,values)],text=True).strip()
 def hud():
  try:return json.loads(ui('status'))
  except (subprocess.CalledProcessError,json.JSONDecodeError):return {}
 wait(lambda:hud().get('lease'))
 assert 'hyprune-hud' in json.dumps(json.loads(session.ctl('layers','-j'))['HEADLESS-1'])
 for i,area in enumerate(areas):
  wid=10+i;client.call('workspace.bind',{'id':wid,'worldId':manifest['id'],'areaId':area['id']})
  session.ctl('dispatch',f'hl.dsp.focus({{ workspace = "{wid}" }})');pause(.8)
  for kind in ['Home','Bench']:
   title='Lumen Reach / '+area['id']+' / '+kind
   rc=a.output/(area['id']+'-'+kind+'.bashrc');rc.write_text("PS1='\\[\\e[38;5;110m\\]reach \\w > \\[\\e[0m\\]'\nclear\nprintf '\\033[1;33mLUMEN REACH / "+area['id'].upper()+"\\033[0m\\n\\nA live terminal in workspace home "+area['workspaceSlot']+".\\n\\n'\n")
   program=['bash','--noprofile','--rcfile',str(rc.resolve())]
   if kind=='Home':
    config=a.output/(area['id']+'.btop.conf');config.write_text('shown_boxes = \"cpu mem proc\"\nupdate_ms = 1000\n');program=['btop','--force-utf','--config',str(config.resolve())]
   children.append(session.envrun('kitty','--class','lumen-'+area['id']+'-'+kind.lower(),'--title',title,'--override','initial_window_width='+('900' if kind=='Home' else '700'),'--override','initial_window_height='+('600' if kind=='Home' else '394'),'--override','font_size='+('10' if kind=='Home' else '24'),*program,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL))
   surface=wait(lambda:next((s for s in state()['surfaces'] if s['title']==title),None))
   window=next(w for w in json.loads(session.ctl('clients','-j')) if w.get('title')==title)
   monitor=next(m['id'] for m in json.loads(session.ctl('monitors','-j')) if m['name']=='HEADLESS-1')
   assert window['monitor']==monitor and window['workspace']['id']==wid,('application on wrong nested output/workspace',title,window['monitor'],window['workspace'])
   width,height=(1920,1080) if kind=='Home' else (700,394)
   address=window['address'];session.ctl('eval',f'hl.dispatch(hl.dsp.window.float({{window="address:{address}",action="enable"}}))');session.ctl('eval',f'hl.dispatch(hl.dsp.window.resize({{window="address:{address}",x={width},y={height}}}))')
   window=next(w for w in json.loads(session.ctl('clients','-j')) if w.get('title')==title)
   report.setdefault('nativeApplications',[]).append({k:window[k] for k in ['title','address','monitor','workspace','at','size','floating']})
   if kind=='Home':
    pause(2) # allow first terminal repaint before another surface occludes it
    # Current core places newly launched applications in a free area. Return the
    # Home application explicitly so it participates in its workspace composite.
    client.call('surface.return',{'surfaceId':surface['id']})
   if kind=='Bench':
    kindname='lectern' if area['id']=='array-hall' else 'terminal-bench' if area['id']=='signal-rise' else 'operator-desk'
    anchor=next(r['anchorId'] for r in mounts if r['areaId']==area['id'] and r['mountType']==kindname)
    client.call('surface.pull',{'surfaceId':surface['id']});client.call('surface.place',{'surfaceId':surface['id'],'anchorId':anchor});terminals.append({'areaId':area['id'],'surfaceId':surface['id'],'anchorId':anchor})
 client.call('workspace.activate',{'id':10});pause(2)
 # Prove keyboard input reaches the placed terminal before shooting the tour.
 first=terminals[0];client.call('surface.focus',{'surfaceId':first['surfaceId'],'intent':'keyboard'})
 marker=a.output/'tour-typed.txt';marker.unlink(missing_ok=True)
 integration.keys(f"printf 'Live input in Lumen Reach\\n' > {marker.resolve()}");integration.keys('-k','Return');wait(marker.exists);integration.keys('-k','Escape')
 client.call('movement.set',{'modeId':'com.hyprune.fly'})
 liveviews=[('sun-court',[-12,-11.5,2.1],[-15,-7.5,1.95]),('array-hall',[-1,35.5,2.1],[-1,39.85,1.95]),('rime-vault',[33.6,77,-4.3],[33.6,81,-4.02]),('signal-rise',[41,118,2.1],[41,123,1.95])]
 for area,position,target in liveviews:
  client.call('camera.set',pose(position,target));pause(.6);subprocess.run([str(session.HERE/'ctl.py'),'shot',str((a.output/('live-'+area+'.png')).resolve())],check=True)
 report['mountedApplicationState']=state()['mounts']
 report['capturesAfterSetup']=session.camera()['captures']
 assert hud().get('status')=='live','Shell must remain connected after application setup'
 homes=[c for c in report['capturesAfterSetup'] if c['title'].endswith(' / Home')]
 assert len(homes)==4 and all(not c['visible'] for c in homes),'Home applications must remain in workspace composites'
 for v in json.loads((a.output/'views.json').read_text())['views']:
  if v['id'].count('-')!=2:continue
  client.call('camera.set',pose(v['position'],v['target']));pause(.6);subprocess.run([str(session.HERE/'ctl.py'),'shot',str((a.output/('live-workspace-'+v['id']+'.png')).resolve())],check=True)
 if a.diagnose:
  report['beforeDiagnostics']=session.camera()
  report['nativeAfterSetup']=json.loads(session.ctl('clients','-j'))
  for v in json.loads((a.output/'views.json').read_text())['views']:
   if v['id'].count('-')!=2:continue
   client.call('camera.set',pose(v['position'],v['target']));pause(1);subprocess.run([str(session.HERE/'ctl.py'),'shot',str((a.output/('live-workspace-'+v['id']+'.png')).resolve())],check=True)
  home=next(s for s in state()['surfaces'] if s['title']=='Lumen Reach / array-hall / Home')
  anchor=next(r['anchorId'] for r in mounts if r['areaId']=='array-hall' and r['mountType']=='operator-desk')
  client.call('surface.pull',{'surfaceId':home['id']});client.call('surface.place',{'surfaceId':home['id'],'anchorId':anchor})
  client.call('camera.set',pose([-2,57,2.1],[-2,53,1.95]));pause(2);subprocess.run([str(session.HERE/'ctl.py'),'shot',str((a.output/'diagnostic-array-source.png').resolve())],check=True)
  report['afterDiagnostics']=session.camera();client.call('surface.return',{'surfaceId':home['id']});log.close();return

 client.call('movement.set',{'modeId':'com.hyprune.walk'})
 client.call('camera.set',pose([-12,-11,1.7],[-15,-7.5,1.95]))
 rec_log=open(a.output/'tour-recorder.log','w')
 recorder=session.envrun('wf-recorder','-o','HEADLESS-1','-r','30','-D','--no-dmabuf','-c','libx264','-p','preset=ultrafast','-p','crf=19','-x','yuv420p','-f',str(raw.resolve()),stdout=rec_log,stderr=subprocess.STDOUT)
 started=time.monotonic();traversals=[]
 nodes={n['id']:n['position'] for n in manifest['extensions']['com.hyprune.lumen-reach.routes']['nodes']}
 def orient(target):
  pos=state()['movement']['position'];current=session.camera();y0=current['yaw'];p0=current['pitch'];dx=target[0]-pos[0];dy=target[1]+pos[2];dz=target[2]-pos[1];y1=math.atan2(dx,dy);p1=math.atan2(dz,math.hypot(dx,dy));delta=(y1-y0+math.pi)%(2*math.pi)-math.pi
  for i in range(13):
   t=i/12;e=t*t*(3-2*t);yaw=y0+delta*e;pitch=p0+(p1-p0)*e;sy=math.sin(-yaw/2);cy=math.cos(-yaw/2);sp=math.sin(pitch/2);cp=math.cos(pitch/2);client.call('camera.set',{'position':pos,'orientation':[cy*sp,sy*cp,-sy*sp,cy*cp]});time.sleep(.045)
 def drive(ids,label,speed=4):
  pts=[[nodes[n][0],nodes[n][1]+1.7,nodes[n][2]] for n in ids]
  client.call('waypoint.set',{'id':ids[-1],'label':label,'position':pts[-1]});client.call('route.set',{'points':[{'position':p} for p in pts]});client.call('autodrive.start',{'speed':speed})
  wait(lambda:not state()['location']['autodrive'],60)
  actual=state()['movement']['position'];assert math.dist(actual,pts[-1])<.15,('blocked tour route',ids,actual,pts[-1]);traversals.append({'ids':ids,'reached':actual,'capsuleChecked':True})
 try:
  pause(1);client.call('surface.focus',{'surfaceId':first['surfaceId'],'intent':'keyboard'});integration.keys('-d','24',"printf 'Four homes connected. Tools stay with their home.\\n'");integration.keys('-k','Return');pause(2);integration.keys('-k','Escape')
  orient([8,24,5]);drive(['arrival','court-junction','court-wall','hall-entry','hall-arrival'],'Array Hall',4.5)
  orient([-1,39.85,1.95]);pause(2);orient([8,48,10]);pause(3)
  drive(['hall-center'],'Atrium',3.5);orient([20,50,1]);drive(['hall-exit','service-entry'],'Service descent',4.5)
  orient([30,76,-4]);drive(['descent-top','descent-bottom'],'Rime Vault descent',3.8)
  orient([38,99,-.1]);drive(['vault-door','vault-arrival'],'Rime Vault',4);orient([33.6,81,-4.02]);pause(2);orient([39,99,-.1]);drive(['vault-center'],'Lower workspace',4);pause(3)
  orient([54,100,-4]);drive(['vault-exit','rise-entry'],'Signal Rise passage',4.5)
  orient([54,124,2]);drive(['rise-ramp-top','rise-arrival'],'Signal Rise ascent',4.5)
  orient([41,123,1.95]);pause(2);orient([57,148,8]);drive(['rise-ring','rise-wall'],'Signal Rise',4);pause(4)
  orient([35,149,10]);pause(5)
  pause(max(0,76-(time.monotonic()-started)))
 finally:
  recorder.send_signal(signal.SIGINT);recorder.wait(timeout=15);rec_log.close()
 subprocess.run(['ffmpeg','-y','-loglevel','error','-i',str(raw),'-an','-vf','scale=1920:1080:flags=lanczos:in_range=pc:out_range=tv','-r','30','-c:v','libx264','-preset','medium','-crf','22','-maxrate','6500k','-bufsize','13000k','-pix_fmt','yuv420p','-color_range','tv','-movflags','+faststart',str(output)],check=True)
 probe=json.loads(subprocess.check_output(['ffprobe','-v','error','-show_streams','-show_format','-of','json',str(output)]));assert 60<=float(probe['format']['duration'])<=90
 assert hud().get('status')=='live','Shell must remain connected throughout recording'
 notes='Real nested Hyprland and Hyprune engine with authenticated shell IPC 0.7, Quickshell HUD, four mounted workspace homes and four real pulled-out terminal windows on owned physical mounts. Real terminal keyboard input verified before recording and typed visibly at the opening. Collision-checked auto-drive walks the connected roads, interior passage, lower service descent and snowy ascent; view turns occur while stationary. Original procedural world and generated textures, CC-BY-4.0. No owner-session control. GPU/package figures and exact engine hashes are in worlds/lumen-reach/reports.'
 output.with_suffix('.json').write_text(json.dumps({'title':'Lumen Reach v2 — four inhabited workspace homes','tag':'world','notes':notes},indent=2)+'\n')
 report['tour']={'duration':probe['format']['duration'],'bytes':output.stat().st_size,'terminals':terminals,'typed':marker.read_text(),'traversals':traversals,'hud':{k:v for k,v in hud().items() if k in ['status','protocol','screen','revision','phase','world','map','places']}};log.close()
 staged=a.output/output.name;shutil.move(str(output),staged);shutil.move(str(output.with_suffix('.json')),staged.with_suffix('.json'));report['tour']['path']=str(staged);report['tour']['encodedIn']=str(recording_dir)
 print('PASS recorded tour',staged,flush=True)


integration.first_session=capture
# A private nested startup config; the exact PID/config remains verified by ctl.
config=a.output.resolve()/'nested-hyprland.lua';config.write_text((session.HERE/'hyprland.lua').read_text()+'''
for slot=10,13 do hl.workspace_rule({workspace=tostring(slot),monitor="HEADLESS-1"}) end
hl.window_rule({name="lumen-capture-size",match={class="^lumen-.*"},float=true,size="900 600",center=true})
hl.window_rule({name="lumen-bench-position",match={class="^lumen-.*-bench$"},center=false,size="700 394",move="30 650"})
'''+ '\nhl.config({misc={disable_watchdog_warning=true},cursor={inactive_timeout=1}})\n')
source=inspect.getsource(session.run);needle="config=str(HERE/'hyprland.lua')";assert source.count(needle)==1
source=source.replace(needle,'config='+repr(str(config)))
# run() ordinarily replaces STATE for its stock integration fixtures.
assert source.count("STATE=HERE/'.integration-state'")==1
source=source.replace("STATE=HERE/'.integration-state'",'STATE='+repr(session.STATE))
# Path repr requires pathlib in the imported harness namespace.
source=source.replace('STATE=PosixPath(', 'STATE=pathlib.Path(')
if a.record or a.release_review:source=source.replace('"0.3" if args.integration', '"0.4" if args.integration')
exec(compile(source,str(session.HERE/'session.py'),'exec'),session.__dict__)
with open('/tmp/worldshell-nested.lock','a') as lock:
 fcntl.flock(lock,fcntl.LOCK_EX)
 (session.STATE/'layout.json').unlink(missing_ok=True)
 try:
  if a.release_review:
   base=a.output;initial=json.loads(json.dumps(report));views=(base/'views.json').read_text();index=[]
   for phase in ['v2-4k','v2-routes','v2-tour']:
    a.output=base/phase;a.output.mkdir(exist_ok=True);(a.output/'views.json').write_text(views)
    a.record=phase=='v2-tour';a.routes=phase=='v2-routes';a.profile=phase=='v2-4k';report=json.loads(json.dumps(initial))
    os.environ['HYPRUNE_NESTED_4K']='1' if a.profile else '0'
    (session.STATE/'layout.json').unlink(missing_ok=True)
    print('Release verification phase:',phase,flush=True)
    session.run(SimpleNamespace(serve=False,record=False,m1=False,m2=False,m3a=False,m3b=False,live=False,integration=True,visible=False))
    index.append({'phase':phase,'report':str(a.output/'nested-report.json'),'status':report['status']})
    (base/'release-review-index.json').write_text(json.dumps(index,indent=2)+'\n')
  else:session.run(SimpleNamespace(serve=False,record=False,m1=False,m2=False,m3a=False,m3b=False,live=False,integration=True,visible=False))
 except Exception as e:report['status']='FAIL';report['error']=str(e);(a.output/'nested-report.json').write_text(json.dumps(report,indent=2)+'\n');raise
