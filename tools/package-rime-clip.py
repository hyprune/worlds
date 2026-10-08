#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Alternate the same three real engine views before/after; encode only in /tmp."""
import argparse,json,shutil,subprocess,tempfile
from pathlib import Path
p=argparse.ArgumentParser();p.add_argument('before',type=Path);p.add_argument('after',type=Path);p.add_argument('output',type=Path);a=p.parse_args()
reports=[json.loads((d/'nested-report.json').read_text()) for d in [a.before,a.after]]
assert all(r['status']=='PASS' and r['graphicsRequest']['quality']=='medium' for r in reports)
assert [r['vaultClip']['version'] for r in reports]==['0.5.0','0.6.0']
assert reports[0]['vaultClip']['views']==reports[1]['vaultClip']['views']
staging=Path(tempfile.mkdtemp(prefix='rime-v3-final-',dir='/tmp'));output=staging/'rime-vault-v3.mp4'
font=subprocess.check_output(['fc-match','-f','%{file}','DejaVu Sans'],text=True).strip()
filters=['[0:v]split=3[b0][b1][b2]','[1:v]split=3[a0][a1][a2]'];order=[]
for i,title in enumerate(['ARRIVAL','FROZEN SERVICES','MAINTENANCE DECK']):
 for prefix,version,label in [('b','0.5.0','BEFORE'),('a','0.6.0','AFTER')]:
  tag=f'{prefix}{i}out';order.append(f'[{tag}]')
  filters.append(f'[{prefix}{i}]trim=start={i*7}:duration=7,setpts=PTS-STARTPTS,drawtext=fontfile={font}:text=RIME VAULT  {version}  {label}  /  {title}:x=32:y=26:fontsize=28:fontcolor=white:box=1:boxcolor=black@0.72:boxborderw=12[{tag}]')
filters.append(''.join(order)+'concat=n=6:v=1:a=0[out]')
subprocess.run(['ffmpeg','-y','-v','error','-i',str(a.before/'vault.mp4'),'-i',str(a.after/'vault.mp4'),'-filter_complex',';'.join(filters),'-map','[out]','-an','-r','30','-c:v','libx264','-preset','medium','-crf','20','-maxrate','8000k','-bufsize','16000k','-pix_fmt','yuv420p','-color_range','tv','-movflags','+faststart',str(output)],check=True)
probe=json.loads(subprocess.check_output(['ffprobe','-v','error','-show_streams','-show_format','-of','json',str(output)]));assert 40<=float(probe['format']['duration'])<=43
metadata={'title':'Rime Vault — frost and service-room density, 0.5.0 to 0.6.0','tag':'world','worldVersion':'0.6.0','durationSeconds':probe['format']['duration'],'preset':'Medium / Intel iGPU','notes':'Real isolated nested-engine capture under /tmp/worldshell-nested.lock. Three identical camera paths alternate BEFORE 0.5.0 and AFTER 0.6.0 at seven-second intervals. Only labels and cuts were added; no grading or retouching. Includes pipe-top rime, directional frozen metal, console rows, grated cable channels and red-amber practicals with cold fill. Encoded in /tmp before delivery. Static screen artwork is authored placeholder UI.','beforeSceneSHA256':reports[0]['sceneSHA256'],'afterSceneSHA256':reports[1]['sceneSHA256']}
assert all(isinstance(v,str) for v in metadata.values())
output.with_suffix('.json').write_text(json.dumps(metadata,indent=2)+'\n')
a.output.mkdir(parents=True,exist_ok=True)
for src in [output,output.with_suffix('.json')]:shutil.move(str(src),a.output/src.name)
(a.output/'video-probe.json').write_text(json.dumps(probe,indent=2)+'\n')
print(a.output/output.name)
