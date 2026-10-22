from pathlib import Path
import shlex
import subprocess
import sys

root = Path(__file__).resolve().parents[4]
out_root = Path(__file__).resolve().parent
solvers = {
    "seed": out_root / "bin/seed",
    "horizon32": out_root / "bin/horizon32",
}
datasets = {
    "open-15": root / "data/pipes/open",
    "holdout-v2": root / "data/pipes/synthetic/final-holdout-v2",
    "development": root / "data/pipes/synthetic/development",
}
commands = []
for dataset_name, tests in datasets.items():
    for solver_name, solver in solvers.items():
        output = out_root / "reports" / dataset_name / solver_name
        command = [
            sys.executable,
            str(root / "tools/pipes_harness.py"),
            "--solver", str(solver),
            "--name", f"{solver_name}-{dataset_name}",
            "--interactor", str(root / "tools/interactor"),
            "--tests", str(tests),
            "--out", str(output),
            "--cpu-limit", "5",
            "--memory-limit-mb", "256",
            "--wall-timeout", "120",
        ]
        commands.append(shlex.join(command))
        result = subprocess.run(command, cwd=root, text=True, capture_output=True)
        output.mkdir(parents=True, exist_ok=True)
        (output / "console.log").write_text(result.stdout + result.stderr, encoding="utf-8")
        print(f"{dataset_name} {solver_name}: rc={result.returncode} report={output}")
        if result.returncode != 0:
            print(result.stdout[-2000:])
            print(result.stderr[-2000:], file=sys.stderr)
            raise SystemExit(result.returncode)
(out_root / "extended_commands.txt").write_text("\n".join(commands) + "\n", encoding="utf-8")
