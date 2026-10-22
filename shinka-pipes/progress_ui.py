"""Serve the existing Shinka WebUI on loopback for the current run only."""

import json
from pathlib import Path
import socketserver
import sqlite3
from urllib.parse import parse_qs, urlparse

from shinka.webui import visualization

ROOT = Path(__file__).resolve().parent
ACTIVE = json.loads((ROOT / "active-run.json").read_text())
RUN = Path(ACTIVE["run_dir"]).resolve()
DATABASE = RUN / "programs.sqlite"


class Handler(visualization.DatabaseRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, search_root=str(RUN),
                         directory=str(Path(visualization.__file__).parent), **kwargs)

    def _load_failed_proposal_nodes(self, abs_db_path, *, include_code=False, generation=None):
        nodes = super()._load_failed_proposal_nodes(
            abs_db_path, include_code=include_code, generation=generation
        )
        # After repair, failed attempts can also be persisted Program rows for
        # budget accounting. Keep their attempt_log history without drawing twice.
        with sqlite3.connect(f"file:{abs_db_path}?mode=ro", uri=True) as connection:
            persisted = {row[0] for row in connection.execute("SELECT DISTINCT generation FROM programs")}
        return [node for node in nodes if node["generation"] not in persisted]

    def do_GET(self):
        query = parse_qs(urlparse(self.path).query)
        if "db_path" in query and Path(query["db_path"][0]).resolve() != DATABASE:
            self.send_error(403, "This viewer serves the active run only")
            return
        super().do_GET()


class Server(socketserver.ThreadingTCPServer):
    allow_reuse_address = True
    daemon_threads = True


if __name__ == "__main__":
    with Server(("127.0.0.1", 8888), Handler) as server:
        print(f"Shinka progress: http://127.0.0.1:8888/viz_tree.html?db_path={DATABASE}", flush=True)
        server.serve_forever()
