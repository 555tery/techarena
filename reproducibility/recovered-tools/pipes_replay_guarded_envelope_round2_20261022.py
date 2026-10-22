"""Pure geometric risk-budget hypothesis with an append-only boundary guard.

Before any deletion, preserve the original edge-placement condition: there is
no fragmentation history to justify interior reservations. After the first
observed deletion, use the 25% rounded-peak envelope of the pinned parent.
The event is causal and independent of case ID and prefix length.
"""
import hashlib,importlib.util
from pathlib import Path
PARENT=Path('/tmp/pipes_replay_volume_envelope_round2_20261022.py')
PARENT_SHA='4f3c509e56d6ab556f5ad431dabd72b7037e1a00f4052327bebfff9157c8898b'

def _parent():
 assert hashlib.sha256(PARENT.read_bytes()).hexdigest()==PARENT_SHA
 spec=importlib.util.spec_from_file_location('pipes_replay_guarded_envelope_parent',PARENT)
 module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
 return module

def _replace(source,old,new):
 assert source.count(old)==1,(old,source.count(old))
 return source.replace(old,new)

def apply_cpp(source,compact=True):
 source=_parent().apply_cpp(source,compact=compact)
 source=_replace(source,'bool emit=true; int T=0;long long volume=0,peakVolume=0;',
 'bool emit=true; bool sawDeletion=false; int T=0;long long volume=0,peakVolume=0;')
 source=_replace(source,'void remove(int id){if(id<=0',
 'void remove(int id){sawDeletion=true;if(id<=0')
 source=_replace(source,'''bool boundedReplay(const Allocator& a,int x,int n){
 const int newT=a.T+20*max(0,(x+n-a.T+19)/20);''',
 '''bool boundedReplay(const Allocator& a,int x,int n){
 const int newT=a.T+20*max(0,(x+n-a.T+19)/20);
 if(!a.sawDeletion&&!guardedReplay(a,x,n,newT))return false;''')
 return source

def apply_cj(source,compact=True):
 source=_parent().apply_cj(source,compact=compact)
 source=_replace(source,'class PhysicalAllocator {\n    public var trench: Int64 = 0',
 'class PhysicalAllocator {\n    public var trench: Int64 = 0\n    public var sawDeletion = false')
 source=_replace(source,'''let p = pipes[id]
        volume -= p.b''',
 '''let p = pipes[id]
        sawDeletion = true
        volume -= p.b''')
 source=_replace(source,'''func causalReplayAllowed(actual: PhysicalAllocator, x: Int64, n: Int64): Bool {
    let newTrench = actual.trench + 20 * iMax(0, (x + n - actual.trench + 19) / 20)''',
 '''func causalReplayAllowed(actual: PhysicalAllocator, x: Int64, n: Int64): Bool {
    let newTrench = actual.trench + 20 * iMax(0, (x + n - actual.trench + 19) / 20)
    if (!actual.sawDeletion && !guardedReplay(actual, x, n, newTrench)) { return false }''')
 return source
