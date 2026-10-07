#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Exercise this package using core's verified, disposable nested harness.
Uses the same global flock as core. No outer-session hyprctl invocation.
Core must already be built; its sources/binaries are not modified.
"""
import argparse,fcntl,json,shutil,subprocess,sys,time
from pathlib import Path
from types import SimpleNamespace
p=argparse.ArgumentParser();p.add_argument('--core',type=Path,default=Path(__file__).resolve().parents[2]/'core');p.add_argument('--package',type=Path,default=Path(__file__).resolve().parents[1]/'dist/com.hyprune.switchyard');p.add_argument('--output',type=Path,default=Path(__file__).resolve().parents[1]/'artifacts/switchyard');args=p.parse_args();args.output.mkdir(parents=True,exist_ok=True)
sys.path.insert(0,str(args.core/'dev/nested'));import session
report={'coreCommit':subprocess.check_output(['git','-C',str(args.core),'rev-parse','HEAD'],text=True).strip()}
def smoke(client,children,ignored):
 manifest=json.loads((args.package/'world.json').read_text());ident=manifest['id'];assert ident=='com.hyprune.switchyard'
 installed=session.STATE/'worlds'/ident
 if installed.exists():shutil.rmtree(installed)
 shutil.copytree(args.package,installed)
 report['load']=client.call('world.load',{'worldId':ident});print('LOAD',report['load'],flush=True)
 sub=client.call('state.subscribe',{'topics':['state']})['subscriptionId']
 # Toggle only the verified nested headless output; ctl refuses outer identities.
 session.ctl('eval','hl.plugin.hyprune.toggle("HEADLESS-1")');time.sleep(2)
 state=client.call('state.snapshot',{'subscriptionId':sub})['snapshot']['state'];report['snapshot']=state
 c=session.camera();report['camera']=c;assert c['active'] and c['frames']>0,c
 subprocess.run([str(session.HERE/'ctl.py'),'shot',str(args.output/'nested-arrival.png')],check=True)
 before=state['movement']['position'];subprocess.run([str(session.HERE/'ctl.py'),'env','wtype','-P','w','-s','650','-p','w'],check=True);time.sleep(.2)
 after=client.call('state.snapshot',{'subscriptionId':sub})['snapshot']['state']['movement']['position'];assert abs(after[2]-before[2])>.3,(before,after);report['walk']={'before':before,'after':after}
 # Camera inspection is confined to the nested test; package stays immutable.
 session.ctl('eval','hl.plugin.hyprune.camera(-14.67, 2.6, -2, 0, 0)');time.sleep(.7)
 subprocess.run([str(session.HERE/'ctl.py'),'shot',str(args.output/'nested-route.png')],check=True)
 client.call('runtime.exit',{});time.sleep(.2);assert not session.camera()['active']
 report['status']='PASS';report['checks']=['world.load','snapshot','active nested rendering','walk at spawn','runtime.exit'];(args.output/'nested-report.json').write_text(json.dumps(report,indent=2)+'\n');print('PASS Switchyard nested load/render/walk/exit',flush=True)
session.smoke=smoke
# Package smoke does not run core's separate client-crash fault-injection suite.
if hasattr(session,'failures'):session.failures=lambda *unused:None
with open('/tmp/worldshell-nested.lock','a') as lock:
 fcntl.flock(lock,fcntl.LOCK_EX)
 try:session.run(SimpleNamespace(serve=False,record=False))
 except Exception as e:
  report['status']='FAIL';report['error']=str(e);(args.output/'nested-report.json').write_text(json.dumps(report,indent=2)+'\n');raise
