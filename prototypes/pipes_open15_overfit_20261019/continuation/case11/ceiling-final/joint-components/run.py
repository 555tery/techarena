from pathlib import Path
import sys
CONTINUATION = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(CONTINUATION))
from runtime import ROOT, e
script = ROOT/'case11'/'ceiling-final'/'joint-components'/'search.py'
raise SystemExit(e.invoke([sys.executable, '-B', str(script)], script.parent, 'search.log', 600))
