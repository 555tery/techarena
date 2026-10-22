"""One fixed round3 ablation: ordinary Best-Fit only above the MC cutoff.

The parent ordinary-BF transformer is pinned by SHA256. Its entire policy and
all structured exclusions stay unchanged, except ordinaryRequest additionally
requires activePipeCount>kMcMaxActivePipes. This reuses the existing4096 boundary
where MC is disabled; it does not choose or tune a new threshold. No builds,
solver runs, experiment registration, or changes to parent/pilot artifacts.
"""
import hashlib,importlib.util
from pathlib import Path
PARENT=Path('/tmp/pipes_ordinary_bestfit_round3_20261022.py')
PARENT_SHA='da8ce0de942ea62e1dcc0ece8219f7585cdbfb6168d0bc2213234c0a4ba30d0a'

def _parent():
 assert hashlib.sha256(PARENT.read_bytes()).hexdigest()==PARENT_SHA,'ordinary-BF parent changed'
 spec=importlib.util.spec_from_file_location('pipes_ordinary_bestfit_large_parent',PARENT)
 module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
 return module

def _replace(source,old,new):
 assert source.count(old)==1,(old,source.count(old))
 return source.replace(old,new)

def apply_cpp(source):
 transformed=_parent().apply_cpp(source)
 return _replace(transformed,
 'const bool ordinaryRequest = !parityCohortMode && !alternatingDeleteMode &&',
 'const bool ordinaryRequest = activePipeCount > kMcMaxActivePipes &&\n            !parityCohortMode && !alternatingDeleteMode &&')

def apply_cj(source):
 transformed=_parent().apply_cj(source)
 return _replace(transformed,
 'let ordinaryRequest = !parityCohortMode && !alternatingDeleteMode &&',
 'let ordinaryRequest = activePipeCount > kMcMaxActivePipes &&\n            !parityCohortMode && !alternatingDeleteMode &&')
