#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Release perf gate: scripted nested route capture against the previous release.

Runs tools/lumen-measure-session.py gate (private nested, native 4K Intel,
continuous rendering): eye-height poses every 3 m along every route edge in
both directions. Fixed render scale -> p50/p95 GPU frame ms; dynamic
resolution at 60 fps -> settled render scale per segment (p50, p05).

Baseline, in order of preference:
- --baseline-package: measured in the same session (rounds alternate), the
  only comparison immune to clock/thermal/driver drift between sessions;
- the newest record in reports/perf/ for an older version, valid only when it
  was taken with the same core commit, plugin, scale and quality (else the
  gate fails asking for --baseline-package).

Fails when p50 GPU ms grows > P50_LIMIT, p95 > P95_LIMIT, or the settled scale
drops by more than SCALE_DROP (p50) / SCALE_DROP_P05 (p05). A/A runs of the
same package agree within ~1 % per pose (opt-0.8.0/aa-noise), so the limits
leave room for noise while catching real regressions. --record writes the
candidate's record for the next release.
"""
import argparse,json,re,subprocess,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
P50_LIMIT,P95_LIMIT,SCALE_DROP,SCALE_DROP_P05=.08,.12,.05,.08
p=argparse.ArgumentParser(description=__doc__,formatter_class=argparse.RawDescriptionHelpFormatter)
p.add_argument('package',type=Path);p.add_argument('--baseline-package',type=Path)
p.add_argument('--records',type=Path,default=ROOT/'lumen-reach/reports/perf');p.add_argument('--output',type=Path,required=True)
p.add_argument('--core',type=Path,default=ROOT.parent/'core-optimise');p.add_argument('--record',action='store_true')
a=p.parse_args()
version=json.loads((a.package/'world.json').read_text())['version']
semver=lambda v:tuple(int(x) for x in re.findall(r'\d+',v)[:3])
cmd=[sys.executable,str(ROOT/'tools/lumen-measure-session.py'),'gate','--rounds','2','--core',str(a.core),'--output',str(a.output/'session')]
if a.baseline_package:cmd+=['--package',str(a.baseline_package)]
cmd+=['--package',str(a.package)]
subprocess.run(cmd,check=True)
s=json.loads((a.output/'session/report.json').read_text())
cand=s['runs']['B' if a.baseline_package else 'A']
record={'version':version,'coreCommit':s['coreCommit'],'pluginSHA256':s['pluginSHA256'],'scale':s['scale'],'quality':s['quality'],'routePoses':s['routePoses'],
 'manifestSHA256':s['packages']['B' if a.baseline_package else 'A']['manifestSHA256'],**cand}
if a.baseline_package:
 base={**s['runs']['A'],'version':s['packages']['A']['version'],'source':'same session'}
else:
 older=sorted((json.loads(f.read_text()) for f in a.records.glob('*.json')),key=lambda r:semver(r['version']))
 older=[r for r in older if semver(r['version'])<semver(version)]
 if not older:sys.exit('no older perf record: pass --baseline-package')
 base={**older[-1],'source':'record'}
 same=all(base.get(k)==record[k] for k in ['coreCommit','pluginSHA256','scale','quality'])
 if not same:
  out={'status':'FAIL','reason':'baseline record was taken with a different core/plugin/scale/quality; rerun with --baseline-package','baseline':base,'candidate':record}
  (a.output/'perf-gate.json').write_text(json.dumps(out,indent=1)+'\n');print(json.dumps(out,indent=1));sys.exit(1)
checks=[('gpuFrameMs.p50',cand['gpuFrameMs']['p50'],base['gpuFrameMs']['p50']*(1+P50_LIMIT),'<='),
 ('gpuFrameMs.p95',cand['gpuFrameMs']['p95'],base['gpuFrameMs']['p95']*(1+P95_LIMIT),'<='),
 ('settledScale.p50',cand['settledScale']['p50'],base['settledScale']['p50']-SCALE_DROP,'>='),
 ('settledScale.p05',cand['settledScale']['p05'],base['settledScale']['p05']-SCALE_DROP_P05,'>=')]
rows=[{'metric':m,'candidate':round(v,4),'limit':round(l,4),'pass':v<=l if op=='<=' else v>=l} for m,v,l,op in checks]
out={'status':'PASS' if all(r['pass'] for r in rows) else 'FAIL','limits':{'p50':P50_LIMIT,'p95':P95_LIMIT,'scaleDrop':SCALE_DROP,'scaleDropP05':SCALE_DROP_P05},'baseline':base,'candidate':record,'checks':rows}
(a.output/'perf-gate.json').write_text(json.dumps(out,indent=1)+'\n')
if a.record and out['status']=='PASS':a.records.mkdir(parents=True,exist_ok=True);(a.records/f'{version}.json').write_text(json.dumps(record,indent=1)+'\n')
print(json.dumps({k:out[k] for k in ['status','checks']},indent=1));sys.exit(0 if out['status']=='PASS' else 1)
