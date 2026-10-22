#!/usr/bin/env python3
"""Freeze existing algorithms and the deduplicated corpus; no optimization."""
import hashlib
import importlib.util
import json
import platform
import shutil
import struct
import subprocess
import sys
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
sys.dont_write_bytecode = True
sys.path.insert(0, str(ROOT/'shinka-pipes/evaluator-native'))
from build_native import build, BASE

def sha(p): return hashlib.sha256(Path(p).read_bytes()).hexdigest()

SOURCES = [
 ('online_cpp', 'Current online / strict_improvement', 'prototypes/pipes_online_patterns_20261020/release/solution.cpp', 'f7b285eee9d59f443b015de581c4622668dd1a321e0cb9ef00d4baf10412f5db'),
 ('online_cj', 'Current online / Cangjie', 'prototypes/pipes_cangjie_port_20261020/release/solution.cj', 'cc2fcdf7d930bad6c75a0656c105c28399c66d5184c937740c69764a1e9e681f'),
 ('primal_recent', 'Previous online / primal_recent', 'prototypes/pipes_online_core_20261020/release/solution.cpp', '57c047da7ae9939d9d86dfb050458f22e1a189ec43c5fb621c578bee324821d9'),
 ('trial22', 'Historical online / trial22', 'research-campaigns/20261018T141843+0700-autonomous/releases/988927c690b4034f3a26c839ee00bc2c0d0956e6ea9f5b6369c9d45e961242e4/solution.cpp', '988927c690b4034f3a26c839ee00bc2c0d0956e6ea9f5b6369c9d45e961242e4'),
 ('hybrid', 'Cautious hybrid / accepted release', 'prototypes/pipes_closed_ready_20261020/release/solution.cpp', '48a44fb0ccad7e6560055245a3096f892c23b5a98c4ab77468c87968e23054c1'),
 ('replay_search', 'Full replay + causal search / cache32', 'prototypes/pipes_g5420_cpu_20261020/cache32/solution.cpp', 'a843822451c2a7c5e07330daa33268fc77bccfbc08fd196bfaf98a673ae24cfe'),
]

def main():
    assert not (HERE/'freeze.json').exists(), 'Already frozen; do not overwrite.'
    spec = importlib.util.spec_from_file_location('official_base', ROOT/'tools/pipes_harness.py')
    base = importlib.util.module_from_spec(spec); spec.loader.exec_module(base)
    methods = []
    compiler = shutil.which('clang++')
    for name, label, source, expected in SOURCES:
        original = ROOT/source
        assert sha(original) == expected, source
        folder = HERE/'methods'/name; folder.mkdir(parents=True, exist_ok=True)
        local = folder/original.name; shutil.copy2(original, local)
        binary = folder/'solver'
        if name == 'online_cj':
            previous = ROOT/'prototypes/pipes_cangjie_port_20261020/bin/solution-cj'
            metadata = json.loads(previous.with_suffix('.build.json').read_text())
            assert metadata['source_sha256']['solution.cj'] == expected
            assert sha(previous) == metadata['binary_sha256']
            shutil.copy2(previous, binary)
            command = metadata['command']
            (folder/'build.json').write_text(json.dumps(metadata,indent=2)+'\n')
        else:
            command = [compiler,'-std=c++20','-O2','-DNDEBUG',str(local),'-o',str(binary)]
            result = subprocess.run(command, capture_output=True, text=True, timeout=180)
            (folder/'build.log').write_text(result.stdout+result.stderr)
            assert result.returncode == 0, result.stderr[-4000:]
        methods.append(dict(id=name,label=label,original_source=source,
                            source=str(local.relative_to(HERE)),source_sha256=expected,
                            binary=str(binary.relative_to(HERE)),binary_sha256=sha(binary),build_command=command))
        print('BUILT',name,flush=True)
    inventory_path = ROOT/'prototypes/pipes_test_inventory_20261020/selected_085.json'
    selected = json.loads(inventory_path.read_text())
    assert len(selected) == 2537
    all_tests = json.loads((inventory_path.parent/'unique_tests.json').read_text())
    selected_hashes = {x['canonical_sha256'] for x in selected}
    extras = [x for x in all_tests if x['canonical_sha256'] not in selected_hashes
              and any(f'data/pipes/open/{i}.in' in x['origins'] for i in range(1,16))]
    assert len(extras) == 4
    inputs = HERE/'inputs'; inputs.mkdir(exist_ok=True)
    cases = []
    for row in selected+extras:
        regular = [x for x in row['origins'] if '!' not in x and (ROOT/x).is_file()]
        assert regular
        source = regular[0]; path = ROOT/source
        raw_sha = sha(path); assert raw_sha in row['raw_sha256s']
        meta = base.parse_test(path)
        assert meta['operation_count'] == row['operations']
        assert meta['final_occupied_length_m'] == row['final_volume']
        assert meta['peak_live_pipe_length_m'] == row['peak_volume']
        tokens = path.read_bytes().split(); n = int(tokens[1]); cmds = list(map(int,tokens[2:2+n]))
        canonical = hashlib.sha256(struct.pack('<I',n)+struct.pack('<'+'i'*n,*cmds)).hexdigest()
        assert canonical == row['canonical_sha256']
        target = inputs/(canonical+'.in'); shutil.copy2(path,target)
        public = [i for i in range(1,16) if f'data/pipes/open/{i}.in' in row['origins']]
        parts = Path(source).parts
        group = '/'.join(parts[:2])
        if source.startswith('data/pipes/open/'): group = 'Open15'
        if source.startswith('results/pipes/improvement/') and len(parts)>3: group='/'.join(parts[:4])
        cases.append(dict(id=canonical,selected=canonical in selected_hashes,public_number=public[0] if public else None,
                          origin=source,origins=row['origins'],source_group=group,
                          input=str(target.relative_to(HERE)),input_sha256=raw_sha,meta=meta))
    # Uniform hash ordering; no ordering or selection based on solver outcomes.
    cases.sort(key=lambda c:c['id'])
    assert len({x['id'] for x in cases}) == 2541
    native = build(HERE/'native-build')
    assert sha(BASE/'task/vendor/interactor.cpp') == sha(ROOT/'vendor/pipes_official/interactor.cpp')
    freeze = dict(created_unix=time.time(),purpose='Exhaustive descriptive comparison of saved methods; no fitting or promotion.',
                  selected_count=2537,extra_open15_cases=4,total_commands_selected=sum(x['operations'] for x in selected),
                  selection='legal unique command streams, F/(20*ceil(peak_active_volume/20)) >= 0.85; volume upper bound, not certified reachable optimum',
                  aggregation='Uniform weight per unique selected stream. Source-group summaries are descriptive, not independent generating families. Official full Open15 shown separately.',
                  no_independent_holdout_claim=True,platform_actions=0,methods=methods,cases=cases,
                  inventory_sha256=sha(inventory_path),host=platform.platform(),machine=platform.machine(),
                  compiler_version=subprocess.check_output([compiler,'--version'],text=True),
                  cpu_limit_s=5,memory_limit_mib=256,response_timeout_s=5,wall_timeout_s=240,
                  runtime_environment={'cjProcessorNum':'1'},hard_cpu_affinity=False,native_windows_tested=False,
                  native_binary=str(native.relative_to(HERE)),native_binary_sha256=sha(native),
                  official_source_sha256=sha(ROOT/'vendor/pipes_official/interactor.cpp'),
                  support_sha256={str(p.relative_to(ROOT)):sha(p) for p in [ROOT/'tools/pipes_harness.py',ROOT/'shinka-pipes/evaluator-native/native_harness.py',ROOT/'shinka-pipes/evaluator-native/native_runner.cpp']})
    (HERE/'freeze.json').write_text(json.dumps(freeze,indent=2)+'\n')
    print('FROZEN',len(cases),'inputs',len(methods),'methods',flush=True)

if __name__=='__main__': main()
