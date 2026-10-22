from pathlib import Path
import sys
sys.path.insert(0, '/Users/555tery/techarena/shinka-pipes')
import progress_ui as viewer
viewer.RUN = Path('/Users/555tery/techarena/shinka-pipes/search-v2/runs/20261018T025030+0700-native')
viewer.DATABASE = viewer.RUN / "programs.sqlite"
with viewer.Server(("127.0.0.1", 8889), viewer.Handler) as server:
    server.serve_forever()
