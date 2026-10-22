"""Pure composition; enabled only after the root's fixed screening gate."""
import hashlib,importlib.util
from pathlib import Path
PINS=[('/tmp/pipes_core_round2_20261022.py', 'c39af23b77e1a22ae2230ff7077f54c4c1038ca52f6de1dafe016d070d8ca847'), ('/tmp/pipes_replay_guarded_envelope_round2_20261022.py', '0ec7f2f6694191db3a3ff10d7e553b83500a7e33f5355a869af189f0842736f0')]
def _load(path,expected):
 p=Path(path);assert hashlib.sha256(p.read_bytes()).hexdigest()==expected
 spec=importlib.util.spec_from_file_location('round2_composed_'+expected[:12],p)
 m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m);return m

def apply_cpp(source):
 core,guard=(_load(*p)for p in PINS)
 return guard.apply_cpp(core.apply_cpp(source),compact=False)

def apply_cj(source):
 core,guard=(_load(*p)for p in PINS)
 return guard.apply_cj(core.apply_cj(source),compact=False)
