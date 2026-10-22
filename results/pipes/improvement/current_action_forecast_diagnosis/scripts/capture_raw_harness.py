#!/usr/bin/env python3
"""Run the unchanged local Pipes harness while teeing solver stdout bytes."""

from pathlib import Path
import sys

_repo_root = Path(__file__).resolve().parents[5]
sys.path.insert(0, str(_repo_root))

import tools.pipes_harness as harness


_current_case_dir = None
_original_run_case = harness.run_case
_original_start_line_reader = harness.start_line_reader


class TeeReader:
    def __init__(self, stream, output_path):
        self._stream = stream
        self._output = Path(output_path).open("wb", buffering=0)

    def readline(self, size=-1):
        try:
            data = self._stream.readline(size)
        except Exception:
            self._output.close()
            raise
        if data:
            self._output.write(data)
        else:
            self._output.close()
        return data


def _start_line_reader(stream, out_queue, label):
    if label == "solver" and _current_case_dir is not None:
        stream = TeeReader(stream, _current_case_dir / "solver_stdout.raw")
    return _original_start_line_reader(stream, out_queue, label)


def _run_case(solver_argv, interactor, test_path, case_dir,
              response_timeout, wall_timeout):
    global _current_case_dir
    _current_case_dir = Path(case_dir)
    try:
        return _original_run_case(solver_argv, interactor, test_path, case_dir,
                                  response_timeout, wall_timeout)
    finally:
        _current_case_dir = None


harness.start_line_reader = _start_line_reader
harness.run_case = _run_case

if __name__ == "__main__":
    sys.exit(harness.main())
