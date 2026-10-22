"""Pure additional hypothesis: replay's avoidable geometric overhead <= 25%.

P=20*ceil(peakLiveVolume/20). The optional replay envelope is floor20(5P/4),
so it cannot spend even one extra section while P<80. Locally unavoidable
expansion remains allowed. This is a declared geometric risk budget, not a
prediction of hidden input likelihood. No solver execution or file mutation.

The parent transformer is pinned by SHA and must remain unchanged.
"""
import hashlib,importlib.util
from pathlib import Path
PARENT=Path('/tmp/pipes_replay_round2_20261022.py')
PARENT_SHA='44b22b8cc4a6567fd4ec6aee88fd7baa1532561ad24fa702a03a3b451696bff2'

def _parent():
 assert hashlib.sha256(PARENT.read_bytes()).hexdigest()==PARENT_SHA
 spec=importlib.util.spec_from_file_location('pipes_replay_volume_envelope_parent',PARENT)
 module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
 return module

def _replace(source,old,new):
 assert source.count(old)==1,(old,source.count(old))
 return source.replace(old,new)

def apply_cpp(source,compact=True):
 p=_parent();source=p.apply_cpp(source,'compact-capped'if compact else'section')
 return _replace(source,'const long long oneSection=20*((peak+19)/20)+20;',
 '''const long long unavoidable=20*((peak+19)/20);
 const long long oneSection=20*((5*unavoidable)/80);''')

def apply_cj(source,compact=True):
 p=_parent();source=p.apply_cj(source,'compact-capped'if compact else'section')
 return _replace(source,'let oneSection = 20 * ((peak + 19) / 20) + 20',
 '''let unavoidable = 20 * ((peak + 19) / 20)
    let oneSection = 20 * ((5 * unavoidable) / 80)''')
