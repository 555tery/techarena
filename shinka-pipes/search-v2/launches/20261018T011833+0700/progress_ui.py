"""View this SEARCH-v2 run using the existing loopback-only Shinka UI."""
from pathlib import Path
import sys
sys.path.insert(0, "/Users/555tery/techarena/shinka-pipes")
import progress_ui as viewer
viewer.RUN = Path("/Users/555tery/techarena/shinka-pipes/search-v2/runs/20261018T011836+0700-084000")
viewer.DATABASE = viewer.RUN / "programs.sqlite"
with viewer.Server(("127.0.0.1", 8889), viewer.Handler) as server:
    print("SEARCH-v2 progress UI listening on 127.0.0.1:8889", flush=True)
    server.serve_forever()
