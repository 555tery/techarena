#!/usr/bin/env python3
"""Small stdlib-only wrapper matching the official runner's pipe wiring."""
import argparse
import subprocess
from pathlib import Path


def run_case(solver, interactor, test, work):
    work.mkdir(parents=True, exist_ok=True)
    score = work / "score.txt"
    answer = work / "answer.txt"
    report = work / "report.txt"
    answer.write_text("")  # testlib requires the optional answer file to exist
    for p in (score, report):
        p.unlink(missing_ok=True)
    with subprocess.Popen([str(interactor), str(test), "score.txt", "answer.txt", "report.txt"],
                          stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                          cwd=work) as judge:
        with subprocess.Popen(solver, stdin=judge.stdout, stdout=judge.stdin,
                              stderr=subprocess.PIPE) as participant:
            participant.stderr.close()
            judge.stdin.close()
            participant.wait(timeout=20)
        judge.stdout.close()
        judge.wait(timeout=20)
        err = judge.stderr.read().decode("utf-8", "replace")
    value = score.read_text().strip() if score.exists() else "missing"
    rep = report.read_text().strip() if report.exists() else ""
    return value, err, rep


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--solver", nargs="+", required=True)
    p.add_argument("--tests", required=True)
    p.add_argument("--out", required=True)
    p.add_argument("--interactor", default="tools/interactor")
    a = p.parse_args()
    tests = sorted(Path(a.tests).glob("*.in")) if Path(a.tests).is_dir() else [Path(a.tests)]
    total = 0.0
    for test in tests:
        value, err, rep = run_case(a.solver, Path(a.interactor).resolve(), test.resolve(), Path(a.out) / test.stem)
        try: total += float(value)
        except ValueError: pass
        print(f"{test.name} score={value} interactor={err.strip()} report={rep}")
    print(f"weighted_score_sum={total:.12g}")


if __name__ == "__main__":
    main()
