"""Tiny generated inputs and builds for transport tests, never search candidates."""

from pathlib import Path
import shutil
import subprocess

from reference import BASE, ROOT, check_reference


def build_tools(directory: Path) -> tuple[Path, Path]:
    check_reference()
    compiler = shutil.which("g++")
    if not compiler:
        raise RuntimeError("g++ required for protocol fixtures")
    solver, judge = directory / "fixture_solver", directory / "official_interactor"
    for command in (
        [compiler, "-O2", "-std=c++20", "-pipe", str(ROOT / "fixtures/protocol_solver.cpp"), "-o", str(solver)],
        [compiler, "-O2", "-std=c++17", "-pipe", "-I", str(BASE / "task/vendor"),
         str(BASE / "task/vendor/interactor.cpp"), "-o", str(judge)],
    ):
        subprocess.run(command, capture_output=True, text=True, timeout=120, check=True)
    return solver, judge


def write_input(path: Path, commands: list[int]) -> None:
    path.write_text("1\n" + str(len(commands)) + "\n" + "\n".join(map(str, commands)) + "\n", encoding="ascii")
