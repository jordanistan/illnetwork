#!/usr/bin/env python3
"""Atomic remote task claims for two-machine work; no credential handling."""
import argparse, re, subprocess, json
from pathlib import Path
from datetime import datetime, timezone
p=argparse.ArgumentParser(); p.add_argument('task'); p.add_argument('--device',choices=['laptop','desktop','chatgpt'],required=True); p.add_argument('--release',action='store_true'); a=p.parse_args()
if not re.fullmatch(r'P\d{3}',a.task): raise SystemExit('Task must be P followed by three digits')
ref='refs/heads/claims/'+a.task
base=Path(subprocess.check_output(['git','rev-parse','--show-toplevel'],text=True).strip())
state=base/'.portfolio-claims'/f'{a.task}-{a.device}.json'
if a.release:
    if not state.is_file(): raise SystemExit('No local claim record; do not guess another owner’s lease SHA')
    data=json.loads(state.read_text()); expected=data['sha']
    if data['ref']!=ref or data['device']!=a.device: raise SystemExit('Claim record mismatch')
    subprocess.run(['git','push',f'--force-with-lease={ref}:{expected}','origin',':'+ref],check=True)
    state.unlink(); print('Released '+a.task)
else:
    if state.exists(): raise SystemExit('A local claim already exists; inspect it before resuming')
    sha=subprocess.check_output(['git','rev-parse','HEAD'],text=True).strip()
    # Empty expected SHA requires a nonexistent remote ref; the server rejects races.
    result=subprocess.run(['git','push',f'--force-with-lease={ref}:','origin',sha+':'+ref])
    if result.returncode: raise SystemExit('Claim not acquired. Choose another task or resolve authentication; never overwrite the claim.')
    state.parent.mkdir(exist_ok=True)
    state.write_text(json.dumps({'task':a.task,'device':a.device,'ref':ref,'sha':sha,'claimed_at':datetime.now(timezone.utc).isoformat()},indent=2)+'\n')
    print('Claimed '+a.task+' for '+a.device+'. Record owner/branch/files in the issue before editing.')
