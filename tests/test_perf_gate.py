# SPDX-License-Identifier: MIT
"""check-perf-gate's decision on recorded captures: same-session baselines,
injected regressions, and records from a different core build."""
import copy,json,subprocess,sys,tempfile,unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];GATE=ROOT/'tools/check-perf-gate.py'
def run(name,gpu=9.0,p95=10.5,scale=.5,baseline=True,records=None,core='c0'):
 base={'gpuFrameMs':{'p50':9.0,'p95':10.5,'n':10},'settledScale':{'p50':.5,'p05':.5,'n':5}}
 cand={'gpuFrameMs':{'p50':gpu,'p95':p95,'n':10},'settledScale':{'p50':scale,'p05':scale,'n':5}}
 report={'coreCommit':core,'pluginSHA256':'p','scale':.5,'quality':'medium','routePoses':400,
  'packages':{'A':{'version':'0.9.0','manifestSHA256':'x'}} if not baseline else {'A':{'version':'0.8.0','manifestSHA256':'a'},'B':{'version':'0.9.0','manifestSHA256':'b'}},
  'runs':{'A':cand} if not baseline else {'A':base,'B':cand}}
 d=Path(tempfile.mkdtemp(prefix=name));(d/'pkg').mkdir();(d/'pkg/world.json').write_text(json.dumps({'version':'0.9.0'}))
 (d/'s.json').write_text(json.dumps(report))
 args=[sys.executable,str(GATE),str(d/'pkg'),'--output',str(d/'out'),'--session-report',str(d/'s.json'),'--records',str(records or d/'records')]
 if baseline:args+=['--baseline-package',str(d/'pkg')]
 (d/'out').mkdir();return subprocess.run(args,capture_output=True,text=True).returncode,d
class PerfGate(unittest.TestCase):
 def test_equal_passes(self):self.assertEqual(run('eq')[0],0)
 def test_p50_regression_fails(self):self.assertEqual(run('p50',gpu=9.9)[0],1)
 def test_p95_regression_fails(self):self.assertEqual(run('p95',p95=11.9)[0],1)
 def test_scale_drop_fails(self):self.assertEqual(run('scale',scale=.4375)[0],1)
 def test_record_from_same_core(self):
  rec=Path(tempfile.mkdtemp());(rec/'0.8.0.json').write_text(json.dumps({'version':'0.8.0','coreCommit':'c0','pluginSHA256':'p','scale':.5,'quality':'medium','gpuFrameMs':{'p50':9.0,'p95':10.5},'settledScale':{'p50':.5,'p05':.5}}))
  self.assertEqual(run('rec',baseline=False,records=rec)[0],0)
  self.assertEqual(run('rec2',baseline=False,records=rec,gpu=9.9)[0],1)
 def test_record_from_other_core_refuses(self):
  rec=Path(tempfile.mkdtemp());(rec/'0.8.0.json').write_text(json.dumps({'version':'0.8.0','coreCommit':'other','pluginSHA256':'p','scale':.5,'quality':'medium','gpuFrameMs':{'p50':9.0,'p95':10.5},'settledScale':{'p50':.5,'p05':.5}}))
  code,d=run('other',baseline=False,records=rec);self.assertEqual(code,1);self.assertIn('different core',(d/'out/perf-gate.json').read_text())
if __name__=='__main__':unittest.main()
