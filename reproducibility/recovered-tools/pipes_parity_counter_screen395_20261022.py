"""Read-only counter diagnostic; no solver, geometry, generation, or report files.

Only frozen round3 screen383 + development12 inputs may be opened. Run explicitly
in the sole evaluator. Counter reconstruction is exact after importObserved;
without a source-pinned observed handoff it is labelled proxy/counterfactual.
"""
import argparse
import collections
import hashlib
import json
import re
from pathlib import Path

CPP_SHA = '1cb3af5bba22e7176d7533d2c20ff6dab5b96bc0cdf1c1ac3046b537ccdcd1b0'
CPP_BIN_SHA = 'f39c5b0b15b6bda0cf67da8ec63953040b503cfaf87b78496a9b68ee5998765c'
FLAGS = {'-DRESERVATION_POLICY=1', '-DLAZY_SLAB=1', '-DREPLAY_GUARD=5'}
KINDS = ('baseline', 'ordinary-bf-all', 'ordinary-bf-large')


def emit(label, obj):
    print(label, json.dumps(obj, ensure_ascii=False, sort_keys=True), flush=True)


def selected_rows(path, ids, required=None):
    """Skip unselected rows before JSON parsing, including sealed-final rows."""
    with path.open() as stream:
        for line in stream:
            if required and required not in line:
                continue
            match = re.search(r'"id"\s*:\s*"([^"]+)"', line)
            if match and match[1] in ids:
                yield json.loads(line)


def counters(commands):
    # Runs compress exactly the last2048 positive observations, including slab
    # placements. Neither physical positions nor observedRunCount enters steady.
    runs = collections.deque()
    history_size = 0
    occurrences = [0] * 41
    removed = [[0, 0] for _ in range(41)]
    pipes = [None]
    supported = set()
    first = None
    last_pid = last_length = -1
    stride = 0
    post_trigger = [0, 0]
    new_trigger = [0, 0]

    def steady():
        return (history_size >= 128 and len(runs) >= 3 and
                runs[-1][0] - runs[-2][0] == runs[-2][0] - runs[-3][0])

    for step, command in enumerate(commands, 1):
        if command > 0:
            assert 1 <= command <= 40
            cohort = occurrences[command] & 1
            occurrences[command] += 1
            pipes.append((command, cohort))
            if runs and runs[-1][0] == command:
                runs[-1][1] += 1
            else:
                runs.append([command, 1])
            history_size += 1
            if history_size > 2048:
                runs[0][1] -= 1
                if runs[0][1] == 0:
                    runs.popleft()
                history_size -= 1
            continue
        pid = -command
        assert 0 < pid < len(pipes) and pipes[pid] is not None
        length, cohort = pipes[pid]
        pipes[pid] = None
        stride = stride + 1 if length == last_length and pid == last_pid + 2 else 0
        last_pid, last_length = pid, length
        removed[length][cohort] += 1
        pair = removed[length]
        if sum(pair) >= 8 and max(pair) * 100 >= sum(pair) * 85 and steady():
            supported.add(length)
            if first is None:
                first = dict(step=step, trigger_length=length, counts=list(pair),
                             dominant_cohort=0 if pair[0] > pair[1] else 1,
                             last_placement_pid=len(pipes) - 1,
                             alternating=stride >= 7, steady=True)
        if first and step > first['step'] and length == first['trigger_length']:
            post_trigger[cohort] += 1
            if pid > first['last_placement_pid']:
                new_trigger[cohort] += 1
    return dict(first_latch=first, parity_latched=first is not None,
                supporting_lengths=sorted(supported), single_size_evidence=len(supported) == 1,
                end_alternating=stride >= 7, end_stride_two_transitions=stride,
                end_steady=steady(), trigger_deaths_after_latch=post_trigger,
                trigger_newborn_deaths_after_latch=new_trigger)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root', type=Path, default=Path('/Users/555tery/techarena'))
    parser.add_argument('--detail-limit', type=int, default=12)
    args = parser.parse_args()
    root = args.root
    directory = root / 'prototypes/pipes_round3_20261022'
    records = directory / 'records.jsonl'
    gates, builds = [], {}
    # Do not load unrelated evaluation rows or any sealed-final payload.
    for line in records.open():
        if '"development_gate_freeze"' in line:
            gates.append(json.loads(line))
        elif '"build"' in line:
            row = json.loads(line)
            if row.get('kind') in KINDS and row.get('language') == 'cpp':
                assert row['status'] == 0
                assert FLAGS <= set(row['command']), 'Unexpected BF policy flags'
                builds[row['kind']] = (row['source_sha256'], row['binary_sha256'])
    assert len(gates) == 1
    gate = gates[0]
    assert gate['baseline_cpp_sha256'] == CPP_SHA
    ids = gate['screen383_ids'] + gate['new12_ids']
    assert len(ids) == len(set(ids)) == 395
    wanted = set(ids)
    meta = {m['id']: m for m in selected_rows(directory / 'input_manifest.jsonl', wanted)}
    assert set(meta) == wanted
    assert all(m['split'] != 'sealed_final' for m in meta.values())
    expected = dict(builds, baseline=(CPP_SHA, CPP_BIN_SHA))
    values = {kind: {} for kind in KINDS}
    for row in selected_rows(records, wanted, 'development-screen395'):
        kind = row.get('kind')
        if (row.get('type') == 'evaluation' and kind in values and
                row.get('language') == 'cpp' and row.get('status') == 'ok' and
                (row.get('source_sha256'), row.get('binary_sha256')) == expected.get(kind)):
            assert row['test_sha256'] == meta[row['id']]['test_sha256']
            values[kind][row['id']] = row
    assert all(set(values[k]) == wanted for k in KINDS), 'Finish all395 paired screens first'
    # Baseline round3 rows often reuse scores without stderr. Recover only
    # source-matched original metadata; never infer handoff from another policy.
    handoffs = {}
    baseline_builds = 0
    for path in [root / 'prototypes/pipes_round2_20261022/records.jsonl', records]:
        for line in path.open():
            if '"build"' not in line:
                continue
            row = json.loads(line)
            if (row.get('type') == 'build' and row.get('language') == 'cpp' and
                    row.get('source_sha256') == CPP_SHA and row.get('binary_sha256') == CPP_BIN_SHA):
                if row.get('alias_only'):
                    continue
                assert isinstance(row.get('command'), list), 'Missing real compiler command'
                assert row['status'] == 0 and FLAGS <= set(row['command'])
                baseline_builds += 1
        for row in selected_rows(path, wanted):
            if (row.get('source_sha256') != CPP_SHA or row.get('language') != 'cpp'
                    or row.get('binary_sha256') != CPP_BIN_SHA or row.get('status') != 'ok'):
                continue
            match = re.search(r'\babort_step=(\d+)\b', row.get('candidate_stderr') or '')
            if match:
                assert row['test_sha256'] == meta[row['id']]['test_sha256']
                step = int(match[1])
                assert row['id'] not in handoffs or handoffs[row['id']] == step
                handoffs[row['id']] = step
    assert baseline_builds > 0, 'Missing exact baseline source/binary/flags build provenance'
    groups = {'all395': set(ids)}
    for name, scenario in gate['scenarios'].items():
        groups[name + ':cheap'] = set(scenario['cheap'])
        groups[name + ':expensive'] = set(scenario['expensive'])
    summaries = {name: collections.Counter() for name in groups}
    details = []
    for index, ident in enumerate(ids, 1):
        m = meta[ident]
        path = Path(m['test_file'])
        if not path.is_absolute():
            path = root / path
        raw = path.read_bytes()
        assert hashlib.sha256(raw).hexdigest() == m['test_sha256']
        tokens = raw.split()
        n = int(tokens[1])
        assert n == m['operation_count']
        commands = list(map(int, tokens[2:2+n]))
        assert len(commands) == n and all(commands)
        diagnostic = counters(commands)
        abort = handoffs.get(ident)
        scope = ('proxy_unknown_handoff' if abort is None else
                 'counterfactual_no_core' if abort == 0 else 'exact_counters_after_import')
        first = diagnostic['first_latch']
        diagnostic.update(id=ident, family=m.get('family'), provenance=m.get('provenance'),
                          scope=scope, abort_step=abort,
                          actual_core_latch_step=max(abort, first['step'])
                          if abort and first else None,
                          first_latch_replayed_in_import=bool(abort and first and first['step'] < abort))
        baseline = values['baseline'][ident]['kpi']
        deltas = {k: values[k][ident]['kpi'] - baseline for k in KINDS[1:]}
        suspect = (diagnostic['single_size_evidence'] and
                   not diagnostic['end_alternating'] and not diagnostic['end_steady'])
        tags = [scope, 'n', 'latched' if first else 'never_latched']
        if suspect:
            tags.append('single_size_with_end_evidence_absent')
        if baseline < .85:
            tags.append('baseline_below_085')
            if suspect:
                tags.append('below085_and_single_size_end_absent')
        for kind, delta in deltas.items():
            result = 'win' if delta > 1e-12 else 'loss' if delta < -1e-12 else 'tie'
            tags.append(kind + ':' + result)
            if suspect:
                tags.append('single_size_end_absent:' + kind + ':' + result)
        for name, members in groups.items():
            if ident in members:
                summaries[name].update(tags)
        if baseline < .85 and first:
            diagnostic.update(baseline_kpi=baseline, bf_kpi_deltas=deltas,
                              descriptive_suspect=suspect)
            details.append(diagnostic)
        if index % 50 == 0:
            emit('progress', dict(processed=index, selected=395))
    emit('scope', dict(selected=395, no_geometry=True, no_policy_or_KPI_replay=True,
                      final24_opened=False, suspicious_tag_is_descriptive_not_causal=True,
                      import_argument='PID lengths, occurrence parity, recent2048 lengths, '
                      'removal counts and stride2 updates match importObserved and real core; '
                      'run/slab histories do not enter this counter subset'))
    for name, summary in summaries.items():
        emit('summary:' + name, dict(summary))
    for row in sorted(details, key=lambda d: d['baseline_kpi'])[:args.detail_limit]:
        emit('low_kpi_latched_case', row)


if __name__ == '__main__':
    main()
