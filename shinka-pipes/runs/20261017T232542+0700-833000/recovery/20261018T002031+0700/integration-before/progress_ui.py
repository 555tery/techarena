"""Serve the existing Shinka WebUI on loopback for the current run only."""

import json
from pathlib import Path
import socketserver
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
