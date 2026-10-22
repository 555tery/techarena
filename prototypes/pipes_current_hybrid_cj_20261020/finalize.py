#!/usr/bin/env python3
"""Check completed arithmetic, source preservation and deliverable links."""
import hashlib
import json
import math
import shutil
import subprocess
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import unquote, urlsplit

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
sha = lambda p: hashlib.sha256(Path(p).read_bytes()).hexdigest()

class Links(HTMLParser):
    def __init__(self):
        super().__init__()
        self.links = []
        self.scripts = []
        self.capture = False
    def handle_starttag(self, tag, attrs):
        a = dict(attrs)
        if tag == "a" and "href" in a:
            self.links.append(a["href"])
        if tag == "script":
            self.capture = a.get("type") != "application/json"
    def handle_endtag(self, tag):
        if tag == "script":
            self.capture = False
    def handle_data(self, text):
        if self.capture:
            self.scripts.append(text)

def main():
    d = json.loads((HERE / "analysis.json").read_text())
    f = json.loads((HERE / "freeze.json").read_text())
    r = [json.loads(x) for x in (HERE / "records.jsonl").read_text().splitlines()]
    idx = {(x["id"], x["method"]): x for x in r}
    freeze_sha = sha(HERE / "freeze.json")
    assert d["complete"] and len(idx) == len(r) == 7911
    assert d["hybrid_cpp_cj_parity"]["identical"] == 2637
    assert not d["hybrid_cpp_cj_parity"]["mismatches"]
    assert d["unchanged_online_baseline"]["identical"] == 2541
    assert not d["unchanged_online_baseline"]["mismatch_ids"]
    assert d["hash_verification"]["verified_response_files"] == 7911
    assert d["hash_verification"]["records_snapshot_sha256"] == sha(HERE / "records.jsonl")
    independent = json.loads((HERE / "cpp/independent_final_audit.json").read_text())
    assert independent["status"] == "pass"
    for name in ("freeze.json", "records.jsonl", "analysis.json"):
        assert independent["verified_input_sha256"][name] == sha(HERE / name)
    assert all(x["workers"] == 1 and x["freeze_sha256"] == freeze_sha for x in r)
    sums = {}
    for group, cases in [
        ("archive2537", [c for c in f["cases"] if c["selected"]]),
        ("fresh96", [c for c in f["cases"] if c["cohort"] == "fresh"]),
    ]:
        group_sums = {}
        for method in f["methods"]:
            m = method["id"]
            rows = [idx[c["id"], m] for c in cases]
            values = []
            for c, row in zip(cases, rows):
                valid = row["status"] == "ok"
                limits = valid and row["solver_cpu_total_s"] is not None and row["solver_cpu_total_s"] < 5
                limits = limits and row["solver_peak_rss_mb"] is not None and row["solver_peak_rss_mb"] < 256
                assert bool(limits) == row["within_limits"]
                value = c["meta"]["final_occupied_length_m"] / row["trench_length_m"] if limits else 0.
                assert math.isclose(value, row["contest_adjusted_kpi"], abs_tol=1e-15)
                values.append(value)
            mean = math.fsum(values) / len(values)
            assert abs(mean - d["summaries"][group]["methods"][m]["contest_adjusted_kpi"]["mean"]) < 1e-13
            group_sums[m] = mean
        sums[group] = group_sums
    originals = {}
    for m in f["methods"]:
        originals[m["id"]] = sha(ROOT / m["original_source"]) == m["source_sha256"]
        assert originals[m["id"]]
    preserved_sources = {
        "prototypes/pipes_online_patterns_20261020/release/solution.cpp": "f7b285eee9d59f443b015de581c4622668dd1a321e0cb9ef00d4baf10412f5db",
        "prototypes/pipes_cangjie_port_20261020/release/solution.cj": "cc2fcdf7d930bad6c75a0656c105c28399c66d5184c937740c69764a1e9e681f",
        "prototypes/pipes_closed_ready_20261020/release/solution.cpp": "48a44fb0ccad7e6560055245a3096f892c23b5a98c4ab77468c87968e23054c1",
    }
    assert all(sha(ROOT / p) == h for p, h in preserved_sources.items())
    links = Links()
    links.feed((HERE / "report.html").read_text())
    missing = []
    for link in links.links:
        url = urlsplit(link)
        if not url.scheme and url.path and url.path != "final_audit.json" and not (HERE / unquote(url.path)).exists():
            missing.append(link)
    assert not missing, missing
    (HERE / "report-script.js").write_text("\n".join(links.scripts))
    node = shutil.which("node") or str(Path.home() / ".local/bin/node")
    subprocess.run([node, "--check", str(HERE / "report-script.js")], check=True)
    audit = dict(
        complete=True, runs=7911, cases=2637, workers=1, transcript_parity=2637,
        unchanged_online_baseline=2541, means_independently_recomputed=sums,
        source_files_preserved=originals, historical_releases_preserved=preserved_sources,
        html_parsed=True, static_local_links_exist=True, visual_browser_check=False,
        report_javascript_syntax_checked=True, independent_arithmetic_audit="pass",
        windows_native_executed=False,
        artifact_sha256={name: sha(HERE / name) for name in (
            "freeze.json", "protocol.json", "records.jsonl", "analysis.json", "report.html", "REPORT.txt",
            "run.py", "prepare.py", "analyze.py", "make_report.py", "package_cj.py",
            "cj_source_manifest.json", "release/solution.cj", "cpp/solution.cpp",
            "cpp/review.json", "cpp/analysis_review.json", "fresh/manifest.json",
            "windows_compare.py", "package_windows.py", "build_windows.bat",
            "current-hybrid-cangjie-windows.zip", "windows-package/package_sha256.json",
            "counterexample.json", "explain_counterexample.py", "measurement_host.json",
            "cpp/final_static_review.json", "cpp/independent_final_audit.json", "finalize.py",
            "platform/result.json", "platform/result-1667192.png"
        )})
    audit["contest_submission"] = {
        "id": 1667192, "compiler": "Cangjie 1.0.5", "accepted": 12,
        "time_limit_tests": [9, 14, 15], "score": 15.85787,
        "precise_server_cpu_and_memory_available": False,
    }
    (HERE / "final_audit.json").write_text(json.dumps(audit, indent=2) + "\n")
    print(json.dumps(dict(complete=True, runs=7911, parity=2637, source_preservation=True)))

if __name__ == "__main__":
    main()
