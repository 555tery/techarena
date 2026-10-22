#!/usr/bin/env python3
from pathlib import Path
import sys,json,hashlib
ROOT=Path(__file__).resolve().parent
CONT=ROOT.parents[1]
REPO=Path(__file__).resolve().parents[5]
sys.path.insert(0,str(CONT)); import runtime
runtime.ROOT=ROOT; runtime.e.ROOT=ROOT
runtime.e.quota=lambda:runtime.e.gate(ROOT,min_remaining_percent=0,max_age_seconds=30)
out=ROOT/'four-free-repair.txt'
log=ROOT/'four-free-repair.log'
cmd=[str(CONT/'joint-csp/repair_min2'),str(REPO/'data/pipes/open/11.in'),str(ROOT/'partial-four.txt'),str(out),'20800','30','20261019',str(ROOT/'initial-invalid.txt')]
rc=runtime.e.invoke(cmd,ROOT,log.name,45)
result={'command':cmd,'returncode':rc,'log':log.read_text(errors='replace') if log.exists() else '',
        'output_exists':out.exists(),'invalid_best_exists':Path(str(out)+'.invalid-best').exists(),
        'binary_sha256':hashlib.sha256((CONT/'joint-csp/repair_min2').read_bytes()).hexdigest(),
        'source_sha256':hashlib.sha256((CONT/'joint-csp/repair_min2.cpp').read_bytes()).hexdigest()}
(ROOT/'four-free-result.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result,indent=2))
