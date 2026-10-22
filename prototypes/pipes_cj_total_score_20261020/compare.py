#!/usr/bin/env python3
"""Contest-score scenarios from frozen paired results; no solver execution."""
from __future__ import annotations

import hashlib
import html
import itertools
import json
import math
import random
import statistics
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
SOURCE = ROOT / "prototypes/pipes_all2537_comparison_20261020"
METHODS = ("online_cpp", "hybrid")
LABELS = {"online_cpp": "Нынешний online на Cangjie",
          "hybrid": "Осторожный гибрид на Cangjie — при сохранении KPI"}
SEED = 202610202537
REPLICATES = 100000


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def comb(n, k):
    return math.comb(n, k) if n >= k else 0


def exact_top2_of4(values):
    """Uniform four distinct items; arbitrary ordering of equal values is safe."""
    v = sorted(values)
    n = len(v)
    assert n >= 4
    weights = [comb(i, 3) + (n - i - 1) * comb(i, 2) for i in range(n)]
    denominator = comb(n, 4)
    assert sum(weights) == 2 * denominator
    return math.fsum(x * w for x, w in zip(v, weights)) / denominator


def quantile(values, q):
    values = sorted(values)
    pos = (len(values) - 1) * q
    low = math.floor(pos)
    high = math.ceil(pos)
    return values[low] + (values[high] - values[low]) * (pos - low)


def summarize(values):
    return {
        "mean": statistics.fmean(values),
        "p05": quantile(values, .05),
        "median": statistics.median(values),
        "p95": quantile(values, .95),
    }


def simulate(cheap, expensive, shared_pool, open_scores, seed):
    rng = random.Random(seed)
    totals = {m: [] for m in METHODS}
    deltas = []
    for _ in range(REPLICATES):
        if shared_pool:
            sample = rng.sample(cheap, 15)
            eleven, four = sample[:11], sample[11:]
        else:
            four, eleven = rng.sample(expensive, 4), rng.sample(cheap, 11)
        pair = {}
        for i, method in enumerate(METHODS):
            ks = [row[i] for row in four]
            score = (open_scores[method]
                     + 4 * math.fsum(row[i] for row in eleven)
                     + 10 * math.fsum(ks)
                     + 10 * math.fsum(sorted(ks)[-2:]))
            totals[method].append(score)
            pair[method] = score
        deltas.append(pair["hybrid"] - pair["online_cpp"])
    return {
        "replicates": REPLICATES,
        "seed": seed,
        "draws": "Same distinct test IDs for both methods; uniform sampling without replacement within the stated pools.",
        "score_distributions": {m: summarize(v) for m, v in totals.items()},
        "paired_delta_hybrid_minus_online": summarize(deltas),
        "standard_error_of_simulated_mean_delta": statistics.stdev(deltas) / math.sqrt(REPLICATES),
        "hybrid_higher_fraction_under_this_sampling_model": sum(x > 0 for x in deltas) / REPLICATES,
        "equal_score_fraction_under_this_sampling_model": sum(x == 0 for x in deltas) / REPLICATES,
        "not_a_probability_of_winning_the_actual_contest": True,
    }


def main():
    for sample in ([0., .1, .1, .4, .8, 1.], [.9] * 6):
        enumerated = statistics.fmean(sum(sorted(x)[-2:]) for x in itertools.combinations(sample, 4))
        assert math.isclose(exact_top2_of4(sample), enumerated, abs_tol=1e-14)
    analysis = json.loads((SOURCE / "analysis.json").read_text())
    audit = json.loads((SOURCE / "final_audit.json").read_text())
    frozen = json.loads((SOURCE / "freeze.json").read_text())
    coverage = json.loads((SOURCE / "coverage.json").read_text())
    assert analysis["complete"] and audit["complete"]
    for name in ("analysis.json", "freeze.json", "coverage.json"):
        assert sha(SOURCE / name) == audit["artifact_sha256"][name]
    cases = [c for c in analysis["per_case_results"]
             if c["selected"] and c["public_number"] is None]
    assert len(cases) == 2526
    for c in cases:
        for m in METHODS:
            assert c["methods"][m]["within_limits"] and c["methods"][m]["raw_kpi"] is not None
            assert c["methods"][m]["raw_kpi"] == c["methods"][m]["contest_adjusted_kpi"]
    open_scores = {m: analysis["full_open15"][m]["raw_weighted_score"] for m in METHODS}
    additional_ids = set(coverage["id_sets"]["other_selected"])
    additional = [c for c in cases if c["id"] in additional_ids]
    short = [c for c in cases if c["operations"] <= 200]
    nonshort = [c for c in cases if c["operations"] > 200]
    long = [c for c in cases if c["operations"] > 100000]
    notlong = [c for c in cases if c["operations"] <= 100000]
    configs = [
        ("archive_uniform", "Равномерно из всего архива без Open15", cases, cases, True),
        ("additional_archive", "Только дополнительные архивные тесты", additional, additional, True),
        ("without_very_short", "Исключены короткие тесты до 200 команд", nonshort, nonshort, True),
        ("long_only", "Все закрытые — длиннее 100 000 команд", long, long, True),
        ("expensive_are_long", "Дорогие — длиннее 100 000, остальные — короче", notlong, long, False),
        ("short_only", "Крайний сценарий: все закрытые до 200 команд", short, short, True),
    ]
    result = {
        "scope": "Conditional score comparison, not a hidden-score forecast or a completed Cangjie hybrid port.",
        "formula": "Open15 + 4*sum(KPI16..26) + 10*sum(KPI27..30) + 10*sum(two largest among KPI27..30)",
        "closed_weights": [4] * 11 + [10] * 4,
        "closed_weight_sum": 84,
        "bonus_rule_source": "User-supplied organizer clarification: the two best-scoring tests from the most expensive closed group are counted again.",
        "statement_weight_source": "data/pipes/statement.pdf, page 3; merged weight cells visually verified.",
        "statement_sha256": sha(ROOT / "data/pipes/statement.pdf"),
        "method_sources": {m["id"]: {"source": m["original_source"], "sha256": m["source_sha256"]}
                           for m in frozen["methods"] if m["id"] in (*METHODS, "online_cj")},
        "source_hashes": {name: sha(SOURCE / name)
                          for name in ("analysis.json", "freeze.json", "coverage.json", "final_audit.json")},
        "script_sha256": sha(Path(__file__)),
        "assumptions": [
            "Both methods qualify for the same Cangjie bonus; bonus selections are made independently for each method.",
            "The hypothetical hybrid port preserves every C++ placement and incurs no resource failures. Its runtime and memory on Cangjie are not measured.",
            "All selected input streams satisfy U>=0.85, a volume upper bound; this selection may differ from the actual closed tests.",
            "The observed archive is not an independent holdout and has no known hidden-distribution sampling weights.",
            "The archived hybrid uses the older trial22 online core. This comparison is not an ablation of adding replay to the latest online core.",
            "The contest test weights are known; the mapping of hidden test mechanisms to weights is unknown.",
            "Monte Carlo quantiles and win fractions describe the explicit sampling scenarios only, not confidence intervals or a probability of winning the contest.",
            "Resource-related zeros and CPU tie-breaking for a future Cangjie hybrid cannot be established by these quality-only calculations.",
        ],
        "open15": open_scores,
        "open_advantage_hybrid": open_scores["hybrid"] - open_scores["online_cpp"],
        "scenarios": [],
    }
    for index, (name, label, cheap_cases, expensive_cases, shared) in enumerate(configs):
        if not shared:
            assert not {c["id"] for c in cheap_cases} & {c["id"] for c in expensive_cases}
        cheap = [tuple(c["methods"][m]["raw_kpi"] for m in METHODS) for c in cheap_cases]
        expensive = [tuple(c["methods"][m]["raw_kpi"] for m in METHODS) for c in expensive_cases]
        exact = {}
        for i, m in enumerate(METHODS):
            cheap_mean = statistics.fmean(x[i] for x in cheap)
            heavy_mean = statistics.fmean(x[i] for x in expensive)
            bonus = 10 * exact_top2_of4([x[i] for x in expensive])
            exact[m] = {"open15": open_scores[m], "expected_cheap_closed": 44 * cheap_mean,
                        "expected_expensive_closed": 40 * heavy_mean,
                        "expected_bonus_top2_of4": bonus,
                        "expected_total": open_scores[m] + 44 * cheap_mean + 40 * heavy_mean + bonus}
        delta = {k: exact["hybrid"][k] - exact["online_cpp"][k] for k in exact["hybrid"]}
        simulation = simulate(cheap, expensive, shared, open_scores, SEED + index)
        error = abs(simulation["paired_delta_hybrid_minus_online"]["mean"] - delta["expected_total"])
        se = simulation["standard_error_of_simulated_mean_delta"]
        assert error < 6 * se + 1e-10, (name, error, se)
        row = {"id": name, "label": label, "cheap_pool_size": len(cheap), "expensive_pool_size": len(expensive),
               "shared_pool_without_replacement": shared,
               "cheap_ids": [c["id"] for c in cheap_cases],
               "expensive_ids": [c["id"] for c in expensive_cases],
               "exact_expectation": exact, "delta_hybrid_minus_online": delta, "paired_simulation": simulation}
        result["scenarios"].append(row)
        print(json.dumps({"scenario": name, "total_online": exact["online_cpp"]["expected_total"],
                          "total_hybrid": exact["hybrid"]["expected_total"], "delta": delta["expected_total"],
                          "bonus_delta": delta["expected_bonus_top2_of4"],
                          "hybrid_higher_share": simulation["hybrid_higher_fraction_under_this_sampling_model"]}), flush=True)
    (HERE / "comparison.json").write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n")
    rows = []
    for row in result["scenarios"]:
        ex, d, sim = row["exact_expectation"], row["delta_hybrid_minus_online"], row["paired_simulation"]
        values = [row["label"], str(row["cheap_pool_size"]) + " / " + str(row["expensive_pool_size"]),
                  f'{ex["online_cpp"]["expected_total"]:.6f}', f'{ex["hybrid"]["expected_total"]:.6f}',
                  f'{d["expected_total"]:+.6f}', f'{d["expected_bonus_top2_of4"]:+.6f}',
                  f'{100*sim["hybrid_higher_fraction_under_this_sampling_model"]:.1f}%']
        rows.append("<tr>" + "".join("<td>" + html.escape(x) + "</td>" for x in values) + "</tr>")
    first = result["scenarios"][0]["exact_expectation"]
    components = []
    for key, label in [("open15", "Измеренный Open15"), ("expected_cheap_closed", "11 закрытых × 4"),
                       ("expected_expensive_closed", "4 закрытых × 10"),
                       ("expected_bonus_top2_of4", "Бонус: два лучших из четырёх"),
                       ("expected_total", "Итого в сценарии")]:
        components.append(f'<tr><th>{label}</th><td>{first["online_cpp"][key]:.6f}</td><td>{first["hybrid"][key]:.6f}</td></tr>')
    page = """<!doctype html><html lang="ru"><meta charset="utf-8"><meta name="viewport" content="width=device-width">
<title>Pipes: общий счёт с бонусом Cangjie</title>
<style>body{font:16px/1.55 system-ui;margin:0;background:#f4f6f8;color:#1d2b35}main{max-width:1250px;margin:auto;padding:28px}h1{line-height:1.2}section{background:white;border:1px solid #d9e1e6;border-radius:12px;padding:22px;margin:20px 0}.scroll{overflow:auto}table{border-collapse:collapse;width:100%;font-variant-numeric:tabular-nums}th,td{padding:10px;border-bottom:1px solid #d9e1e6;text-align:right}th:first-child,td:first-child{text-align:left}.notice{border-left:4px solid #a47816;background:#fff3d5;padding:18px}a{color:#006b68}</style>
<main><h1>Online и осторожный гибрид: общий счёт с Cangjie</h1>
<p class="notice">Это сценарный расчёт по сохранённым результатам. Гибрид ещё не перенесён на Cangjie; предполагается сохранение его C++ KPI и отсутствие превышений ресурсов. Реальный состав закрытых тестов неизвестен.</p>
<section><h2>Правило счёта</h2><p>S = Open15 + 4 × Σ KPI₁₆…₂₆ + 10 × Σ KPI₂₇…₃₀ + 10 × (два лучших KPI среди 27…30).</p>
<p>Бонус рассчитывается отдельно для каждого метода. Это два лучших из четырёх дорогих результатов, а не удвоенный средний KPI по архиву. Веса сверены по третьей странице условия; правило бонуса — из приведённого пользователем уточнения организатора.</p></section>
<section><h2>Равномерный сценарий: 2 526 архивных тестов без Open15</h2><div class="scroll"><table><tr><th>Составляющая</th><th>Online Cangjie</th><th>Гибрид Cangjie</th></tr>__COMPONENTS__</table></div><p>Из архива равномерно выбираются 15 разных тестов. Первым 11 назначается вес 4, последним четырём — вес 10. Только Open15 измерен на реальных конкурсных входах; закрытые компоненты — точные математические ожидания в этом искусственном сценарии.</p></section>
<section><h2>Зависимость вывода от состава закрытых тестов</h2><div class="scroll"><table><tr><th>Сценарий</th><th>Размеры пулов 4 / 10</th><th>Online: E[S]</th><th>Гибрид: E[S]</th><th>Δ гибрид − online</th><th>Δ бонуса</th><th>Гибрид выше в моделировании</th></tr>__ROWS__</table></div>
<p>Ожидания рассчитаны точно для выборки без возвращения. Последний столбец — 100 000 парных случайных наборов в каждом сценарии; методы получают одни и те же входы. Это частота внутри модели, а не вероятность победы в соревновании.</p></section>
<section><h2>Границы вывода</h2><p>Архив содержит знакомые генераторы, коррелирующие примеры и направленные ловушки. Он отобран по объёмной верхней оценке U ≥ 0,85. Ни частоты механизмов, ни соответствие размеров теста его конкурсному весу для закрытой части не известны.</p>
<p>Существующий гибрид содержит старое online-ядро trial22. Гибрид с нынешним online-ядром — другой, пока не измеренный кандидат. Для будущего порта нужны проверка совпадения ответов и нативные измерения Windows/G5420; его память и CPU нельзя приравнивать к C++.</p>
<p><a href="comparison.json">Полные числа, исходные хеши, состав сценариев и квантили</a> · <a href="../pipes_all2537_comparison_20261020/report.html">Первичный прогон 2 537 тестов</a> · <a href="../../data/pipes/statement.pdf">Условие</a></p></section></main></html>"""
    (HERE / "report.html").write_text(page.replace("__COMPONENTS__", "".join(components)).replace("__ROWS__", "".join(rows)))
    print("DONE", flush=True)


if __name__ == "__main__":
    main()
