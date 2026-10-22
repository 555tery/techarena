"""Derive descriptive comparisons from report.json; no raw inputs or solutions."""

import json
from pathlib import Path

OUT = Path(__file__).resolve().parent


def main():
    report = json.loads((OUT / "report.json").read_text())
    groups = {g: [c for c in report["cases"] if c["group"] == g] for g in ("main", "stress", "open15")}
    predicates = {
        "high_final": ("F/B >= .95", lambda f: f["final_to_bound"] >= .95),
        "intermediate_final": (".30 <= F/B < .95", lambda f: .30 <= f["final_to_bound"] < .95),
        "short_trace": ("operations < 2000", lambda f: f["operations"] < 2000),
        "rare_deletion": ("delete_fraction < .05", lambda f: f["delete_fraction"] < .05),
        "tiny_dominance": ("share(length<=2) >= .80", lambda f: f["share_length_le2"] >= .8),
        "soft_recency": ("mean active deletion rank >= .90 AND exact-newest deletion fraction < .30",
                         lambda f: f["deletion_age_rank_mean"] is not None and f["deletion_age_rank_mean"] >= .9
                         and f["lifo_deletion_fraction"] < .3),
        "soft_recency_with_positive_serial_sizes": (
            "soft_recency AND insertion-size lag1 Pearson > .10",
            lambda f: f["deletion_age_rank_mean"] is not None and f["deletion_age_rank_mean"] >= .9
            and f["lifo_deletion_fraction"] < .3 and f["size_lag1_correlation"] is not None and f["size_lag1_correlation"] > .1),
        "isolated_deletions": ("deletions>0 AND max delete run == 1", lambda f: f["deletions"] > 0 and f["delete_run_max"] == 1),
    }
    findings = {"scope": "post-hoc descriptive workload predicates, not independent statistical tests or future fitness weights",
                "predicates": {}, "weighted_feature_means": {}}
    for name, (definition, pred) in predicates.items():
        item = {"definition": definition}
        for group, cases in groups.items():
            matched = [c for c in cases if pred(c["features"])]
            total = sum(c["features"]["weight"] for c in cases)
            item[group] = {"count": len(matched), "ids": [c["id"] for c in matched],
                           "weight_share": sum(c["features"]["weight"] for c in matched) / total}
        findings["predicates"][name] = item
    keys = ("final_to_bound", "mean_load_over_peak", "time_above_90pct_peak", "mean_insert_length",
            "share_length_le2", "old_survivor_volume_over_final", "deletion_age_rank_mean", "size_lag1_correlation")
    for key in keys:
        findings["weighted_feature_means"][key] = {g: report["summaries"][g]["weighted_mean"][key] for g in groups}
    (OUT / "findings.json").write_text(json.dumps(findings, indent=2, allow_nan=False) + "\n")
    lines = ["# Таблицы характеристик входов", "", "Только входные команды; решения не запускались.", "",
             "## Open15 по случаям", "",
             "| Open | Вес | Операции | F/B | Удаления | Пик live | Средний размер | Размеры ≤2 | Ранг удаления |",
             "|---:|---:|---:|---:|---:|---:|---:|---:|---:|"]
    for c in groups["open15"]:
        f = c["features"]
        lines.append(f"| {c['id']} | {f['weight']:g} | {f['operations']} | {f['final_to_bound']:.4f} | "
                     f"{f['delete_fraction']:.2%} | {f['peak_live_count']} | {f['mean_insert_length']:.3f} | "
                     f"{f['share_length_le2']:.2%} | {f['deletion_age_rank_mean']:.4f} |")
    lines += ["", "Ранг: 0 — самый старый живой PID, 1 — самый новый; усреднение по удалениям.", "",
              "## Наличие режимов", "",
              "Пороги заданы после просмотра данных и служат описанию, не тесту гипотезы.", "",
              "| Режим | Main /128 | Stress /32 | Open /15 | Доля веса Open |", "|---|---:|---:|---:|---:|"]
    for name, item in findings["predicates"].items():
        lines.append(f"| `{name}` | {item['main']['count']} | {item['stress']['count']} | {item['open15']['count']} | "
                     f"{item['open15']['weight_share']:.2%} |")
    lines += ["", "Точные определения и ID — в [findings.json](findings.json).", "",
              "## Средние с весами", "", "Main/stress: равный вес каждого потока; Open15: официальный вес теста.", "",
              "| Характеристика | Main | Stress | Open15 |", "|---|---:|---:|---:|"]
    for key, values in findings["weighted_feature_means"].items():
        lines.append(f"| `{key}` | {values['main']:.5f} | {values['stress']:.5f} | {values['open15']:.5f} |")
    lines += ["", "Это распределения выбранных наборов; веса закрытых механизмов из них не следуют.", "",
              "## Близость гистограмм размеров", "",
              "TV=0 означает одинаковые доли размеров, TV=1 — непересекающиеся распределения.",
              "Сходство гистограммы не устанавливает сходство порядка команд или фрагментации.", "",
              "| Open | Ближайший main по TV | Семейство | TV |", "|---:|---|---|---:|"]
    for row in report["open15_vs_main"]:
        near = row["nearest_main_by_size_histogram"]
        lines.append(f"| {row['id']} | `{near['id']}` | {near['family']} | {near['total_variation']:.4f} |")
    (OUT / "TABLES.md").write_text("\n".join(lines) + "\n")


if __name__ == "__main__":
    main()
