"""Bounded native feedback retries and stop on pre-evaluation failure, v2 only."""

from __future__ import annotations

import types

MAX_PATCH_ATTEMPTS = 3  # Original proposal plus at most two feedback corrections.


def policy() -> dict:
    return {
        "max_patch_attempts": MAX_PATCH_ATTEMPTS,
        "max_patch_resamples": 1,
        "max_novelty_attempts": 1,
        "corrections_within_same_generation": 2,
        "on_exhaustion": "stop_before_next_generation_without_program_row",
    }


def install_stop_on_failed_proposal(runner) -> None:
    """Keep native diagnostics/costs, then stop instead of spending later slots.

    Native _run_patch_async supplies the apply error and conversation history
    to each retry against the same parent. Only its terminal failure reaches
    this hook. Unlike the v1 recovery hook, this never persists a failed Program.
    The v2 manager reports the early stop rather than claiming completion.
    """
    if getattr(runner, "_search_v2_repair_installed", False):
        return
    original = runner._record_terminal_failed_proposal

    async def record_and_stop(self, **kwargs):
        try:
            await original(**kwargs)
        finally:
            metadata = kwargs.get("meta_patch_data") or {}
            parent = kwargs.get("parent_program")
            self._search_v2_repair_stop = {
                "generation": kwargs["generation"],
                "parent_id": getattr(parent, "id", None),
                "stage": kwargs.get("failure_stage"),
                "reason": kwargs.get("failure_reason"),
                "patch_attempts": metadata.get("patch_attempt"),
                "proposal_cost_estimate": kwargs.get("api_costs", 0.0),
                "failed_program_persisted": False,
                "automatic_restart": False,
            }
            # The pinned runner waits for finalization_complete, not should_stop
            # alone. Set both so an exhausted repair cannot leave a stalled run.
            self.should_stop.set()
            self.slot_available.set()
            self.finalization_complete.set()

    runner._record_terminal_failed_proposal = types.MethodType(record_and_stop, runner)
    runner._search_v2_repair_installed = True


def run_with_patch_repair(cli, *, task, run, generations):
    """Install on this future CLI invocation only; always restore its builder."""
    original_build = cli._build_runner
    runners = []

    def build(**kwargs):
        runner = original_build(**kwargs)
        install_stop_on_failed_proposal(runner)
        runners.append(runner)
        return runner

    cli._build_runner = build
    try:
        result = cli.main([
            "--task-dir", str(task), "--config-fname", "shinka.yaml",
            "--results_dir", str(run), "--num_generations", str(generations),
        ])
    finally:
        cli._build_runner = original_build
    stopped = next((r._search_v2_repair_stop for r in runners
                    if getattr(r, "_search_v2_repair_stop", None)), None)
    return result, stopped
