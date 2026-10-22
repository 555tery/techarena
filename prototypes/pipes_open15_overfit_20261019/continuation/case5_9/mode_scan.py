#!/usr/bin/env python3
"""Bounded case9 scan of conditioned allocator modes for fixed shared pins."""
from pathlib import Path
import hashlib, json, subprocess, time
REPO=Path(__file__).resolve().parents[4]
ROOT=Path(__file__).resolve().parent
CONT=ROOT.parent
DATA=REPO/'data/pipes/open/9.in'
PINS=ROOT/'pins.txt'
MODES=[('knapsack',CONT/'conditioned_knapsack',m) for m in range(2000,2008)] + [('reverse',CONT/'conditioned_reverse',m) for m in range(8)]
def sha(path): return hashlib.sha256(Path(path).read_bytes()).hexdigest()
results=[]; started=time.monotonic()
for family, binary, mode in MODES:
    try:
        r=subprocess.run([str(binary),str(DATA),str(PINS),'125','/dev/null',str(mode)],cwd=REPO,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,text=True,timeout=15)
        try: score=int(r.stdout.strip().splitlines()[-1])
        except Exception: score=None
        results.append({'family':family,'mode':mode,'returncode':r.returncode,'T':score,'output':r.stdout.strip()[-300:]})
    except subprocess.TimeoutExpired as e:
        results.append({'family':family,'mode':mode,'timeout':True,'output':str(e)[:200]})
out={'scope':'case9 only, fixed pins.txt, no native harness','prefix':125,'modes':results,'elapsed_seconds':round(time.monotonic()-started,3),'sha256':{'input9':sha(DATA),'pins':sha(PINS),'baseline_case5':sha(ROOT/'case5_positions.txt'),'baseline_case9':sha(ROOT/'case9_positions.txt'),'conditioned_knapsack_cpp':sha(CONT/'conditioned_knapsack.cpp'),'conditioned_knapsack_binary':sha(CONT/'conditioned_knapsack'),'conditioned_reverse_cpp':sha(CONT/'conditioned_reverse.cpp'),'conditioned_reverse_binary':sha(CONT/'conditioned_reverse')}}
(ROOT/'mode-scan.json').write_text(json.dumps(out,indent=2)+'\n')
print(json.dumps(out,indent=2))
