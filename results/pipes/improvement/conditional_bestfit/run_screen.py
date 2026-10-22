from pathlib import Path
import shlex
import subprocess
import sys

root = Path(__file__).resolve().parents[4]
out_root = Path(__file__).resolve().parent
solvers = {
    "seed": out_root / "bin/seed",
    "fragment_tight": out_root / "bin/fragment_tight",
    "small_demand": out_root / "bin/small_demand",
    "large_demand": out_root / "bin/large_demand",
}
commands = []
for solver_name, solver in solvers.items():
    for case in (5, 9, 15):
        output = out_root / "reports/screen" / f"{solver_name}-case{case}"
        command = [
            sys.executable,
            str(root / "tools/pipes_harness.py"),
            "--solver", str(solver),
            "--name", f"{solver_name}-case{case}",
            "--interactor", str(root / "tools/interactor"),
            "--tests", str(root / f"data/pipes/open/{case}.in"),
            "--out", str(output),
            "--cpu-limit", "5",
            "--memory-limit-mb", "256",
            "--wall-timeout", "120",
        ]
        commands.append(shlex.join(command))
        result = subprocess.run(command, cwd=root, text=True, capture_output=True)
        (output / "console.log").write_text(result.stdout + result.stderr, encoding="utf-8")
        print(f"{solver_name} case {case}: rc={result.returncode} report={output}")
        if result.returncode != 0:
            print(result.stdout[-2000:])
            print(result.stderr[-2000:], file=sys.stderr)
            raise SystemExit(result.returncode)
(out_root / "screen_commands.txt").write_text("\n".join(commands) + "\n", encoding="utf-8")
