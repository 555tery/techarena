#!/usr/bin/env python3
"""Freeze train-selected tree #33 into a standalone, env-independent source."""

from __future__ import annotations

import re
from pathlib import Path

HERE = Path(__file__).resolve().parents[0].parent
SEARCH_SOURCE = HERE / "src/policy_search.cpp"
FROZEN_SOURCE = HERE / "src/tree_033_frozen.cpp"


def main():
    source = SEARCH_SOURCE.read_text()
    pattern = r"    static int synthesisPolicyId\(\) \{.*?\n    \}\n"
    source, count = re.subn(pattern, "    static int synthesisPolicyId() { return 33; }\n", source, count=1, flags=re.S)
    if count != 1:
        raise RuntimeError("could not freeze policy ID")
    FROZEN_SOURCE.write_text(source)
    print(FROZEN_SOURCE)


if __name__ == "__main__":
    main()
