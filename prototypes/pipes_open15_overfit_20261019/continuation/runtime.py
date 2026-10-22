"""Continuation explicitly authorized by user; quota reserve withdrawn, no API purchases."""
from pathlib import Path
import sys
ROOT=Path(__file__).resolve().parent
PARENT=ROOT.parent
REPO=PARENT.parents[1]
sys.path.insert(0,str(REPO/'prototypes/pipes_options_v4_20261019'))
import evaluate as e
e.ROOT=ROOT
e.quota=lambda:e.gate(ROOT,min_remaining_percent=0,max_age_seconds=30)
