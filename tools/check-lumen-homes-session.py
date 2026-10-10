#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Lumen Reach screens end to end in a private flocked core nested session.

For a package (e.g. the format 0.7 release in dist-07/): core's homes 21-24
and the Director's locations; places, map and projected HUD map markers;
anchors by mount role and data objects as core publishes them; a real
window on each of workspaces 21-24 lands on that area's primary wall (frame
at the primary anchor, aimable from in front, still per wall) and its
workspace frame fills the 16:9 wall on both axes; and a real
window placed on every tool mount (surface.place) sits at that anchor.
Writes report.json and wall stills. Never live-session IPC.
"""
import argparse,fcntl,hashlib,inspect,json,math,os,shutil,subprocess,sys,time
from pathlib import Path
from types import SimpleNamespace
ROOT=Path(__file__).resolve().parents[1]
p=argparse.ArgumentParser(description=__doc__);p.add_argument('--core',type=Path,default=ROOT.parent/'core-optimise');p.add_argument('--package',type=Path,required=True);p.add_argument('--output',type=Path,required=True);a=p.parse_args()
a.output=a.output.resolve();a.output.mkdir(parents=True,exist_ok=True);a.package=a.package.resolve()
sys.path.insert(0,str(a.core/'dev/nested'))
manifest=json.loads((a.package/'world.json').read_text());WID=manifest['id']
HOMES=[(21,'sun-court'),(22,'array-hall'),(23,'rime-vault'),(24,'signal-rise')]
report={'status':'RUNNING','package':str(a.package),'version':manifest['version'],'formatVersion':manifest['formatVersion'],'manifestSHA256':hashlib.sha256((a.package/'world.json').read_bytes()).hexdigest(),
 'coreCommit':subprocess.check_output(['git','-C',str(a.core),'rev-parse','HEAD'],text=True).strip(),'checks':[]}
def save():(a.output/'report.json').write_text(json.dumps(report,indent=1)+'\n')
def check(name,ok,data=None):
 report['checks'].append({'name':name,'passed':bool(ok),'evidence':data});save();print(('PASS ' if ok else 'FAIL ')+name,flush=True)

def acceptance(client,children,args,shell_token,socketpath):
 # Imported here, as core's harnesses are (inside session.run).
 import session as s
 from m2 import wait
 def windows():return json.loads(s.ctl('clients','-j'))
 s.ctl('eval','hl.config({misc={disable_watchdog_warning=true},cursor={inactive_timeout=1}})');s.ctl('eval','hl.dispatch(hl.dsp.focus({ monitor = "HEADLESS-1" }))')
 client.call('world.load',{'worldId':WID})
 sub=client.call('state.subscribe',{'topics':['state']})['subscriptionId']
 def state():return client.call('state.snapshot',{'subscriptionId':sub})['snapshot']['state']
 s.ctl('eval','hl.plugin.hyprune.toggle("HEADLESS-1")');wait(lambda:s.camera()['active'])
 st=state();m=st['mounts']
 check('homes 21-24 from the world areas',[(b['id'],b['areaId']) for b in m['bindings']]==HOMES,m['bindings'])
 located={l['id']:l['label'] for l in st['workspaces']['locations']}
 check('Director lists the four homes',all(located.get(i)==ar for i,ar in HOMES),located)
 roles={}
 for an in m['anchors']:roles[an.get('mount',{}).get('role','none')]=roles.get(an.get('mount',{}).get('role','none'),0)+1
 check('anchors by role: 4 walls, 20 tool mounts',roles.get('mounted-workspace')==4 and roles.get('tool-mount')==20,roles)
 objects=m.get('objects') or m.get('dataObjects') or []
 check('37 data objects published',len(objects)==37,{'count':len(objects),'keys':sorted(m.keys())})
 sp=st['spatial'];places=(sp.get('world') or {}).get('places') or []
 check('Director places and map present',len(places)>0 and bool(sp.get('map')),{'places':[pl.get('label',pl.get('id')) for pl in places],'map':sorted((sp.get('map') or {}).keys())})
 markers=wait(lambda:((state()['spatial'].get('projection') or {}).get('markers')) or None)
 kinds={}
 for mk in markers:kinds[mk.get('kind','?')]=kinds.get(mk.get('kind','?'),0)+1
 check('HUD map markers projected',len(markers)>0,{'count':len(markers),'kinds':kinds,'example':markers[0]})
 # A real window on each home workspace lands on that area's primary wall.
 for id,area in HOMES:
  s.ctl('eval','hl.window_rule({name="home-'+str(id)+'",match={title="^Home-'+str(id)+'$"},workspace="'+str(id)+' silent"})')
  children.append(s.envrun('kitty','--title','Home-'+str(id),'--override','font_size=48','--override','cursor_blink_interval=0','bash','--noprofile','--norc','-c',f'printf "\\n  WORKSPACE {id}\\n  {area}\\n"; exec bash --noprofile --norc',stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL))
 anchors={x['id']:x for x in m['anchors']};areas={x['id']:x for x in m['areas']}
 client.call('movement.set',{'modeId':'com.hyprune.fly'})
 for id,area in HOMES:
  wait(lambda:any(w['title']=='Home-'+str(id) and w['workspace']['id']==id for w in windows()))
  an=anchors[areas[area]['primaryAnchor']]
  f=wait(lambda:next((f for f in s.camera()['workspaceFrames'] if f['workspaceId']==id),None))
  x,y,z,w=an['pose']['rotation'];pp=an['pose']['position'];n=[2*(x*z+w*y),2*(y*z-w*x),1-2*(x*x+y*y)];yaw=math.atan2(-n[0],n[2]);aim=None
  for d in [2.5,3.5,1.8,4.5]:
   s.ctl('eval',f'hl.plugin.hyprune.camera({pp[0]+n[0]*d},{pp[1]},{pp[2]+n[2]*d},{yaw},0)');time.sleep(.35)
   if s.camera()['aim']=='workspace-'+str(id):aim=d;break
  # Wide still from the standback so the whole wall is in frame.
  dd=max(8.0,an['size'][0]*.9);s.ctl('eval',f'hl.plugin.hyprune.camera({pp[0]+n[0]*dd},{pp[1]},{pp[2]+n[2]*dd},{yaw},0)');time.sleep(.6)
  shot=a.output/f'wall-{id}-{area}.png';subprocess.run([str(s.HERE/'ctl.py'),'shot',str(shot)],check=True,stdout=subprocess.DEVNULL)
  check(f'workspace {id} window on the {area} primary wall',math.dist(f['position'],pp)<.5 and aim is not None,{'frame':f,'anchor':an['id'],'aimDistance':aim,'still':str(shot)})
  # 0.9.1: core composes each home workspace into a 1280x720 frame fitted
  # into the primary anchor (surfaces::anchorPlane: width min(w, h*16/9)),
  # so only a 16:9 wall is filled on both axes; the home's real tiled window
  # is the monitor's aspect less the gaps (the capture's own pixels).
  c=next((c for c in s.camera()['captures'] if c['title']=='Home-'+str(id)),None)
  fw=min(an['size'][0],an['size'][1]*16/9);fill=[round(fw/an['size'][0],4),round(fw/(16/9)/an['size'][1],4)]
  px=c['pixels'] if c else None
  check(f'workspace {id} frame fills the {area} 16:9 wall',min(fill)>=.995 and px and abs(px[0]/px[1]/(16/9)-1)<=.03,{'anchorSize':an['size'],'frameFill':fill,'windowPixels':px,'still':str(shot)})
 # Tool mounts: a window can be placed only from a workspace with an area
 # home (core Layout::place), so each area's probe opens on its home (21-24)
 # and visits every tool mount of that area.
 placed=[];bad=[];tools=[x for x in m['anchors'] if x.get('mount',{}).get('role')=='tool-mount']
 for id,area in HOMES:
  title='Tool-'+str(id)
  s.ctl('eval','hl.window_rule({name="tool-'+str(id)+'",match={title="^'+title+'$"},workspace="'+str(id)+' silent"})')
  children.append(s.envrun('kitty','--title',title,'--override','cursor_blink_interval=0','sh','-c','echo tool probe; exec sleep 600',stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL))
  cap=wait(lambda:next((c for c in s.camera()['captures'] if c['title']==title and c['workspaceId']==id),None),timeout=30)
  for an in [x for x in tools if x['id'] in areas[area]['toolAnchors']]:
   try:
    client.call('surface.place',{'surfaceId':cap['id'],'anchorId':an['id']})
    wait(lambda:next((c for c in s.camera()['captures'] if c['id']==cap['id'] and math.dist(c['position'],an['pose']['position'])<.3),None),timeout=8);placed.append(an['id'])
   except Exception as e:bad.append({'anchor':an['id'],'error':repr(e)[:200],'capture':next((c for c in s.camera()['captures'] if c['id']==cap['id']),None)})
 check(f'tool mounts accept placement ({len(placed)}/{len(tools)})',not bad and len(placed)==len(tools)==20,{'placed':placed,'failed':bad})
 client.call('runtime.exit',{})
 report['status']='PASS' if all(c['passed'] for c in report['checks']) else 'FAIL';save()
# Run under core's workspace-homes suite setup (IPC 0.15, fresh layout
# state) with this acceptance and this package, like run.sh would.
import types
def prepare(installed):
 target=installed/WID;shutil.rmtree(target,ignore_errors=True);shutil.copytree(a.package,target)
sys.modules['workspace_homes']=types.SimpleNamespace(prepare=prepare,acceptance=acceptance,LUMEN=WID)
sys.argv=[str(a.core/'dev/nested/session.py'),'--workspace-homes']
os.environ['HYPRUNE_NESTED_PLUGIN']=str(a.core/'build/hyprune-core.so')
import runpy
with open('/tmp/worldshell-nested.lock','a') as lock:
 print('Waiting for private nested lock',flush=True);fcntl.flock(lock,fcntl.LOCK_EX)
 try:runpy.run_path(str(a.core/'dev/nested/session.py'),run_name='__main__')
 except SystemExit:pass
 except Exception as e:report.update(status='FAIL',error=repr(e));save();raise
