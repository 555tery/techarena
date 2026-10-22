"""Generate valid synthetic Pipes command streams with baseline-derived pairs."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import subprocess

from model import joint_probability
from pipes_common import (
    FROZEN_BINARY_SHA256,
    FROZEN_SOURCE_SHA256,
    GROUPED_LOG_OR,
    HORIZON,
    PROTOCOL_VERSION,
    Pipe,
    adjacent_disjoint_pairs,
    synthetic_hazard,
    uniform_draw,
)

INITIAL_LENGTHS = [
    4, 4, 4, 7, 7, 7, 10, 10, 10, 13, 13, 13, 16, 16, 16, 19,
    19, 19, 22, 22, 22, 25, 25, 25, 28, 28, 28, 31, 31, 31, 34, 34,
]
EVAL_MODE_INDEX = {"independent": 0, "grouped": 1, "phase": 2}
EVAL_SEED_BASE = 202610170000
EVAL_REPLICATES = 24
EVAL_EPOCHS = 156
SYNTHETIC_APPROVAL_TOKEN = "synthetic-eval-reviewed-v3"
EVAL_DIR_NAME = "eval"


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for block in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


class OnlineSolver:
    def __init__(self, source: Path, binary: Path):
        if sha256_file(source) != FROZEN_SOURCE_SHA256:
            raise RuntimeError("frozen-final source hash mismatch")
        if sha256_file(binary) != FROZEN_BINARY_SHA256:
            raise RuntimeError("frozen-final binary hash mismatch")
        self.proc = subprocess.Popen(
            [str(binary)],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            bufsize=1,
        )
        self.responses: list[str] = []
        self.active: dict[int, Pipe] = {}
        self.length_occurrences = [0] * 41
        self.next_pid = 1
        self.command_count = 0
        self.trench_length = 0

    def command(self, value: int) -> tuple[int, ...]:
        if value == 0:
            raise ValueError("zero is reserved for solver termination")
        assert self.proc.stdin is not None and self.proc.stdout is not None
        self.proc.stdin.write(f"{value}\n")
        self.proc.stdin.flush()
        line = self.proc.stdout.readline()
        if line == "":
            stderr = self.proc.stderr.read() if self.proc.stderr is not None else ""
            raise RuntimeError(f"solver ended before replying: {stderr}")
        fields = tuple(int(token) for token in line.split())
        self.command_count += 1
        if value > 0:
            if len(fields) != 2:
                raise RuntimeError(f"placement reply must have two integers: {line!r}")
            digs, start = fields
            if digs < 0 or start < 0:
                raise RuntimeError("negative placement coordinate or dig count")
            self.trench_length += 20 * digs
            pid = self.next_pid
            self.next_pid += 1
            parity = self.length_occurrences[value] % 2
            self.length_occurrences[value] += 1
            pipe = Pipe(pid, value, start, self.command_count, parity)
            self._check_no_overlap(pipe)
            self.active[pid] = pipe
        else:
            if len(fields) != 1:
                raise RuntimeError(f"removal reply must have one integer: {line!r}")
            pid = -value
            pipe = self.active.pop(pid, None)
            if pipe is None or fields[0] != pipe.start:
                raise RuntimeError(f"invalid removal output for PID {pid}: {line!r}")
        self.responses.append(line.rstrip("\n"))
        return fields

    def _check_no_overlap(self, candidate: Pipe) -> None:
        left = candidate.start
        right = candidate.start + candidate.length
        for pipe in self.active.values():
            other_left = pipe.start
            other_right = pipe.start + pipe.length
            if max(left, other_left) < min(right, other_right):
                raise RuntimeError(f"overlapping placement for PID {candidate.pid}")

    def finish(self) -> str:
        assert self.proc.stdin is not None
        self.proc.stdin.write("0\n")
        self.proc.stdin.flush()
        self.proc.stdin.close()
        extra = self.proc.stdout.read() if self.proc.stdout is not None else ""
        return_code = self.proc.wait(timeout=30)
        stderr = self.proc.stderr.read() if self.proc.stderr is not None else ""
        if return_code != 0:
            raise RuntimeError(f"frozen-final returned {return_code}: {stderr}")
        if extra.strip():
            raise RuntimeError(f"solver printed after termination: {extra!r}")
        return stderr


def _add_pipe(solver: OnlineSolver, commands: list[int], length: int) -> Pipe:
    solver.command(length)
    commands.append(length)
    return solver.active[solver.next_pid - 1]


def _remove_pipe(solver: OnlineSolver, commands: list[int], pid: int) -> None:
    solver.command(-pid)
    commands.append(-pid)


def _filler_cycle(solver: OnlineSolver, commands: list[int]) -> None:
    filler = _add_pipe(solver, commands, 1)
    _remove_pipe(solver, commands, filler.pid)


def _mode_is_grouped(mode: str, epoch: int, epoch_count: int) -> bool:
    if mode == "grouped":
        return True
    if mode == "independent":
        return False
    if mode == "phase":
        return epoch >= epoch_count // 2
    raise ValueError(f"unknown mode: {mode}")


def _sample_finite_or_pair(
    seed: int,
    epoch: int,
    left_pid: int,
    right_pid: int,
    p_left: float,
    p_right: float,
) -> tuple[bool, bool]:
    """Sample a bivariate Bernoulli pair with exact marginals and finite log OR."""
    p_both = joint_probability(p_left, p_right, GROUPED_LOG_OR)
    u_left = uniform_draw(seed, epoch, left_pid)
    u_right = uniform_draw(seed, epoch, right_pid)
    left_event = u_left < p_left
    if left_event:
        p_right_conditional = p_both / p_left
    else:
        p_right_conditional = (p_right - p_both) / (1.0 - p_left)
    right_event = u_right < p_right_conditional
    return left_event, right_event


def _expected_eval_names(mode: str) -> set[str]:
    names = {"manifest.json"}
    for replicate in range(EVAL_REPLICATES):
        stem = f"{mode}-{replicate:02d}"
        names.update(
            {
                f"{stem}.in",
                f"{stem}.judge_output.txt",
                f"{stem}.metadata.json",
            }
        )
    return names


def _write_eval_manifest(
    mode: str,
    output_dir: Path,
    stream_metadata: list[dict[str, object]],
) -> None:
    expected_names = _expected_eval_names(mode)
    actual_names = {path.name for path in output_dir.iterdir()}
    if actual_names != expected_names - {"manifest.json"}:
        raise RuntimeError(
            f"synthetic eval directory has unexpected files: "
            f"missing={sorted(expected_names - actual_names)}, "
            f"extra={sorted(actual_names - expected_names)}"
        )
    entries = []
    for replicate, metadata in enumerate(stream_metadata):
        stem = f"{mode}-{replicate:02d}"
        input_name = f"{stem}.in"
        reply_name = f"{stem}.judge_output.txt"
        metadata_name = f"{stem}.metadata.json"
        entries.append(
            {
                "name": stem,
                "seed": _seed_for_eval(mode, replicate),
                "input_file": input_name,
                "input_sha256": metadata["input_sha256"],
                "reply_file": reply_name,
                "reply_sha256": metadata["reply_sha256"],
                "metadata_file": metadata_name,
                "metadata_sha256": sha256_file(output_dir / metadata_name),
            }
        )
    source_manifest = Path(__file__).resolve().parent / "SOURCE_SHA256SUMS"
    manifest = {
        "protocol_version": PROTOCOL_VERSION,
        "mode": mode,
        "replicate_count": EVAL_REPLICATES,
        "epoch_count": EVAL_EPOCHS,
        "grouped_log_odds_ratio": GROUPED_LOG_OR,
        "source_sha256s_sha256": sha256_file(source_manifest),
        "expected_names": sorted(expected_names),
        "entries": entries,
    }
    (output_dir / "manifest.json").write_text(
        json.dumps(manifest, indent=2) + "\n", encoding="utf-8"
    )


def generate_stream(
    *,
    mode: str,
    seed: int,
    epoch_count: int,
    source: Path,
    binary: Path,
    output_dir: Path,
    stem: str,
) -> dict[str, object]:
    if epoch_count <= 0:
        raise ValueError("epoch_count must be positive")
    output_dir.mkdir(parents=True, exist_ok=True)
    solver = OnlineSolver(source, binary)
    commands: list[int] = []
    target_pids: set[int] = set()
    pair_counts: list[int] = []
    same_size_pair_counts: list[int] = []

    for length in INITIAL_LENGTHS:
        pipe = _add_pipe(solver, commands, length)
        target_pids.add(pipe.pid)
    while solver.command_count < HORIZON:
        _filler_cycle(solver, commands)
    if solver.command_count != HORIZON or len(target_pids) != 32:
        raise RuntimeError("initial setup did not land on the preregistered boundary")

    for epoch in range(epoch_count):
        if set(solver.active) != target_pids:
            raise RuntimeError("unexpected active PID set at epoch boundary")
        snapshot_pairs = adjacent_disjoint_pairs(solver.active.values())
        pair_counts.append(len(snapshot_pairs))
        same_size_pair_counts.append(sum(pair.relation for pair in snapshot_pairs))
        grouped = _mode_is_grouped(mode, epoch, epoch_count)
        events: dict[int, bool] = {}
        if grouped:
            for pair in snapshot_pairs:
                if pair.relation != 1:
                    continue
                left = pair.left
                right = pair.right
                p_left = synthetic_hazard(
                    left.length, solver.command_count - left.placed_at
                )
                p_right = synthetic_hazard(
                    right.length, solver.command_count - right.placed_at
                )
                y_left, y_right = _sample_finite_or_pair(
                    seed, epoch, left.pid, right.pid, p_left, p_right
                )
                events[left.pid] = y_left
                events[right.pid] = y_right

        for pid in sorted(target_pids):
            if pid in events:
                continue
            pipe = solver.active[pid]
            p = synthetic_hazard(pipe.length, solver.command_count - pipe.placed_at)
            events[pid] = uniform_draw(seed, epoch, pid) < p
        deletion_ids = [pid for pid, event in events.items() if event]

        for pid in sorted(target_pids):
            pipe = solver.active[pid]
            if pid in deletion_ids:
                _remove_pipe(solver, commands, pid)
                target_pids.remove(pid)
                replacement = _add_pipe(solver, commands, pipe.length)
                target_pids.add(replacement.pid)
                _filler_cycle(solver, commands)
            else:
                _filler_cycle(solver, commands)
                _filler_cycle(solver, commands)
        expected_boundary = HORIZON * (epoch + 2)
        if solver.command_count != expected_boundary:
            raise RuntimeError(
                f"epoch {epoch} ended at {solver.command_count}, expected {expected_boundary}"
            )
        if len(target_pids) != 32 or set(solver.active) != target_pids:
            raise RuntimeError("target active set changed size or retained a filler PID")

    stderr = solver.finish()
    if len(commands) != solver.command_count:
        raise RuntimeError("input command count and solver command count diverged")
    stream_path = output_dir / f"{stem}.in"
    reply_path = output_dir / f"{stem}.judge_output.txt"
    with stream_path.open("w", encoding="ascii") as output:
        output.write(f"1.0 {len(commands)}\n")
        output.writelines(f"{command}\n" for command in commands)
        output.write("0\n")
    with reply_path.open("w", encoding="ascii") as output:
        output.writelines(f"{response}\n" for response in solver.responses)
    metadata = {
        "mode": mode,
        "seed": seed,
        "epochs": epoch_count,
        "command_count": len(commands),
        "pair_counts_per_snapshot": pair_counts,
        "same_size_pair_counts_per_snapshot": same_size_pair_counts,
        "solver_stderr_empty": not bool(stderr),
        "source_sha256": sha256_file(source),
        "binary_sha256": sha256_file(binary),
        "input_path": str(stream_path),
        "reply_path": str(reply_path),
        "input_sha256": sha256_file(stream_path),
        "reply_sha256": sha256_file(reply_path),
    }
    metadata_path = output_dir / f"{stem}.metadata.json"
    metadata_path.write_text(json.dumps(metadata, indent=2) + "\n", encoding="utf-8")
    return metadata


def _seed_for_eval(mode: str, replicate: int) -> int:
    if mode not in EVAL_MODE_INDEX or not 0 <= replicate < EVAL_REPLICATES:
        raise ValueError("eval mode or replicate is outside the preregistered range")
    return EVAL_SEED_BASE + 1000 * EVAL_MODE_INDEX[mode] + replicate


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source", type=Path, required=True)
    parser.add_argument("--solver", type=Path, required=True)
    parser.add_argument("--approval-token")
    args = parser.parse_args()
    package_root = Path(__file__).resolve().parent

    if args.approval_token != SYNTHETIC_APPROVAL_TOKEN:
        raise SystemExit("eval seed generation requires explicit root review approval")
    eval_root = package_root / EVAL_DIR_NAME
    eval_root.mkdir(parents=True, exist_ok=False)
    for mode in EVAL_MODE_INDEX:
        mode_dir = eval_root / mode
        mode_dir.mkdir()
        mode_metadata = []
        for replicate in range(EVAL_REPLICATES):
            mode_metadata.append(
                generate_stream(
                    mode=mode,
                    seed=_seed_for_eval(mode, replicate),
                    epoch_count=EVAL_EPOCHS,
                    source=args.source,
                    binary=args.solver,
                    output_dir=mode_dir,
                    stem=f"{mode}-{replicate:02d}",
                )
            )
        _write_eval_manifest(mode, mode_dir, mode_metadata)


if __name__ == "__main__":
    main()
