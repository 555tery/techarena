"""Run tail-pool witness search through the authorized tracked runtime."""
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent.parent))
from runtime import ROOT, REPO, e

PY = REPO / "shinka-pipes" / ".venv" / "bin" / "python"
SEARCH = HERE / "tail_pool_search.py"
before = set((ROOT / "processes").glob("*.json"))
rc = e.invoke([str(PY), "-B", str(SEARCH)], HERE, "tail-pool-search.log", 100)
created = sorted(set((ROOT / "processes").glob("*.json")) - before,
                 key=lambda p: p.stat().st_mtime)
pid = None
if created:
    proc = json.loads(created[-1].read_text())
    pid = proc.get("pid")
report = HERE / "report.json"
if report.exists():
    record = json.loads(report.read_text())
    record["search_pid"] = pid
    record["search_runtime_record"] = str(created[-1]) if created else None
    report.write_text(json.dumps(record, indent=2) + "\n")
print(json.dumps({"returncode": rc, "pid": pid,
                  "report_exists": report.exists(),
                  "positions_exists": (HERE / "positions.txt").exists()}))
