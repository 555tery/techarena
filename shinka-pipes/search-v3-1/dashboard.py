"""Serve the standard Shinka viewer on loopback for this run namespace."""
import argparse
import os
from pathlib import Path
import socketserver

from support import ROOT


def main():
    from shinka.webui import visualization
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("run", type=Path)
    parser.add_argument("--port", type=int, default=8890)
    args = parser.parse_args()
    run = args.run.resolve()
    if run.parent != ROOT / "runs" or not (run / "run-manifest.json").is_file():
        raise ValueError("requires an authorized SEARCH-v3.1 run")
    os.chdir(Path(visualization.__file__).resolve().parent)
    class Server(socketserver.ThreadingTCPServer):
        allow_reuse_address = True
        daemon_threads = True
    with Server(("127.0.0.1", args.port), visualization.create_handler_factory(str(run))) as server:
        server.serve_forever()


if __name__ == "__main__":
    main()
