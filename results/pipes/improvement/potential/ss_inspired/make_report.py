import csv
import hashlib
import json
from pathlib import Path

ROOT = Path.cwd()
OUT = Path('results/pipes/improvement/potential/ss_inspired')
BASELINE_SUMMARY = Path('results/pipes/final/open-run-scoped-overlay/summary.json')
BASELINE_MANIFEST = Path('results/pipes/final/manifest.json')
HARNESS = Path('tools/pipes_harness.py')
INTERACTOR_SOURCE = Path('vendor/pipes_official/interactor.cpp')
INTERACTOR_BINARY = Path('results/pipes/final/bin/interactor')
SOURCE = OUT / 'ss_potential.cpp'
VARIANTS = {
    'expected_dig': {
        'name': 'SS expected next-demand dig cost',
        'binary': OUT / 'bin/ss_expected_dig',
        'summary': OUT / 'runs/ss_expected_dig/summary.json',
        'formula': 'P_A = -sum_l f_l * 1[N_l=0] * ceil(max(0,l-T)/20). Maximize P_A among equal scoreGap candidates.',
        'build': 'clang++ -O2 -std=c++20 -Wall -Wextra -Wconversion -Wshadow -pedantic -Werror -DSS_FORMULA=1 results/pipes/improvement/potential/ss_inspired/ss_potential.cpp -o results/pipes/improvement/potential/ss_inspired/bin/ss_expected_dig',
        'run': 'python3 tools/pipes_harness.py --solver results/pipes/improvement/potential/ss_inspired/bin/ss_expected_dig --name ss-expected-next-demand-dig-cost --interactor results/pipes/final/bin/interactor --tests data/pipes/open --out results/pipes/improvement/potential/ss_inspired/runs/ss_expected_dig --wall-timeout 30',
    },
    'log_availability': {
        'name': 'SS log fit availability minus tail dig cost',
        'binary': OUT / 'bin/ss_log_availability',
        'summary': OUT / 'runs/ss_log_availability/summary.json',
        'formula': 'P_B = sum_l f_l * log(1+N_l) - sum_l f_l * 1[N_l=0] * ceil(max(0,l-T)/20). Maximize P_B among equal scoreGap candidates.',
        'build': 'clang++ -O2 -std=c++20 -Wall -Wextra -Wconversion -Wshadow -pedantic -Werror -DSS_FORMULA=2 results/pipes/improvement/potential/ss_inspired/ss_potential.cpp -o results/pipes/improvement/potential/ss_inspired/bin/ss_log_availability',
        'run': 'python3 tools/pipes_harness.py --solver results/pipes/improvement/potential/ss_inspired/bin/ss_log_availability --name ss-log-fit-availability-minus-tail-dig-cost --interactor results/pipes/final/bin/interactor --tests data/pipes/open --out results/pipes/improvement/potential/ss_inspired/runs/ss_log_availability --wall-timeout 30',
    },
}

def sha(path):
    h = hashlib.sha256()
    with Path(path).open('rb') as f:
        for block in iter(lambda: f.read(1024 * 1024), b''):
            h.update(block)
    return h.hexdigest()

def load(path):
    return json.loads(Path(path).read_text())

baseline = load(BASELINE_SUMMARY)
baseline_manifest = load(BASELINE_MANIFEST)
base_by_case = {str(r['case']): r for r in baseline['records']}
variants = {key: {**spec, 'data': load(spec['summary'])} for key, spec in VARIANTS.items()}
for spec in variants.values():
    spec['by_case'] = {str(r['case']): r for r in spec['data']['records']}
    assert set(spec['by_case']) == set(base_by_case)
    for case, br in base_by_case.items():
        assert spec['by_case'][case]['test_sha256'] == br['test_sha256']
        assert spec['by_case'][case]['status'] == 'ok'

csv_path = OUT / 'per_case_comparison.csv'
columns = ['case', 'weight', 'input_sha256']
for prefix in ['baseline', *variants.keys()]:
    columns += [f'{prefix}_weighted_score', f'{prefix}_score_delta',
                f'{prefix}_trench_m', f'{prefix}_trench_delta_m',
                f'{prefix}_solver_cpu_s', f'{prefix}_solver_rss_mib']
with csv_path.open('w', newline='') as f:
    writer = csv.DictWriter(f, fieldnames=columns)
    writer.writeheader()
    ordered_cases = sorted(base_by_case, key=int)
    for case in ordered_cases:
        br = base_by_case[case]
        row = {'case': case, 'weight': br['weight'], 'input_sha256': br['test_sha256']}
        row.update({
            'baseline_weighted_score': br['weighted_score'],
            'baseline_score_delta': 0.0,
            'baseline_trench_m': br['trench_length_m'],
            'baseline_trench_delta_m': 0,
            'baseline_solver_cpu_s': br['solver_cpu_total_s'],
            'baseline_solver_rss_mib': br['solver_peak_rss_mb'],
        })
        for key, spec in variants.items():
            r = spec['by_case'][case]
            row.update({
                f'{key}_weighted_score': r['weighted_score'],
                f'{key}_score_delta': r['weighted_score'] - br['weighted_score'],
                f'{key}_trench_m': r['trench_length_m'],
                f'{key}_trench_delta_m': r['trench_length_m'] - br['trench_length_m'],
                f'{key}_solver_cpu_s': r['solver_cpu_total_s'],
                f'{key}_solver_rss_mib': r['solver_peak_rss_mb'],
            })
        writer.writerow(row)

open_tests = sorted(Path('data/pipes/open').glob('*.in'), key=lambda p: int(p.stem))
manifest = {
    'experiment': 'SS-inspired gap-histogram potential tie-breaks',
    'source_baseline': {
        'path': 'results/pipes/final/solution.cpp',
        'sha256': sha('results/pipes/final/solution.cpp'),
        'expected_sha256': 'e95ed98e038aad6f46ccf62f4f167a45b2f1cc695772484d53001936c178df41',
        'unchanged_from_requested_source': sha('results/pipes/final/solution.cpp') == 'e95ed98e038aad6f46ccf62f4f167a45b2f1cc695772484d53001936c178df41',
        'candidate_source_path': str(SOURCE),
        'candidate_source_sha256': sha(SOURCE),
    },
    'official_baseline': {
        'manifest_path': str(BASELINE_MANIFEST),
        'summary_path': str(BASELINE_SUMMARY),
        'source_sha256': baseline_manifest['source']['sha256'],
        'binary_path': baseline_manifest['build']['binary_path'],
        'binary_sha256': baseline_manifest['build']['binary_sha256'],
        'weighted_score_sum': baseline['weighted_score_sum'],
        'ok_count': baseline['ok_count'],
    },
    'selection_gate': {
        'required_score_strictly_greater_than': 29.781127,
        'open_gate_passed': any(v['data']['weighted_score_sum'] > 29.781127 for v in variants.values()),
        'independent_repeat_run': False,
        'holdout_v2_run': False,
        'stress_run': False,
        'reason': 'Neither screened candidate exceeded 29.781127; stopped at open-set gate.',
    },
    'toolchain_and_harness': {
        'compile_flags': ['-O2', '-std=c++20', '-Wall', '-Wextra', '-Wconversion', '-Wshadow', '-pedantic', '-Werror'],
        'strict_warnings_passed': True,
        'harness_path': str(HARNESS),
        'harness_sha256': sha(HARNESS),
        'official_interactor_source_path': str(INTERACTOR_SOURCE),
        'official_interactor_source_sha256': sha(INTERACTOR_SOURCE),
        'official_interactor_binary_path': str(INTERACTOR_BINARY),
        'official_interactor_binary_sha256': sha(INTERACTOR_BINARY),
    },
    'dataset': {
        'path': 'data/pipes/open',
        'is_official_open_test_set': True,
        'case_count': len(open_tests),
        'input_sha256': {p.stem: sha(p) for p in open_tests},
    },
    'variants': {},
    'comparison_csv': str(csv_path),
}
for key, spec in variants.items():
    data = spec['data']
    recs = data['records']
    manifest['variants'][key] = {
        'description': spec['name'],
        'formula': spec['formula'],
        'binary_path': str(spec['binary']),
        'binary_sha256': sha(spec['binary']),
        'build_command': spec['build'],
        'harness_command': spec['run'],
        'summary_path': str(spec['summary']),
        'weighted_score_sum': data['weighted_score_sum'],
        'delta_vs_official_baseline': data['weighted_score_sum'] - baseline['weighted_score_sum'],
        'delta_vs_gate': data['weighted_score_sum'] - 29.781127,
        'case_count': data['case_count'],
        'ok_count': data['ok_count'],
        'max_solver_cpu_s': max(r['solver_cpu_total_s'] for r in recs),
        'max_solver_rss_mib': max(r['solver_peak_rss_mb'] for r in recs),
        'max_wall_orchestration_s': max(r['wall_orchestration_s'] for r in recs),
    }
(OUT / 'manifest.json').write_text(json.dumps(manifest, indent=2) + '\n')

report = [
    '# SS-inspired potential по гистограмме свободных gaps',
    '',
    '## Результат',
    '',
    'Проверены ровно две формулы как вторичный tie-break только при равном исходном `scoreGap`; первый критерий размещения и endpoint-правило T46 сохранены. Обе версии прошли официальный интерактивный harness на всех 15 открытых тестах. Ни одна не превысила gate `29.781127`, поэтому независимый повтор, holdout-v2 и stress не запускались.',
    '',
    '| Вариант | Балл / 32.1 | Δ к официальному baseline | Δ к gate | 15/15 | Max solver CPU | Max RSS |',
    '|---|---:|---:|---:|---:|---:|---:|',
]
for key, spec in variants.items():
    d = spec['data']
    m = manifest['variants'][key]
    report.append(f"| {spec['name']} | {d['weighted_score_sum']:.12f} | {m['delta_vs_official_baseline']:+.12f} | {m['delta_vs_gate']:+.12f} | {d['ok_count']}/15 | {m['max_solver_cpu_s']:.6f} s | {m['max_solver_rss_mib']:.3f} MiB |")
report += [
    '',
    f"Официальный baseline для сравнения — `{baseline['weighted_score_sum']:.12f}/32.1` из `{BASELINE_SUMMARY}`. Это strict open-run, привязанный manifest-ом final source hash `{baseline_manifest['source']['sha256']}`. Исторический `results/pipes/final/open-run/summary.json` относится к более раннему прогону и не использован для gate-сравнения.",
    '',
    '## Формулы и состояние после placement',
    '',
    'Пусть `f_l` — частота длины `l` среди последних максимум 2048 размещений, `N_l` — число текущих free gaps длиной не меньше `l` после гипотетического размещения, а `T` — длина реально оставшегося expandable tail. Для выбора среди совпавших `scoreGap` сравнивали оценку состояния после размещения и предпочитали большую.',
    '',
    '- **Expected next-demand dig cost:** `P_A = -Σ_l f_l · 1[N_l=0] · ceil(max(0,l−T)/20)`. Это ожидаемые дополнительные секции для следующего запроса; внутренние gaps и tail учитываются отдельно через пригодность и расширяемый остаток.',
    '- **Log fit availability:** `P_B = Σ_l f_l·log(1+N_l) − Σ_l f_l·1[N_l=0]·ceil(max(0,l−T)/20)`. Логарифм уменьшает отдачу от дублирующих gaps, а tail по-прежнему получает фактический section-cost, если ни один gap не подходит.',
    '',
    'При `highSide` placement в хвосте занимает его внешний конец: оставшийся кусок становится внутренней дырой, а expandable tail исчезает. При `lowSide` остаток продолжает быть хвостом. Для размещения во внутренней дыре хвост не меняется. Именно это преобразование использовано при вычислении обоих tie-break score. Счётчики fit-классов для длины 1–40 обновляются на `addFreeGap`/`eraseGap`.',
    '',
    '## Per-case и ресурсы',
    '',
    'Все per-case weighted scores, длины траншеи, CPU и RSS для baseline и обоих вариантов приведены в [per_case_comparison.csv](per_case_comparison.csv). Полные official harness outputs сохранены в `runs/ss_expected_dig/` и `runs/ss_log_availability/`; source, binaries, interactor, inputs и воспроизводимые команды перечислены в [manifest.json](manifest.json).',
    '',
    f"По сравнению с baseline ожидаемый-dig вариант прибавил траншею на тестах 5 (+580 м), 7 (+80 м), 14 (+20 м), 15 (+60 м) и ухудшил score на тестах 5, 7, 14, 15; выигрыш на 11-м тесте составил около +0.006412 weighted score. Лог-вариант не превзошёл expected-dig: его итог ниже на {variants['expected_dig']['data']['weighted_score_sum'] - variants['log_availability']['data']['weighted_score_sum']:.12f}.",
    '',
    '## Вывод',
    '',
    f"Эти две одноступенчатые histogram-потенциальные оценки не дают достаточного улучшения: лучший результат `{variants['expected_dig']['data']['weighted_score_sum']:.12f}` ниже gate на `{29.781127 - variants['expected_dig']['data']['weighted_score_sum']:.12f}` и ниже официального baseline на `{baseline['weighted_score_sum'] - variants['expected_dig']['data']['weighted_score_sum']:.12f}`. Ветку останавливаю; нового кандидата для продвижения нет. В solver нет ветвления по test ID, номеру команды или будущим входным данным.",
    '',
    '## Воспроизведение',
    '',
    'Сборка и запуск использовали команды из `manifest.json`. Оба варианта собраны с `-Werror` и прогнаны командой `python3 tools/pipes_harness.py` на `data/pipes/open` с локально собранным official interactor. `results/pipes/final/solution.cpp` остался неизменённым.'
]
(OUT / 'REPORT.md').write_text('\n'.join(report) + '\n')
