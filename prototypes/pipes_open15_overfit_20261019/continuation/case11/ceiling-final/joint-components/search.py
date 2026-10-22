import bisect, hashlib, json, math, sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[3]))
from runtime import ROOT, PARENT, REPO, e

OUT = ROOT / 'case11' / 'ceiling-final' / 'joint-components'
SOURCE = ROOT / 'case11' / 'ceiling-final' / 'positions.txt'
INPUT11 = REPO / 'data/pipes/open/11.in'
INPUT15 = REPO / 'data/pipes/open/15.in'
PREFIX_COMMANDS = 4999
PREFIX_PIPES = 4006
TARGET15 = 418780


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def read_case(path):
    tok = list(map(int, Path(path).read_text().split()))
    n = tok[1]
    cmd = tok[2:]
    assert len(cmd) == n or (len(cmd) == n+1 and cmd[-1] == 0)
    cmd = cmd[:n]
    lens = [0]
    birth = [0]
    death = [n]  # index 0 unused
    pidat = [0] * n
    pid = 0
    for t, c in enumerate(cmd):
        if c > 0:
            pid += 1
            pidat[t] = pid
            lens.append(c)
            birth.append(t)
            death.append(n)
        else:
            assert 0 < -c <= pid
            death[-c] = t
    assert pid == len(lens) - 1
    return cmd, lens, birth, death, pidat


def physical_replay(path, positions):
    import numpy as np
    cmd, lens, birth, death, pidat = read_case(path)
    assert len(positions) == len(lens) - 1
    maxend = max((x + lens[i] for i, x in enumerate(positions, 1)), default=0)
    owner = np.zeros(maxend, dtype=np.int32)
    active, peak, live_ids = 0, 0, set()
    for t, c in enumerate(cmd):
        if c > 0:
            pid = pidat[t]
            x, r = positions[pid - 1], positions[pid - 1] + c
            assert x >= 0 and r <= maxend
            assert all(owner[z] == 0 for z in range(x, r)), (t, pid, x, r)
            for z in range(x, r):
                owner[z] = pid
            active += c
            live_ids.add(pid)
            peak = max(peak, active)
        else:
            pid = -c
            assert pid in live_ids, (t, pid, 'not live')
            x, r = positions[pid - 1], positions[pid - 1] + lens[pid]
            assert all(owner[z] == pid for z in range(x, r)), (t, pid, x, r)
            for z in range(x, r):
                owner[z] = 0
            active -= lens[pid]
            live_ids.remove(pid)
    extent = max((x + lens[i] for i, x in enumerate(positions, 1)), default=0)
    return {'commands': len(cmd), 'pipes': len(lens)-1, 'peak_volume': peak,
            'extent': extent, 'T': 20 * ((extent + 19) // 20),
            'pid1': {'x': positions[0], 'length': lens[1], 'birth': birth[1],
                     'death': death[1], 'immortal': death[1] == len(cmd)}}


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    c11, lens11, b11, d11, _ = read_case(INPUT11)
    c15, lens15, b15, d15, _ = read_case(INPUT15)
    assert c11[:PREFIX_COMMANDS] == c15[:PREFIX_COMMANDS]
    assert sum(x > 0 for x in c11[:PREFIX_COMMANDS]) == PREFIX_PIPES
    srcpos = list(map(int, SOURCE.read_text().split()))
    assert len(srcpos) == len(lens11)-1
    src_replay = physical_replay(INPUT11, srcpos)
    assert src_replay['T'] == 20760 and src_replay['pid1']['x'] == 0
    assert sha(SOURCE) == '640ad400bdf1578b7bb80235540ff51e3c2b39e984f7e90a9a622bbcacabeb8b'

    live15 = {pid for pid in range(1, len(lens15)) if d15[pid] == len(c15)}
    dead15 = {pid: d15[pid] for pid in range(1, len(lens15)) if d15[pid] < len(c15)}

    cs = []
    for l, r in sorted((x, x+n) for x, n in zip(srcpos, lens11[1:])):
        if not cs or l >= cs[-1][1]:
            cs.append([l, r])
        else:
            cs[-1][1] = max(cs[-1][1], r)
    starts = [c[0] for c in cs]
    comp = [bisect.bisect_right(starts, x)-1 for x in srcpos]
    assert all(k >= 0 and srcpos[i]+lens11[i+1] <= cs[k][1] for i,k in enumerate(comp))
    first = comp[0]
    full, pin, last = [0]*len(cs), [0]*len(cs), [0]*len(cs)
    for i, x in enumerate(srcpos[:PREFIX_PIPES]):
        k = comp[i]
        pin[k] += lens11[i+1]
        pid = i+1
        if pid in live15:
            full[k] += lens11[i+1]
        else:
            last[k] = max(last[k], dead15.get(pid, 0))

    best = None
    mode_results = []
    for mode in range(8):
        def key(k):
            width = cs[k][1]-cs[k][0]
            if k == first:
                return (-10, 0, 0)
            group = mode//2
            if group == 0:
                return (-full[k]/width, -full[k], k)
            if group == 1:
                return (-int(full[k] > 0), last[k], k)
            if group == 2:
                return (-int(full[k] > 0), -last[k], k)
            return (-int(full[k] > 0), -int(pin[k] > 0), k)
        order = sorted(range(len(cs)), key=key)
        at, newstart = 0, {}
        for k in order:
            newstart[k] = at
            at += cs[k][1]-cs[k][0]
        newpos = []
        for x, n, k in zip(srcpos, lens11[1:], comp):
            rel = x-cs[k][0]
            if mode % 2 and k != first:
                rel = cs[k][1]-cs[k][0]-rel-n
            newpos.append(newstart[k]+rel)
        assert newpos[0] == 0
        replay11 = physical_replay(INPUT11, newpos)
        assert replay11['T'] == 20760 and replay11['pid1']['immortal']
        assert replay11['pid1']['x'] == 0
        d = OUT / f'mode-{mode}'
        d.mkdir(exist_ok=False)
        p11 = d/'11.txt'
        p11.write_text('\n'.join(map(str, newpos))+'\n')
        pins = d/'pins.txt'
        pins.write_text('\n'.join(map(str, newpos[:PREFIX_PIPES]))+'\n')
        # Match the established suite, but try the former best knapsack mode first.
        methods = [('conditioned_knapsack', [2002, 2000, 2001, 2003]),
                   ('conditioned_reverse', [2, 3, 1, 5]),
                   ('conditioned', [0])]
        best15 = None
        attempts = []
        for method, modes in methods:
            for m in modes:
                plan = d/f'15-{method}-{m}.txt'
                log = f'{method}-{m}.log'
                rc = e.invoke([str(ROOT/method), str(INPUT15), str(pins),
                               str(PREFIX_COMMANDS), str(plan), str(m)], d, log, 120)
                if rc != 0:
                    attempts.append({'method': method, 'mode': m, 'returncode': rc,
                                     'log': log})
                    continue
                t15 = int((d/log).read_text().strip().splitlines()[-1])
                if not plan.exists():
                    attempts.append({'method': method, 'mode': m, 'T15': t15,
                                     'error': 'successful planner did not write plan'})
                    continue
                pos15 = list(map(int, plan.read_text().split()))
                replay15 = physical_replay(INPUT15, pos15)
                assert replay15['T'] == t15, (mode, method, m, t15, replay15)
                assert pos15[:PREFIX_PIPES] == newpos[:PREFIX_PIPES]
                item = {'component_mode': mode, 'method': method, 'mode': m, 'T15': t15,
                        'plan15': str(plan), 'sha256': sha(plan),
                        'replay15': replay15, 'log': log}
                attempts.append(item)
                if best15 is None or t15 < best15['T15']:
                    best15 = item
                    e.save(d/'best15.json', best15)
                    print(json.dumps({'mode': mode, 'method': method, 'planner_mode': m,
                                      'T11': replay11['T'], 'T15': t15,
                                      'plan15': str(plan)}, ensure_ascii=False), flush=True)
                if best15['T15'] == TARGET15:
                    break
            if best15 and best15['T15'] == TARGET15:
                break
        summary = {'component_mode': mode, 'components': len(cs),
                   'component_span': at, 'T11': replay11['T'],
                   'plan11': str(p11), 'plan11_sha256': sha(p11),
                   'attempts': attempts, 'best15': best15}
        e.save(d/'result.json', summary)
        mode_results.append(summary)
        if best15 and (best is None or best15['T15'] < best['T15']):
            best = best15
            e.save(OUT/'best15.json', best)
        if best and best['T15'] <= 418800:
            break
    if best:
        chosen = next(x for x in mode_results if x['component_mode'] == best['component_mode'])
        best_result = {'component_mode': best['component_mode'], 'components': len(cs),
                       'source11': str(SOURCE), 'source11_sha256': sha(SOURCE),
                       'plan11': chosen['plan11'], 'plan11_sha256': chosen['plan11_sha256'],
                       'T11': chosen['T11'],
                       'plan15': best['plan15'], 'plan15_sha256': best['sha256'],
                       'T15': best['T15'], 'replay15': best['replay15'],
                       'method': best['method'], 'planner_mode': best['mode'],
                       'combined_sum': chosen['T11']+best['T15'],
                       'combined_objective': 20361/chosen['T11']+10*418757/best['T15']}
        e.save(OUT/'best.json', best_result)
    e.save(OUT/'report.json', {
        'status': 'complete', 'source_sha256': sha(SOURCE),
        'input11_sha256': sha(INPUT11), 'input15_sha256': sha(INPUT15),
        'prefix_commands': PREFIX_COMMANDS, 'prefix_pipes': PREFIX_PIPES,
        'component_count': len(cs), 'source_replay11': src_replay,
        'searched_orders': len(mode_results), 'mode_results': mode_results,
        'best15': best,
        'best_combined_sum': (20760 + best['T15']) if best else None,
        'best_combined_objective': (20361/20760+10*418757/best['T15']) if best else None,
    })

if __name__ == '__main__':
    main()
