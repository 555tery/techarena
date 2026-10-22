"""Guarded offline search only; never contacts the contest platform."""
import sys,json
from pathlib import Path
ROOT=Path(__file__).resolve().parent
sys.path.insert(0,str(ROOT.parents[1]/'prototypes/pipes_options_v4_20261019'))
import evaluate as e
e.ROOT=ROOT
e.quota()
assert e.invoke(['/usr/bin/clang++','-std=c++17','-O3',str(ROOT/'pack.cpp'),'-o',str(ROOT/'pack')],ROOT,'compile-pack.log',120)==0
rc=e.invoke([str(ROOT/'pack'),str(ROOT/'problem.txt'),str(ROOT/'best-positions.txt'),'128'],ROOT,'search.log',900)
e.save(ROOT/'search-completion.json',{'returncode':rc,'has_best':(ROOT/'best-positions.txt').exists(),'iterations_cap':128})
print(json.dumps({'returncode':rc,'has_best':(ROOT/'best-positions.txt').exists()}))
