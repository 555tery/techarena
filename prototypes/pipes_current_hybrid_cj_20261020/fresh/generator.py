#!/usr/bin/env python3
"""Input-only frozen corpus. Never imports or executes a placement policy."""
import argparse
import hashlib
import importlib.util
import json
import math
import random
import struct
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
OUT = Path(__file__).resolve().parent
MASTER_SEED = 202610205817693
FAMILIES = ['phase_lifetime_switch', 'periodic_interval_deletions',
            'bursts_and_drains', 'size_lifetime_correlation_flip',
            'comb_holes_replacement', 'rotating_cohorts',
            'bimodal_antiphase', 'young_old_mixture']

def sha(data):
    return hashlib.sha256(data).hexdigest()

def canonical(commands):
    h = hashlib.sha256(struct.pack('<I', len(commands)))
    for x in commands:
        h.update(struct.pack('<i', x))
    return h.hexdigest()

class Stream:
    def __init__(self, prefix=()):
        self.commands = []
        self.lengths = [0]
        self.birth = [0]
        self.live = []
        self.pos = {}
        self.volume = self.peak = self.peak_active = 0
        for x in prefix:
            self.add(x) if x > 0 else self.remove(-x)

    def add(self, length):
        pid = len(self.lengths)
        self.lengths.append(length)
        self.birth.append(len(self.commands))
        self.pos[pid] = len(self.live)
        self.live.append(pid)
        self.commands.append(length)
        self.volume += length
        self.peak = max(self.peak, self.volume)
        self.peak_active = max(self.peak_active, len(self.live))

    def remove(self, pid):
        idx = self.pos.pop(pid)
        last = self.live.pop()
        if idx < len(self.live):
            self.live[idx] = last
            self.pos[last] = idx
        self.commands.append(-pid)
        self.volume -= self.lengths[pid]

    def choose(self, rng, mode):
        sample = rng.sample(self.live, min(17, len(self.live)))
        if mode == 'young':
            return max(sample, key=lambda p: self.birth[p])
        if mode == 'old':
            return min(sample, key=lambda p: self.birth[p])
        if mode == 'small':
            return min(sample, key=lambda p: (self.lengths[p], self.birth[p]))
        if mode == 'large':
            return max(sample, key=lambda p: (self.lengths[p], self.birth[p]))
        return rng.choice(sample)

def next_size(rng, regime):
    if regime == 0:
        return rng.randint(1, 9)
    if regime == 1:
        return rng.randint(26, 40)
    if regime == 2:
        return rng.choice([3, 7, 11, 13, 17, 19, 21, 27, 31, 37, 39])
    if regime == 3:
        return rng.choice([rng.randint(1, 4), rng.randint(35, 40)])
    return rng.randint(1, 40)

def evolve(s, rng, count, family, params):
    """Several mechanisms change their size/deletion rules within one stream."""
    phase = params['phase_length']
    batch = []
    for t in range(count):
        epoch, offset = divmod(t, phase)
        regime = (epoch + params['size_offset']) % 5
        mode = ['young', 'old', 'small', 'large', 'random'][epoch % 5]
        probability = 0.46
        if family == 'phase_lifetime_switch':
            probability = [0.18, 0.72, 0.35, 0.62][epoch % 4]
            mode = ['old', 'young'][epoch % 2]
        elif family == 'periodic_interval_deletions':
            probability = 0.88 if offset < phase // 3 else 0.24
            if offset == 0:
                ids = sorted(s.live)
                stride = params['stride']
                batch = ids[epoch % stride::stride]
                rng.shuffle(batch)
        elif family == 'bursts_and_drains':
            probability = 0.87 if epoch % 3 == 1 else 0.11
            mode = ['large', 'old', 'young'][epoch % 3]
        elif family == 'size_lifetime_correlation_flip':
            probability = 0.55 if epoch % 2 else 0.37
            mode = 'small' if epoch % 2 else 'large'
        elif family == 'comb_holes_replacement':
            probability = 0.72 if offset < phase * 0.45 else 0.20
            if offset == 0:
                ids = sorted(s.live)
                batch = ids[(epoch % 3)::3]
        elif family == 'rotating_cohorts':
            probability = 0.60 if epoch % 2 else 0.27
            if offset == 0:
                ids = sorted(s.live, key=lambda p: s.birth[p])
                lo = (epoch % 4) * len(ids) // 4
                batch = ids[lo:lo + max(1, len(ids) // 4)]
                rng.shuffle(batch)
        elif family == 'bimodal_antiphase':
            probability = 0.59 if epoch % 2 else 0.29
            regime = 0 if epoch % 2 else 1
            mode = 'large' if epoch % 2 else 'small'
        elif family == 'young_old_mixture':
            probability = 0.44 + 0.15 * (epoch % 2)
            mode = 'young' if rng.random() < params['young_probability'] else 'old'
        if s.live and rng.random() < probability:
            while batch and batch[-1] not in s.pos:
                batch.pop()
            pid = batch.pop() if batch else s.choose(rng, mode)
            s.remove(pid)
        else:
            s.add(next_size(rng, regime))

def inventory_hashes():
    directory = ROOT / 'prototypes/pipes_test_inventory_20261020'
    hashes, sources = set(), []
    def visit(obj):
        if isinstance(obj, dict):
            for k, v in obj.items():
                if k == 'canonical_sha256' and isinstance(v, str):
                    hashes.add(v)
                else:
                    visit(v)
        elif isinstance(obj, list):
            for v in obj:
                visit(v)
    for name in ['unique_tests.json', 'raw_stream_supplement.json']:
        p = directory / name
        data = p.read_bytes()
        visit(json.loads(data))
        sources.append({'path': str(p.relative_to(ROOT)), 'sha256': sha(data)})
    return hashes, sources

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--out', type=Path, default=OUT)
    args = parser.parse_args()
    out = args.out.resolve()
    if (out / 'manifest.json').exists():
        raise SystemExit('Refusing to overwrite frozen corpus; choose a new --out.')
    out.mkdir(parents=True, exist_ok=True)
    (out / 'inputs').mkdir(exist_ok=True)
    spec = importlib.util.spec_from_file_location('official_local_parser', ROOT / 'tools/pipes_harness.py')
    harness = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(harness)
    known, inventory_sources = inventory_hashes()
    initial_known = len(known)
    public, public_sources = {}, []
    for k in range(1, 16):
        path = ROOT / f'data/pipes/open/{k}.in'
        raw = path.read_bytes()
        tokens = raw.split()
        public[k] = [int(x) for x in tokens[2:2 + int(tokens[1])]]
        public_sources.append({'path': str(path.relative_to(ROOT)), 'sha256': sha(raw),
                               'canonical_sha256': canonical(public[k])})
    cases = []
    plans = []
    for k in range(1, 16):
        for variant in range(4):
            plans.append(('public_prefix', k, variant, FAMILIES[(k * 3 + variant * 2) % 8]))
    for f, family in enumerate(FAMILIES):
        for variant in range(4):
            plans.append(('composition', f, variant, family))
    for variant in range(4):
        plans.append(('stress', variant, 0, FAMILIES[variant * 2]))
    for index, (kind, group, variant, family) in enumerate(plans):
        seed = MASTER_SEED + index * 1000003
        rng = random.Random(seed)
        prefix_length = 0
        if kind == 'public_prefix':
            bands = [(0.01, 0.07), (0.19, 0.37), (0.56, 0.79), (0.08, 0.93)]
            lo, hi = bands[variant]
            prefix_length = max(1, min(len(public[group]) - 1,
                                      round(len(public[group]) * rng.uniform(lo, hi))))
            prefix = public[group][:prefix_length]
            suffix_budget = rng.randint(3600, 13500)
            target_n = min(200000, prefix_length + suffix_budget)
        elif kind == 'stress':
            prefix = []
            target_n = 200000
        else:
            prefix = []
            target_n = rng.randint(4200, 24000)
        params = {'phase_length': rng.randint(51, 401) if kind != 'stress' else rng.randint(701, 2301),
                  'stride': rng.randint(3, 11), 'size_offset': rng.randrange(5),
                  'young_probability': rng.uniform(0.18, 0.82),
                  'planned_operations': target_n, 'prefix_length': prefix_length}
        # Structural-only retries: no allocation outputs or solver measurements exist here.
        for attempt in range(100):
            trial_rng = random.Random(seed + attempt * 1000000007)
            s = Stream(prefix)
            available = target_n - prefix_length
            body = int(available * (0.69 if kind == 'stress' else 0.62))
            evolve(s, trial_rng, body, family, params)
            tail_start = len(s.commands)
            while len(s.commands) < target_n:
                s.add(next_size(trial_rng, (len(s.commands) // params['phase_length'] + 2) % 5))
            upper = s.volume / (20 * math.ceil(s.peak / 20))
            digest = canonical(s.commands)
            if upper >= 0.85 and s.volume > 0 and digest not in known:
                break
        else:
            raise RuntimeError(f'No structurally eligible unique stream for {index}')
        name = (f'{index + 1:02d}-{kind}-open{group:02d}-v{variant + 1}' if kind == 'public_prefix'
                else f'{index + 1:02d}-{kind}-{family}-v{variant + 1}')
        path = out / 'inputs' / f'{name}.in'
        payload = f'1\n{len(s.commands)}\n' + '\n'.join(map(str, s.commands)) + '\n'
        path.write_text(payload, encoding='ascii')
        checked = harness.parse_test(path)
        assert checked['operation_count'] == len(s.commands)
        assert checked['final_occupied_length_m'] == s.volume
        assert checked['peak_live_pipe_length_m'] == s.peak
        assert checked['kpi_upper_bound_from_live_volume'] >= 0.85
        known.add(digest)
        cases.append({'name': name, 'path': str(path.relative_to(out)), 'kind': kind,
                      'family': family, 'seed': seed, 'structural_attempt': attempt,
                      'parameters': params, 'public_input': group if kind == 'public_prefix' else None,
                      'prefix_band': ['short', 'medium', 'long', 'mixed'][variant] if kind == 'public_prefix' else None,
                      'tail_insertion_operations': target_n - tail_start,
                      'canonical_sha256': digest, 'sha256': sha(path.read_bytes()),
                      'operations': len(s.commands), 'placements': len(s.lengths) - 1,
                      'peak_active_pipes': s.peak_active, 'final_volume': s.volume,
                      'peak_volume': s.peak, 'U': upper, 'parser_validation': checked})
    manifest = {'schema': 'pipes-fresh-input-only-v1', 'created_utc': datetime.now(timezone.utc).isoformat(),
                'frozen_before_solver_evaluation': True, 'master_seed': MASTER_SEED,
                'count': len(cases), 'counts': {'public_prefix': 60, 'composition': 32, 'stress': 4},
                'generator_sha256': sha(Path(__file__).read_bytes()),
                'parser_path': 'tools/pipes_harness.py',
                'parser_sha256': sha((ROOT / 'tools/pipes_harness.py').read_bytes()),
                'public_sources': public_sources, 'inventory_sources': inventory_sources,
                'inventory_distinct_canonical_hashes_checked': initial_known,
                'duplicate_streams_against_inventory': 0, 'duplicate_streams_internal': 0,
                'canonical_encoding': 'uint32_le N followed by N int32_le commands; weight excluded',
                'corpus_canonical_sha256': sha(''.join(c['canonical_sha256'] + '\n' for c in cases).encode()),
                'selection': 'Only legality, N<=200000, positive final volume, U>=0.85, and exact input uniqueness. No solver execution or solver-dependent selection.',
                'independence': ['New master seed and locally authored generator; no old suffix is read or reused.',
                                 'Public-prefix cases retain only an explicitly declared initial segment; suffix uses independent PRNG seed.',
                                 '32 composition streams use eight mechanisms, four independent seeds each, and no public commands.',
                                 'Four 200000-operation stress streams use separate seeds and longer phase intervals.',
                                 'Only public input files, inventory hashes, parser and task rules are read; compared solver source/results are not read.',
                                 'Mechanisms are newly composed here; globally unseen mechanism novelty is not claimed.',
                                 'Insertion-only tails preserve high final volume; their lengths are disclosed per case.'],
                'cases': cases}
    manifest_path = out / 'manifest.json'
    manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + '\n')
    freeze = {'manifest_sha256': sha(manifest_path.read_bytes()),
              'generator_sha256': manifest['generator_sha256'], 'count': len(cases),
              'corpus_canonical_sha256': manifest['corpus_canonical_sha256'],
              'min_U': min(c['U'] for c in cases), 'solvers_executed': 0,
              'freeze_policy': 'Do not modify or adapt inputs/generator/manifest after solver evaluation; create a new corpus for any later study.'}
    (out / 'freeze.json').write_text(json.dumps(freeze, indent=2) + '\n')
    print(json.dumps(freeze, indent=2))

if __name__ == '__main__':
    main()
