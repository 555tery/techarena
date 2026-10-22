"""Render descriptive figures from saved statistics only, no raw input access."""

import json
import os
from pathlib import Path

OUT = Path(__file__).resolve().parent
os.environ["MPLCONFIGDIR"] = str(OUT / ".matplotlib-cache")
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np


def main():
    report = json.loads((OUT / "report.json").read_text())
    groups = {name: [c for c in report["cases"] if c["group"] == name] for name in ("main", "stress", "open15")}
    plt.rcParams.update({"font.size": 10, "axes.grid": True, "grid.alpha": .18,
                         "axes.spines.top": False, "axes.spines.right": False})
    fig, axes = plt.subplots(2, 2, figsize=(13, 9.5), constrained_layout=True)
    panels = [("delete_fraction", "final_to_bound", "Deletion fraction", "Final volume / rounded peak", "End load and churn"),
              ("operations", "peak_live_count", "Operations (log)", "Peak live pipe count (log)", "Workload scale"),
              ("mean_insert_length", "share_length_le2", "Mean inserted length", "Fraction of insertions of length 1 or 2", "Very short allocations"),
              ("deletion_age_rank_mean", "completed_lifetime_p90_over_n", "Mean deletion age rank (0=oldest, 1=newest)",
               "Completed lifetime p90 / trace length", "Deletion order and observed lifetimes")]
    colors = {"main": "#64748b", "stress": "#38a4a0", "open15": "#c2410c"}
    offsets = [
        {"2": (-12, 7), "7": (-8, -14), "8": (-15, 7), "11": (6, -13), "12": (5, 9), "13": (5, -13), "15": (-8, 10)},
        {"2": (-10, -15), "3": (-8, -15), "4": (5, 6), "6": (5, 5)},
        {"8": (6, 7), "13": (-15, 7), "11": (-14, -13), "15": (5, 7)},
        {"5": (-17, 7), "8": (3, 27), "13": (-28, 10), "14": (8, 4), "15": (-20, 10)},
    ]
    for panel_index, (ax, (x, y, xlabel, ylabel, title)) in enumerate(zip(axes.flat, panels)):
        for group, rows in groups.items():
            usable = [c for c in rows if c["features"][x] is not None and c["features"][y] is not None]
            ax.scatter([c["features"][x] for c in usable], [c["features"][y] for c in usable],
                       s=[25 + 7 * c["features"]["weight"] if group == "open15" else 16 for c in usable],
                       color=colors[group], alpha=.85 if group == "open15" else .38,
                       marker="D" if group == "open15" else "o", label={"main": "SEARCH-v3 main (128)", "stress": "Separate stress (32)", "open15": "Open15 (size reflects weight)"}[group])
            if group == "open15":
                for c in usable:
                    shift = offsets[panel_index].get(c["id"], (4, 4))
                    ax.annotate(c["id"], (c["features"][x], c["features"][y]), xytext=shift,
                                textcoords="offset points", color=colors[group], fontsize=8,
                                arrowprops={"arrowstyle": "-", "lw": .35, "color": colors[group]} if shift != (4, 4) else None)
        ax.set(xlabel=xlabel, ylabel=ylabel, title=title)
    axes[0, 1].set_xscale("log")
    axes[0, 1].set_yscale("log")
    axes[0, 0].legend(loc="lower right", fontsize=8)
    fig.suptitle("Input characteristics only: SEARCH-v3 and Open15", fontsize=16)
    fig.savefig(OUT / "coverage.png", dpi=160)
    plt.close(fig)

    curves = np.array([c["load_curve"] for c in groups["main"]])
    x = np.linspace(0, 1, 101)
    lo, median, hi = np.quantile(curves, [.1, .5, .9], axis=0)
    fig, axes = plt.subplots(5, 3, figsize=(13, 13), sharex=True, sharey=True, constrained_layout=True)
    for ax, c in zip(axes.flat, groups["open15"]):
        f = c["features"]
        ax.fill_between(x, lo, hi, color="#cbd5e1", alpha=.65)
        ax.plot(x, median, "--", color="#64748b", linewidth=.9)
        ax.step(x, c["load_curve"], where="post", color="#c2410c", linewidth=1.6)
        ax.set_title(f"Open {c['id']} | weight {f['weight']:g} | n={f['operations']:,}", fontsize=10)
        ax.text(.03, .07, f"F/B={f['final_to_bound']:.3f}", transform=ax.transAxes, fontsize=9)
        ax.set_ylim(0, 1.05)
    fig.suptitle("Open15 normalized load histories\nGray: SEARCH-v3 main p10–p90 and median; orange: individual Open trace", fontsize=14)
    fig.supxlabel("Fraction of operation stream")
    fig.supylabel("Live volume / own historical peak")
    fig.savefig(OUT / "load-curves.png", dpi=150)
    plt.close(fig)

    histograms = np.array([c["size_histogram"] for c in groups["main"]])
    sizes = np.arange(1, 41)
    fig, axes = plt.subplots(2, 2, figsize=(12, 7), sharex=True, constrained_layout=True)
    for ax, case_id in zip(axes.flat, ("12", "13", "14", "15")):
        c = next(c for c in groups["open15"] if c["id"] == case_id)
        ax.fill_between(sizes, histograms.min(axis=0), histograms.max(axis=0), color="#cbd5e1", alpha=.6,
                        label="Main min–max per size")
        ax.bar(sizes, c["size_histogram"], width=.8, color="#c2410c", alpha=.85, label=f"Open {case_id}")
        ax.set_title(f"Open {case_id}, weight={c['features']['weight']:g}")
        ax.set(xlabel="Inserted length", ylabel="Fraction of insertions")
    axes[0, 0].legend(fontsize=8)
    fig.suptitle("Size distributions of the four largest-weight Open cases", fontsize=14)
    fig.savefig(OUT / "size-profiles.png", dpi=160)
    plt.close(fig)


if __name__ == "__main__":
    main()
