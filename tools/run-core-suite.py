#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Run a core nested suite (dev/nested/session.py --<suite>) against a chosen
Lumen Reach package, without editing core. Core's workspace-homes harness
installs ../worlds/dist/com.hyprune.lumen-reach (the source package); this
swaps in --lumen (e.g. the format 0.7 release package in dist-07/).
Run it as core's run.sh does, under the nested lock:
  flock /tmp/worldshell-nested.lock python3 tools/run-core-suite.py --core ../core-optimise --lumen dist-07/com.hyprune.lumen-reach workspace-homes
"""
import argparse,runpy,shutil,sys
from pathlib import Path
p=argparse.ArgumentParser(description=__doc__,formatter_class=argparse.RawDescriptionHelpFormatter)
p.add_argument('--core',type=Path,required=True);p.add_argument('--lumen',type=Path,required=True);p.add_argument('suite')
a=p.parse_args();nested=(a.core/'dev/nested').resolve();lumen=a.lumen.resolve()
sys.path.insert(0,str(nested))
# Patch the harness when session.run() imports it, exactly as in run.sh's
# flow: importing it (and its `session` copy) any earlier changes state.
import importlib.abc,importlib.machinery
class Patch(importlib.abc.MetaPathFinder):
 def find_spec(self,name,path,target=None):
  if name!='workspace_homes':return None
  sys.meta_path.remove(self);spec=importlib.machinery.PathFinder.find_spec(name,[str(nested)]);loader=spec.loader
  class L(importlib.abc.Loader):
   def create_module(self,spec):return None
   def exec_module(self,module):
    loader.exec_module(module);original=module.prepare
    def prepare(installed):
     original(installed);target=installed/module.LUMEN;shutil.rmtree(target);shutil.copytree(lumen,target)
     print('Lumen package for this run:',lumen,flush=True)
    module.prepare=prepare
  spec.loader=L();return spec
sys.meta_path.insert(0,Patch())
sys.argv=[str(nested/'session.py'),'--'+a.suite]
runpy.run_path(str(nested/'session.py'),run_name='__main__')
