"""Local proposal guards for two workers; no candidate execution on import."""

from pathlib import Path
import types

from research import atomic_json, code_hash, exact_duplicate, read_programs


def reserve_source(state, code):
    """Atomically within the event-loop thread reject completed/in-flight copies.

    The caller performs no await between this check and reservation. A frozen
    proposal snapshot is insufficient: another worker may have completed since
    this proposal began. Reservations are run-process-local; the run manager
    holds an exclusive lock and terminates its descendants before resume.
    """
    run = state.get("run")
    if run is None:  # Serial fixtures and the original standalone guard.
        duplicate = exact_duplicate(code, state["programs"])
        return None if duplicate is None else f"evaluated SEARCH-v3.1 generation {duplicate['generation']}"
    programs = read_programs(run)
    reservations = state["reservations"]
    finished = {p["generation"] for p in programs}
    for sha, generation in list(reservations.items()):
        if generation in finished or (Path(run) / f"gen_{generation}" / "failure.json").exists():
            del reservations[sha]
    duplicate = exact_duplicate(code, programs)
    sha = code_hash(code)
    if duplicate is not None:
        return f"evaluated SEARCH-v3.1 generation {duplicate['generation']}"
    owner = reservations.get(sha)
    if owner is not None and owner != state["generation"]:
        return f"in-flight SEARCH-v3.1 proposal {owner} (not evaluated yet)"
    reservations[sha] = state["generation"]
    atomic_json(Path(run) / "inflight-sources.json", {
        "scope": "diagnostic snapshot; reconstructed by the current process",
        "sources": reservations,
    })
    return None


def install_crossover_feedback(runner):
    """Native cross prompts otherwise omit both meta advice and our ledger."""
    sampler = getattr(runner, "prompt_sampler", None)
    if sampler is None or getattr(sampler, "_pipes_cross_feedback", False):
        return
    original = sampler.sample

    def sample(self, *args, **kwargs):
        system, prompt, patch_type = original(*args, **kwargs)
        recommendations = kwargs.get("meta_recommendations")
        if recommendations is None and len(args) > 3:
            recommendations = args[3]
        if patch_type == "cross" and recommendations not in (None, "none", ""):
            system += "\n\n# Research evidence and potential recommendations\n" + recommendations
        return system, prompt, patch_type

    sampler.sample = types.MethodType(sample, sampler)
    sampler._pipes_cross_feedback = True
