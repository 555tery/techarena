"""Run independent candidate replay through the tracked local runtime."""
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent.parent))
from runtime import ROOT, REPO, e

PY = REPO / "shinka-pipes" / ".venv" / "bin" / "python"
SCRIPT = HERE / "audit_pool_order.py"
before = set((ROOT / "processes").glob("*.json"))
rc = e.invoke([str(PY), "-B", str(SCRIPT)], HERE, "audit-pool-order.log", 30)
created = sorted(set((ROOT / "processes").glob("*.json")) - before,
                 key=lambda p: p.stat().st_mtime)
if rc != 0:
    raise SystemExit(f"independent audit failed, status={rc}")
report = HERE / "report.json"
record = json.loads(report.read_text())
record["audit_pid"] = json.loads(created[-1].read_text()).get("pid") if created else None
record["runtime_record"] = str(created[-1]) if created else None
report.write_text(json.dumps(record, indent=2) + "\n")
print(json.dumps({k: record[k] for k in ("status", "extent", "T", "pid1", "common_prefix", "positions_file_sha256", "audit_pid")}, indent=2))
