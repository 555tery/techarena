#!/usr/bin/env python3
"""Verify the C++ historical-scenario sampler matches Python random.choice."""
from __future__ import annotations

import random
import subprocess
import tempfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
SOURCE = HERE / "src/policy_conditioned.cpp"
SEEDS = (0, 1, 0xFFFFFFFF, 617000181, 912300000)
COUNTS = (3, 16, 87, 128)
DRAWS = 20


def main() -> None:
    with tempfile.TemporaryDirectory(prefix="rng-check-", dir=HERE / "logs") as temp:
        temp_path = Path(temp)
        probe = temp_path / "probe.cpp"
        binary = temp_path / "probe"
        probe.write_text(
            '#define main pipes_solver_main\n'
            f'#include "{SOURCE}"\n'
            '#undef main\n'
            '#include <iostream>\n'
            'int main() {\n'
            '  const std::uint32_t seeds[] = {0U, 1U, 0xffffffffU, 617000181U, 912300000U};\n'
            '  const std::size_t counts[] = {3U, 16U, 87U, 128U};\n'
            '  for (const auto seed : seeds) {\n'
            '    for (const auto count : counts) {\n'
            '      PythonRandom rng; rng.seed(seed);\n'
            '      for (int draw = 0; draw < 20; ++draw) {\n'
            '        if (draw != 0) std::cout << \' \';\n'
            '        std::cout << rng.choiceIndex(count);\n'
            '      }\n'
            '      std::cout << \'\\n\';\n'
            '    }\n'
            '  }\n'
            '}\n',
            encoding="utf-8",
        )
        subprocess.run(
            ["g++", "-O2", "-std=c++20", "-Wall", "-Wextra", "-Wconversion",
             "-Wshadow", "-pedantic", "-Werror", str(probe), "-o", str(binary)],
            cwd=HERE,
            check=True,
        )
        observed = subprocess.run([str(binary)], check=True, capture_output=True, text=True).stdout.splitlines()

    expected = []
    for seed in SEEDS:
        for count in COUNTS:
            rng = random.Random(seed)
            expected.append(" ".join(str(rng.choice(range(count))) for _ in range(DRAWS)))
    if observed != expected:
        for index, (actual, target) in enumerate(zip(observed, expected)):
            if actual != target:
                raise SystemExit(f"Python RNG mismatch at stream {index}: {actual!r} != {target!r}")
        raise SystemExit(f"Python RNG line count mismatch: {len(observed)} != {len(expected)}")
    print(f"matched {len(SEEDS) * len(COUNTS) * DRAWS} Python random.choice draws")


if __name__ == "__main__":
    main()
