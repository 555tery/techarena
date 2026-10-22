"""Mixed, isolated lineage bootstrap for SEARCH-v3.1.

This module is inert on import. It validates the pinned seed plan, assigns
proposal generations to one of eight lineages, and assembles task-only seeds
inside the run directory. It never launches a model, compiler, evaluator, or
search by itself.
"""

from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
import tempfile
import time
import fcntl
from contextlib import contextmanager
from typing import Any, Mapping


VERSION = "mixed-seeds-v1"
STATE_NAME = "mixed-seed-state.json"
STATE_LOCK_NAME = "mixed-seed-state.lock"
START_MARKER = "// EVOLVE-BLOCK-START"
END_MARKER = "// EVOLVE-BLOCK-END"


def digest_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _safe_pinned_file(root: Path, relative: str, expected: str) -> tuple[Path, str]:
    if not isinstance(relative, str) or not relative or Path(relative).is_absolute():
        raise ValueError("seed-plan file paths must be nonempty and relative")
    root = root.resolve()
    path = root / relative
    if path.is_symlink():
        raise ValueError("seed-plan files cannot be symlinks")
    resolved = path.resolve()
    if not resolved.is_relative_to(root) or not resolved.is_file():
        raise ValueError("seed-plan file escaped SEARCH-v3.1 or is missing")
    raw = resolved.read_bytes()
    if hashlib.sha256(raw).hexdigest() != expected:
        raise ValueError(f"seed-plan file hash changed: {relative}")
    content = raw.decode("utf-8")
    return resolved, content


def load_plan(root: str | os.PathLike[str]) -> dict[str, Any]:
    """Load and fully validate the immutable mixed-start plan and assets."""
    root = Path(root).resolve()
    path = root / "seed-plan.json"
    plan = json.loads(path.read_text(encoding="utf-8"))
    if (plan.get("version") != VERSION or plan.get("initial_islands") != 8
            or plan.get("max_islands") != 10
            or plan.get("isolation_correct_per_lineage") != 4):
        raise ValueError("mixed seed plan does not match the authorized eight-lineage policy")
    seeds = plan.get("seeds")
    if not isinstance(seeds, list) or len(seeds) != 8:
        raise ValueError("mixed seed plan must contain eight lineages")
    if [item.get("lineage_id") for item in seeds] != list(range(8)):
        raise ValueError("mixed seed lineages must be ordered and numbered 0 through 7")
    kinds = [item.get("kind") for item in seeds]
    if kinds.count("strong") != 2 or kinds.count("simple") != 2 or kinds.count("independent") != 4:
        raise ValueError("mixed start requires two strong, two simple, and four independent lineages")

    checked = []
    independent_prompts = set()
    for seed in seeds:
        kind = seed["kind"]
        if not isinstance(seed.get("name"), str) or not seed["name"].strip():
            raise ValueError("every mixed seed needs a name")
        if kind in {"strong", "simple"}:
            if "prompt_path" in seed or "prompt_sha256" in seed:
                raise ValueError("fixed source seeds cannot contain prompt references")
            source_path, source = _safe_pinned_file(
                root, seed.get("source_path"), seed.get("source_sha256")
            )
            _split_source(source)
            checked.append({**seed, "source_path_resolved": str(source_path), "source": source})
        else:
            if "source_path" in seed or "source_sha256" in seed:
                raise ValueError("independent seeds may receive a task prompt only")
            prompt_path, prompt = _safe_pinned_file(
                root, seed.get("prompt_path"), seed.get("prompt_sha256")
            )
            independent_prompts.add((seed["prompt_path"], seed["prompt_sha256"]))
            scaffold = extract_scaffold(prompt)
            _split_source(scaffold)
            checked.append({**seed, "prompt_path_resolved": str(prompt_path), "prompt": prompt,
                            "scaffold": scaffold})
    if len(independent_prompts) != 1:
        raise ValueError("all four independent lineages must use the same task-only prompt and interface")
    plan = {**plan, "seeds": checked, "plan_sha256": hashlib.sha256(path.read_bytes()).hexdigest()}
    return plan


def _split_source(source: str) -> tuple[str, str, str]:
    if source.count(START_MARKER) != 1 or source.count(END_MARKER) != 1:
        raise ValueError("candidate scaffold must contain exactly one EVOLVE-BLOCK")
    start = source.index(START_MARKER) + len(START_MARKER)
    end = source.index(END_MARKER, start)
    if end < start:
        raise ValueError("candidate scaffold has reversed EVOLVE-BLOCK markers")
    return source[:start], source[start:end], source[end:]


def extract_scaffold(prompt: str) -> str:
    """Extract the single complete C++ scaffold from the task-only prompt."""
    fences = []
    marker = "```cpp"
    offset = 0
    while True:
        start = prompt.find(marker, offset)
        if start < 0:
            break
        body_start = prompt.find("\n", start + len(marker))
        if body_start < 0:
            raise ValueError("independent prompt has an unterminated C++ fence")
        end = prompt.find("```", body_start + 1)
        if end < 0:
            raise ValueError("independent prompt has an unterminated C++ fence")
        fences.append(prompt[body_start + 1:end].strip("\n") + "\n")
        offset = end + 3
    if len(fences) != 1:
        raise ValueError("independent task prompt must contain exactly one C++ scaffold")
    return fences[0]


def protected_parts(source: str) -> tuple[str, str]:
    prefix, _, suffix = _split_source(source)
    return prefix, suffix


def replace_evolve_block(scaffold: str, candidate: str) -> str:
    prefix, _, suffix = _split_source(scaffold)
    _, block, _ = _split_source(candidate)
    return prefix + block + suffix


def extract_evolve_block(response: str, scaffold: str) -> str:
    """Read model output and return only its mutable block.

    Prefix and suffix are reconstructed from the pinned scaffold, so a model
    response can never alter protocol code outside EVOLVE-BLOCK.
    """
    source = response.strip()
    if "```" in source:
        start = source.find("```cpp")
        if start < 0:
            raise ValueError("independent response must contain a fenced C++ source")
        body_start = source.find("\n", start + len("```cpp"))
        end = source.find("```", body_start + 1)
        if body_start < 0 or end < 0:
            raise ValueError("independent response has an unterminated C++ fence")
        source = source[body_start + 1:end]
    _, block, _ = _split_source(source)
    return replace_evolve_block(scaffold, source)


def seed_for_lineage(plan: Mapping[str, Any], lineage_id: int) -> dict[str, Any]:
    if type(lineage_id) is not int or not 0 <= lineage_id < 8:
        raise ValueError("lineage id must be in [0, 7]")
    return plan["seeds"][lineage_id]


def initial_seed_for_generation(plan: Mapping[str, Any], generation: int) -> dict[str, Any] | None:
    """The first eight evaluated slots are baseline plus lineages 1 through 7."""
    if type(generation) is not int or generation < 1:
        raise ValueError("candidate generation must be positive")
    if 1 <= generation <= 7:
        return seed_for_lineage(plan, generation)
    return None


def _atomic_json(path: Path, payload: Mapping[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, name = tempfile.mkstemp(prefix=f".{path.name}.", dir=path.parent)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as stream:
            json.dump(payload, stream, ensure_ascii=False, sort_keys=True, indent=2)
            stream.write("\n")
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(name, path)
    except BaseException:
        try:
            os.unlink(name)
        except FileNotFoundError:
            pass
        raise


def _state_path(run: Path) -> Path:
    return run / STATE_NAME


@contextmanager
def _state_lock(run: Path):
    """Serialize state read-modify-write across the event loop and DB worker."""
    run.mkdir(parents=True, exist_ok=True)
    with (run / STATE_LOCK_NAME).open("a+") as stream:
        fcntl.flock(stream.fileno(), fcntl.LOCK_EX)
        try:
            yield
        finally:
            fcntl.flock(stream.fileno(), fcntl.LOCK_UN)


def _load_state(run: Path) -> dict[str, Any]:
    path = _state_path(run)
    if not path.exists():
        return {"version": VERSION, "assignments": {}, "isolation_released": False,
                "created_at": time.time()}
    state = json.loads(path.read_text(encoding="utf-8"))
    if state.get("version") != VERSION or not isinstance(state.get("assignments"), dict):
        raise ValueError("mixed seed state is malformed or from another runtime version")
    return state


def _row_metadata(program: Mapping[str, Any]) -> dict[str, Any]:
    value = program.get("metadata")
    if isinstance(value, dict):
        return value
    if isinstance(value, str):
        try:
            parsed = json.loads(value)
        except json.JSONDecodeError:
            return {}
        return parsed if isinstance(parsed, dict) else {}
    return {}


def _is_copy(program: Mapping[str, Any]) -> bool:
    metadata = _row_metadata(program)
    return bool(metadata.get("_is_island_copy") or metadata.get("_spawned_island"))


def _program_rows_by_generation(programs: list[Mapping[str, Any]]) -> dict[int, list[Mapping[str, Any]]]:
    result: dict[int, list[Mapping[str, Any]]] = {}
    for program in programs:
        generation = program.get("generation")
        if type(generation) is int:
            result.setdefault(generation, []).append(program)
    return result


def _resolved(run: Path, generation: int, rows: Mapping[int, list[Mapping[str, Any]]]) -> bool:
    if rows.get(generation):
        return True
    return (run / f"gen_{generation}" / "failure.json").is_file()


def _correct_counts(programs: list[Mapping[str, Any]]) -> tuple[list[int], list[bool]]:
    counts = [0] * 8
    roots = [False] * 8
    for program in programs:
        if not program.get("correct") or _is_copy(program):
            continue
        island = program.get("island_idx")
        generation = program.get("generation")
        if type(island) is not int or not 0 <= island < 8 or type(generation) is not int:
            continue
        counts[island] += 1
        metadata = _row_metadata(program)
        assignment = metadata.get("mixed_seed")
        if island == 0 and generation == 0:
            roots[0] = True
        elif isinstance(assignment, dict) and assignment.get("phase") == "seed" \
                and assignment.get("lineage_id") == island:
            roots[island] = True
    return counts, roots


def warmup_status(programs: list[Mapping[str, Any]], required: int = 4) -> dict[str, Any]:
    if type(required) is not int or required < 1:
        raise ValueError("required correct programs per lineage must be positive")
    counts, roots = _correct_counts(programs)
    complete = all(roots) and all(count >= required for count in counts)
    return {"complete": complete, "correct_per_lineage": counts,
            "roots_present": roots, "required": required}


def _active_assignments(
    run: Path,
    state: Mapping[str, Any],
    rows: Mapping[int, list[Mapping[str, Any]]],
    phase: str | None = None,
) -> list[tuple[int, dict[str, Any]]]:
    active = []
    for raw_generation, assignment in state.get("assignments", {}).items():
        try:
            generation = int(raw_generation)
        except (TypeError, ValueError):
            continue
        if not isinstance(assignment, dict) or (phase and assignment.get("phase") != phase):
            continue
        if not _resolved(run, generation, rows):
            active.append((generation, assignment))
    return active


def _reserve_assignment_unlocked(
    run: str | os.PathLike[str],
    programs: list[Mapping[str, Any]],
    generation: int,
    plan: Mapping[str, Any],
) -> dict[str, Any] | None:
    """Reserve a seed/warmup slot, return None once ordinary search may begin.

    Returns ``{"wait": true}`` while earlier bootstrap candidates are in
    flight and no additional lineage can safely be assigned. Callers may yield
    and retry; they must not select from another lineage in that state.
    """
    if type(generation) is not int or generation < 1:
        raise ValueError("mixed bootstrap requires a positive proposal generation")
    run = Path(run).resolve()
    state = _load_state(run)
    existing = state["assignments"].get(str(generation))
    if isinstance(existing, dict):
        return dict(existing)
    if state.get("isolation_released"):
        return None

    required = int(plan["isolation_correct_per_lineage"])
    status = warmup_status(programs, required)
    rows = _program_rows_by_generation(programs)
    counts = status["correct_per_lineage"]
    roots = status["roots_present"]

    # The first seven evaluated proposals are deterministic seed slots. The
    # initial generation-zero baseline is lineage zero.
    if 1 <= generation <= 7:
        lineage = generation
        assignment = {"phase": "seed", "lineage_id": lineage,
                      "kind": plan["seeds"][lineage]["kind"],
                      "name": plan["seeds"][lineage]["name"], "retry": 0}
    elif not all(roots):
        active = _active_assignments(run, state, rows, "seed")
        pending_lineages = {int(item.get("lineage_id", -1)) for _, item in active}
        missing = [i for i in range(1, 8) if not roots[i]]
        unassigned = [i for i in missing if i not in pending_lineages]
        if not unassigned:
            return {"wait": True, "reason": "independent seed evaluations are still in flight"}
        lineage = unassigned[0]
        prior = [item for item in state["assignments"].values()
                 if isinstance(item, dict) and item.get("phase") == "seed"
                 and item.get("lineage_id") == lineage]
        assignment = {"phase": "seed", "lineage_id": lineage,
                      "kind": plan["seeds"][lineage]["kind"],
                      "name": plan["seeds"][lineage]["name"], "retry": len(prior)}
    elif status["complete"]:
        state["isolation_released"] = True
        state["isolation_released_at_generation"] = max((int(g) for g in rows), default=0)
        state["isolation_status"] = status
        _atomic_json(_state_path(run), state)
        return None
    else:
        active = _active_assignments(run, state, rows)
        reserved = [0] * 8
        for _, item in active:
            lineage = item.get("lineage_id")
            if type(lineage) is int and 0 <= lineage < 8 and item.get("phase") == "warmup":
                reserved[lineage] += 1
            if type(lineage) is int and 0 <= lineage < 8 and item.get("phase") == "seed":
                reserved[lineage] += 1
        available = [i for i in range(8) if counts[i] + reserved[i] < required]
        if not available:
            return {"wait": True, "reason": "correct warmup evaluations are still in flight"}
        lineage = min(available, key=lambda i: (counts[i] + reserved[i], counts[i], i))
        assignment = {"phase": "warmup", "lineage_id": lineage,
                      "kind": plan["seeds"][lineage]["kind"],
                      "name": plan["seeds"][lineage]["name"], "retry": 0}

    state["assignments"][str(generation)] = assignment
    state["last_assignment_generation"] = generation
    _atomic_json(_state_path(run), state)
    return dict(assignment)


def reserve_assignment(
    run: str | os.PathLike[str],
    programs: list[Mapping[str, Any]],
    generation: int,
    plan: Mapping[str, Any],
) -> dict[str, Any] | None:
    """Reserve one slot under a process-shared read-modify-write lock."""
    with _state_lock(Path(run).resolve()):
        return _reserve_assignment_unlocked(run, programs, generation, plan)


def _mark_isolation_released_unlocked(
    run: str | os.PathLike[str], programs: list[Mapping[str, Any]], required: int = 4,
) -> bool:
    """Persist the one-way transition from isolated lineages to shared search."""
    run = Path(run).resolve()
    state = _load_state(run)
    if state.get("isolation_released"):
        return True
    status = warmup_status(programs, required)
    if status["complete"]:
        state["isolation_released"] = True
        state["isolation_status"] = status
        state["isolation_released_at_generation"] = max(
            (int(p["generation"]) for p in programs if type(p.get("generation")) is int), default=0
        )
        _atomic_json(_state_path(run), state)
        return True
    return False


def mark_isolation_released(
    run: str | os.PathLike[str], programs: list[Mapping[str, Any]], required: int = 4,
) -> bool:
    """Persist the one-way isolation transition without racing reservations."""
    with _state_lock(Path(run).resolve()):
        return _mark_isolation_released_unlocked(run, programs, required)


def assignment_for_generation(run: str | os.PathLike[str], generation: int) -> dict[str, Any] | None:
    state = _load_state(Path(run).resolve())
    value = state.get("assignments", {}).get(str(generation))
    return dict(value) if isinstance(value, dict) else None


def seed_code(plan: Mapping[str, Any], lineage_id: int, scaffold: str) -> str:
    seed = seed_for_lineage(plan, lineage_id)
    if seed["kind"] == "independent":
        return seed["scaffold"]
    source = seed["source"]
    return replace_evolve_block(scaffold, source)


def independent_candidate(response: str, prompt_scaffold: str, run_scaffold: str) -> str:
    """Use model logic only; keep the selected task's protected source exact."""
    prompt_prefix, _, prompt_suffix = _split_source(prompt_scaffold)
    run_prefix, _, run_suffix = _split_source(run_scaffold)
    def same_with_optional_terminal_newline(left: str, right: str) -> bool:
        return left == right or left + "\n" == right or right + "\n" == left

    if (not same_with_optional_terminal_newline(prompt_prefix, run_prefix)
            or not same_with_optional_terminal_newline(prompt_suffix, run_suffix)):
        raise ValueError("independent prompt scaffold differs from the frozen task interface")
    returned = extract_evolve_block(response, prompt_scaffold)
    return replace_evolve_block(run_scaffold, returned)


def safe_wait_should_stop(runner: Any) -> bool:
    event = getattr(runner, "should_stop", None)
    return bool(event is not None and event.is_set())
