"""Deterministic, witness-backed microstreams for SEARCH-v3.1.

This module deliberately has no filesystem, process, network, solver, or model
dependencies.  It creates legal insert/delete command streams and a fixed-layout
certificate showing that the rounded peak capacity is feasible without moves.
"""

from __future__ import annotations

import hashlib
import random


MICRO_FAMILIES = (
    "micro_gap_refill",
    "micro_neighbor_coalescence",
    "micro_short_churn",
    "micro_size_shift",
    "micro_tail_reuse",
    "micro_partial_drain",
)

VERSION = "search-v3.1/micro-r1"
SECTION_M = 20
MAX_PIPE_M = 40
MAX_OPERATIONS = 80


def _namespace(family: str, variant: int) -> str:
    return f"{VERSION}/{family}/{variant}"


def _seed(namespace: str) -> int:
    return int.from_bytes(hashlib.sha256(namespace.encode("utf-8")).digest()[:8], "big")


def make_micro_specs() -> list[dict]:
    """Return the fixed 24-case search block (six mechanisms by four seeds)."""
    specs = []
    for family_index, family in enumerate(MICRO_FAMILIES):
        for variant in range(4):
            namespace = _namespace(family, variant)
            seed = _seed(namespace)
            rng = random.Random(seed ^ 0x4D4943524F31)
            sections = 1 + (family_index + variant) % 3
            specs.append({
                "id": f"s31_{129 + len(specs):03d}_{family}",
                "family": family,
                "variant": variant,
                "role": "search",
                "regime": "micro",
                "mechanism_block": "micro",
                "design_seed": seed,
                "seed_namespace": namespace,
                "operation_budget": rng.randint(56, MAX_OPERATIONS),
                "parameters": {
                    "sections": sections,
                    "capacity_m": sections * SECTION_M,
                    "max_operations": MAX_OPERATIONS,
                    "small_length_max_m": 8,
                },
            })
    return specs


def _partition(total: int, count: int, rng: random.Random) -> list[int]:
    """Random positive integer composition, preserving the requested sum."""
    if count < 1 or total < count:
        raise ValueError("cannot partition total into positive parts")
    cuts = sorted(rng.sample(range(1, total), count - 1)) if count > 1 else []
    bounds = [0, *cuts, total]
    return [bounds[i + 1] - bounds[i] for i in range(count)]


def _bounded_partition(total: int, count: int, rng: random.Random) -> list[int]:
    """Random positive partition with every value in 1..8."""
    if count < 1 or total < count or total > 8 * count:
        raise ValueError("total cannot fit the requested small-pipe count")
    parts = [1] * count
    remaining = total - count
    while remaining:
        eligible = [i for i, value in enumerate(parts) if value < 8]
        if not eligible:
            raise AssertionError("bounded partition exhausted its capacity")
        index = rng.choice(eligible)
        add = rng.randint(1, min(3, 8 - parts[index], remaining))
        parts[index] += add
        remaining -= add
    return parts


def _initial_count_bounds(peak: int, family: str) -> tuple[int, int]:
    sections = (peak + SECTION_M - 1) // SECTION_M
    if sections == 1:
        bounds = {
            "micro_gap_refill": (6, 9),
            "micro_neighbor_coalescence": (4, 9),
            "micro_short_churn": (4, 6),
            "micro_size_shift": (4, 7),
            "micro_tail_reuse": (4, 7),
            "micro_partial_drain": (5, 9),
        }
    elif sections == 2:
        bounds = {
            "micro_gap_refill": (8, 14),
            "micro_neighbor_coalescence": (8, 15),
            "micro_short_churn": (8, 12),
            "micro_size_shift": (8, 14),
            "micro_tail_reuse": (8, 15),
            "micro_partial_drain": (9, 15),
        }
    else:
        bounds = {
            "micro_gap_refill": (12, 18),
            "micro_neighbor_coalescence": (12, 20),
            "micro_short_churn": (12, 18),
            "micro_size_shift": (12, 18),
            "micro_tail_reuse": (12, 20),
            "micro_partial_drain": (12, 20),
        }
    low, high = bounds[family]
    low = max(low, 4, (peak + 7) // 8)
    high = min(high, peak - 3)
    if low > high:
        raise ValueError("target peak has no feasible initial-count range")
    return low, high


def _initial_layout(peak: int, family: str, rng: random.Random) -> list[int]:
    """Create a shuffled bounded partition with at least three distinct sizes."""
    low, high = _initial_count_bounds(peak, family)
    feasible = []
    for count in range(low, high + 1):
        triples = []
        for a in range(1, 9):
            for b in range(a + 1, 9):
                for c in range(b + 1, 9):
                    filler_count = count - 3
                    remainder = peak - a - b - c
                    if filler_count <= remainder <= 8 * filler_count:
                        triples.append((a, b, c))
        if triples:
            feasible.append((count, triples))
    if not feasible:
        raise AssertionError("no small positive partition with three distinct sizes")
    count, triples = rng.choice(feasible)
    triple = list(rng.choice(triples))
    filler = _bounded_partition(peak - sum(triple), count - 3, rng)
    lengths = triple + filler
    rng.shuffle(lengths)
    if len(set(lengths)) < 3 or sum(lengths) != peak or max(lengths) > 8:
        raise AssertionError("initial small-pipe partition lost its diversity invariant")
    return lengths


class _Layout:
    """Append commands while retaining one immutable feasible coordinate per PID."""

    def __init__(self, capacity: int):
        self.capacity = capacity
        self.commands: list[int] = []
        self.events: list[dict] = []
        self.placements: list[dict] = []
        self.active: dict[int, tuple[int, int]] = {}
        self.next_pid = 1
        self.peak = 0

    def insert(self, length: int, start: int) -> int:
        if not isinstance(length, int) or isinstance(length, bool) or not 1 <= length <= MAX_PIPE_M:
            raise ValueError("pipe length must be an integer in 1..40")
        if not isinstance(start, int) or isinstance(start, bool) or start < 0 or start + length > self.capacity:
            raise ValueError("witness placement is outside target capacity")
        end = start + length
        for other_start, other_length in self.active.values():
            other_end = other_start + other_length
            if start < other_end and other_start < end:
                raise ValueError("witness placement overlaps a live pipe")
        pid = self.next_pid
        self.next_pid += 1
        self.active[pid] = (start, length)
        operation = len(self.commands) + 1
        placement = {"pid": pid, "start_m": start, "length_m": length,
                     "insert_op": operation, "delete_op": None}
        self.placements.append(placement)
        self.commands.append(length)
        self.events.append({"op": operation, "kind": "insert", "command": length,
                            "pid": pid, "start_m": start, "length_m": length})
        volume = sum(size for _, size in self.active.values())
        self.peak = max(self.peak, volume)
        return pid

    def delete(self, pid: int) -> None:
        if pid not in self.active:
            raise ValueError("delete PID is not active")
        del self.active[pid]
        operation = len(self.commands) + 1
        self.commands.append(-pid)
        self.events.append({"op": operation, "kind": "delete", "command": -pid, "pid": pid})
        self.placements[pid - 1]["delete_op"] = operation

    def phase(self, phases: list[dict], name: str, first: int, details: dict | None = None) -> None:
        last = len(self.commands)
        if last < first:
            raise AssertionError(f"empty declared phase: {name}")
        phases.append({"name": name, "start_op": first, "end_op": last,
                       **(details or {})})


def _insert_initial(layout: _Layout, lengths: list[int]) -> list[int]:
    pids, cursor = [], 0
    for length in lengths:
        pids.append(layout.insert(length, cursor))
        cursor += length
    return pids


def _fill_region(layout: _Layout, start: int, lengths: list[int]) -> list[int]:
    pids, cursor = [], start
    for length in lengths:
        pids.append(layout.insert(length, cursor))
        cursor += length
    return pids


def _initial_capacity(spec: dict, rng: random.Random) -> tuple[int, list[int]]:
    sections = spec["parameters"]["sections"]
    capacity = sections * SECTION_M
    # The rounded peak must require exactly this many 20 m sections.
    lower = max(19, (sections - 1) * SECTION_M + 1)
    peak = rng.randint(lower, capacity)
    return peak, _initial_layout(peak, spec["family"], rng)


def _build_family(layout: _Layout, family: str, variant: int, pids: list[int],
                  lengths: list[int], rng: random.Random) -> list[dict]:
    phases: list[dict] = []
    layout.phase(phases, "coldstart", 1,
                 {"insertions": len(pids), "deletions": 0})

    if family == "micro_gap_refill":
        hole_count = min(5, (len(pids) + 1) // 2)
        indices = list(range(0, len(pids), 2))[:hole_count]
        victims = [pids[i] for i in indices]
        first = len(layout.commands) + 1
        for pid in victims:
            layout.delete(pid)
        layout.phase(phases, "separated_hole_creation", first,
                     {"victim_pids": victims})
        first = len(layout.commands) + 1
        refilled = []
        for pid in victims:
            placement = layout.placements[pid - 1]
            size = placement["length_m"]
            fill = max(1, size - (1 if size > 1 and rng.random() < .35 else 0))
            count = 2 if fill >= 3 and rng.random() < .55 else 1
            pieces = _partition(fill, count, rng)
            refilled.extend(_fill_region(layout, placement["start_m"], pieces))
        layout.phase(phases, "holes_refill", first,
                     {"source_victims": victims, "refill_pids": refilled})

    elif family == "micro_neighbor_coalescence":
        pair_index = rng.randrange(len(pids) - 1)
        left, right = pids[pair_index], pids[pair_index + 1]
        a, b = lengths[pair_index], lengths[pair_index + 1]
        gap_start = layout.placements[left - 1]["start_m"]
        first = len(layout.commands) + 1
        layout.delete(left)
        layout.delete(right)
        layout.phase(phases, "neighboring_deletions", first,
                     {"victim_pids": [left, right], "pair_index": pair_index})
        first = len(layout.commands) + 1
        merged_length = rng.randint(max(a, b) + 1, a + b)
        new_pid = layout.insert(merged_length, gap_start)
        layout.phase(phases, "coalesced_gap_refill", first,
                     {"source_victims": [left, right], "refill_pids": [new_pid]})

    elif family == "micro_short_churn":
        max_rounds = 12
        if layout.capacity == SECTION_M:
            max_rounds = min(max_rounds, (18 - len(layout.commands)) // 2)
        rounds = rng.randint(4, max_rounds)
        small_live = [pid for pid in pids if layout.active[pid][1] <= 8]
        first = len(layout.commands) + 1
        pairs = []
        for _ in range(rounds):
            old_pid = rng.choice(small_live)
            start, old_size = layout.active[old_pid]
            layout.delete(old_pid)
            new_size = rng.randint(1, old_size)
            new_pid = layout.insert(new_size, start)
            small_live.remove(old_pid)
            small_live.append(new_pid)
            pairs.append([old_pid, new_pid])
        layout.phase(phases, "short_replacement_churn", first,
                     {"replacement_pairs": pairs, "rounds": rounds})

    elif family == "micro_size_shift":
        count = rng.randint(3, 4)
        eligible_regions = []
        for region_index in range(len(pids) - count + 1):
            region = pids[region_index:region_index + count]
            region_span = sum(layout.active[pid][1] for pid in region)
            if count < region_span < 8 * count:
                eligible_regions.append((region_index, region, region_span))
        if not eligible_regions:
            raise AssertionError("no variable-size contiguous shift region")
        region_index, victims, span = rng.choice(eligible_regions)
        start = layout.placements[victims[0] - 1]["start_m"]
        first = len(layout.commands) + 1
        for pid in victims:
            layout.delete(pid)
        layout.phase(phases, "release_size_shift_region", first,
                     {"victim_pids": victims, "region_start_m": start, "region_length_m": span})
        pieces = _bounded_partition(span, count, rng)
        if len(set(pieces)) == 1:
            pieces[0] -= 1
            pieces[1] += 1
        pieces.sort(reverse=(variant % 2 == 1))
        direction = "large_to_small" if variant % 2 else "small_to_large"
        first = len(layout.commands) + 1
        inserted = _fill_region(layout, start, pieces)
        layout.phase(phases, "request_" + direction, first,
                     {"request_lengths_m": pieces, "inserted_pids": inserted})
        if count == 3:
            first = len(layout.commands) + 1
            victim = rng.choice(list(layout.active))
            layout.delete(victim)
            layout.phase(phases, "post_shift_single_delete", first,
                         {"victim_pids": [victim]})

    elif family == "micro_tail_reuse":
        count = rng.randint(2, min(8, len(pids) - 1))
        victims = pids[-count:]
        suffix_start = layout.placements[victims[0] - 1]["start_m"]
        suffix_length = sum(layout.active[pid][1] for pid in victims)
        first = len(layout.commands) + 1
        for pid in reversed(victims):
            layout.delete(pid)
        layout.phase(phases, "release_tail", first,
                     {"victim_pids_right_to_left": list(reversed(victims)),
                      "tail_start_m": suffix_start, "tail_length_m": suffix_length})
        request_lengths = _bounded_partition(suffix_length, count, rng)
        if variant % 2:
            request_lengths.reverse()
        first = len(layout.commands) + 1
        inserted = _fill_region(layout, suffix_start, request_lengths)
        layout.phase(phases, "tail_reuse", first,
                     {"request_lengths_m": request_lengths, "inserted_pids": inserted,
                      "tail_start_m": suffix_start, "tail_length_m": suffix_length})

    elif family == "micro_partial_drain":
        if variant in (1, 3):
            small_live = [pid for pid in pids if layout.active[pid][1] <= 8]
            first = len(layout.commands) + 1
            rounds = 2 + variant
            pairs = []
            for _ in range(rounds):
                old_pid = rng.choice(small_live)
                start, old_size = layout.active[old_pid]
                layout.delete(old_pid)
                new_pid = layout.insert(rng.randint(1, old_size), start)
                small_live.remove(old_pid)
                small_live.append(new_pid)
                pairs.append([old_pid, new_pid])
            layout.phase(phases, "pre_drain_churn", first,
                         {"replacement_pairs": pairs, "rounds": rounds})
        drain_count = rng.randint(4, min(15 - (rounds if variant in (1, 3) else 0),
                                        len(layout.active) - 1))
        # A declared input-only floor keeps this search family informative for
        # F/T. Deep drain remains a separate stress mechanism.
        final_floor = layout.capacity // 2
        eligible = list(layout.active)
        rng.shuffle(eligible)
        remaining = sum(size for _, size in layout.active.values())
        victims = []
        for pid in eligible:
            size = layout.active[pid][1]
            if remaining - size >= final_floor:
                victims.append(pid)
                remaining -= size
            if len(victims) == drain_count:
                break
        if not victims:
            raise AssertionError("partial drain needs at least one deletion above its volume floor")
        first = len(layout.commands) + 1
        for pid in victims:
            layout.delete(pid)
        layout.phase(phases, "partial_drain", first,
                     {"victim_pids": victims, "drain_count": len(victims),
                      "planned_max_deletions": drain_count, "final_volume_floor_m": final_floor})

    else:
        raise ValueError(f"unknown micro family: {family}")

    return phases


def generate_micro(spec: dict) -> tuple[list[int], dict]:
    """Generate one finite legal stream and its non-moving layout witness."""
    if spec.get("role") != "search" or spec.get("regime") != "micro" or spec.get("mechanism_block") != "micro":
        raise ValueError("micro generator accepts only declared search micro specs")
    family, variant = spec.get("family"), spec.get("variant")
    if family not in MICRO_FAMILIES or not isinstance(variant, int) or isinstance(variant, bool) or not 0 <= variant < 4:
        raise ValueError("unknown micro family or variant")
    expected_namespace = _namespace(family, variant)
    if spec.get("seed_namespace") != expected_namespace or spec.get("design_seed") != _seed(expected_namespace):
        raise ValueError("micro design seed is outside its fixed namespace")
    params = spec.get("parameters")
    if not isinstance(params, dict):
        raise ValueError("micro parameters are required")
    family_index = MICRO_FAMILIES.index(family)
    sections = 1 + (family_index + variant) % 3
    if params.get("sections") != sections or params.get("capacity_m") != sections * SECTION_M:
        raise ValueError("micro target sections do not match the fixed family/variant design")
    budget = spec.get("operation_budget")
    if not isinstance(budget, int) or isinstance(budget, bool) or not 8 <= budget <= MAX_OPERATIONS:
        raise ValueError("micro operation budget must be in 8..80")

    seed = spec["design_seed"]
    rng = random.Random(seed)
    peak, lengths = _initial_capacity(spec, rng)
    capacity = sections * SECTION_M
    layout = _Layout(capacity)
    initial_start = len(layout.commands) + 1
    pids = _insert_initial(layout, lengths)
    if len(layout.commands) != len(pids):
        raise AssertionError("coldstart must consist only of insertions")
    phases = _build_family(layout, family, variant, pids, lengths, rng)
    # Replace the provisional coldstart end with the exact insertion-only extent.
    phases[0]["end_op"] = len(pids)
    phases[0]["start_op"] = initial_start

    if len(layout.commands) > min(budget, MAX_OPERATIONS):
        raise AssertionError("fixed micro plan exceeded its declared operation budget")
    final_volume = sum(length for _, length in layout.active.values())
    if not layout.active or final_volume <= 0 or layout.peak != peak:
        raise AssertionError("microstream must retain positive final volume and exact planned peak")
    if not (20 * (sections - 1) < layout.peak <= capacity):
        raise AssertionError("rounded peak does not require exactly the declared sections")

    witness = {
        "version": "micro-layout-v1",
        "target_capacity_sections": sections,
        "capacity_m": capacity,
        "peak_volume_m": layout.peak,
        "final_volume_m": final_volume,
        "placements": layout.placements,
        "events": layout.events,
    }
    metadata = {
        "seed": seed,
        "seed_namespace": expected_namespace,
        "generator_attempt": 0,
        "termination": {
            "policy": "fixed finite phases declared before stream construction",
            "appended_insertions": 0,
            "appended_deletions": 0,
        },
        "family": family,
        "variant": variant,
        "operations": len(layout.commands),
        "target_capacity_sections": sections,
        "target_capacity_m": capacity,
        "peak_volume_m": layout.peak,
        "final_volume_m": final_volume,
        "final_live_count": len(layout.active),
        "initial_small_lengths_m": sorted(set(lengths)),
        "phases": phases,
        "layout_witness": witness,
    }
    if not verify_layout_witness(layout.commands, metadata):
        raise AssertionError("generated micro layout witness failed its verifier")
    return layout.commands, metadata


def verify_layout_witness(commands: list[int], metadata: dict) -> bool:
    """Validate the fixed-coordinate certificate; raises ValueError if malformed."""
    witness = metadata.get("layout_witness")
    if not isinstance(witness, dict) or witness.get("version") != "micro-layout-v1":
        raise ValueError("missing or unsupported layout witness")
    sections = witness.get("target_capacity_sections")
    capacity = witness.get("capacity_m")
    if not isinstance(sections, int) or isinstance(sections, bool) or sections not in (1, 2, 3):
        raise ValueError("invalid target section count")
    if capacity != sections * SECTION_M or metadata.get("target_capacity_m") != capacity:
        raise ValueError("witness capacity does not match target section count")
    events, placements = witness.get("events"), witness.get("placements")
    if not isinstance(commands, list) or not commands or not isinstance(events, list) or len(events) != len(commands):
        raise ValueError("witness event coverage does not match commands")
    if not isinstance(placements, list):
        raise ValueError("witness placements must be a list")
    placement_by_pid = {}
    for row in placements:
        if not isinstance(row, dict):
            raise ValueError("malformed placement record")
        pid, start, length = row.get("pid"), row.get("start_m"), row.get("length_m")
        if (not isinstance(pid, int) or isinstance(pid, bool) or pid < 1
                or not isinstance(start, int) or isinstance(start, bool)
                or not isinstance(length, int) or isinstance(length, bool)
                or length < 1 or length > MAX_PIPE_M or start < 0 or start + length > capacity
                or pid in placement_by_pid):
            raise ValueError("invalid or duplicate fixed placement")
        placement_by_pid[pid] = row

    active: dict[int, tuple[int, int]] = {}
    observed_deletions: dict[int, int] = {}
    next_pid, peak = 1, 0
    for index, (command, event) in enumerate(zip(commands, events), 1):
        if not isinstance(command, int) or isinstance(command, bool) or command == 0 or not isinstance(event, dict):
            raise ValueError("commands must be nonzero integers with event records")
        if event.get("op") != index or event.get("command") != command:
            raise ValueError("witness event does not match command stream")
        pid = event.get("pid")
        if command > 0:
            row = placement_by_pid.get(next_pid)
            if (event.get("kind") != "insert" or pid != next_pid or row is None
                    or row.get("insert_op") != index or row.get("length_m") != command
                    or event.get("length_m") != command or event.get("start_m") != row.get("start_m")):
                raise ValueError("insert event and fixed placement disagree")
            start = row["start_m"]
            end = start + command
            if any(start < other_start + other_length and other_start < end
                   for other_start, other_length in active.values()):
                raise ValueError("fixed placements overlap during live interval")
            active[next_pid] = (start, command)
            next_pid += 1
            peak = max(peak, sum(length for _, length in active.values()))
        else:
            target = -command
            if event.get("kind") != "delete" or pid != target or target not in active:
                raise ValueError("delete event does not name an active PID")
            del active[target]
            observed_deletions[target] = index
            if placement_by_pid[target].get("delete_op") != index:
                raise ValueError("placement deletion operation is inconsistent")

    if set(placement_by_pid) != set(range(1, next_pid)):
        raise ValueError("placement records do not cover all insertions")
    for pid, row in placement_by_pid.items():
        if row.get("delete_op") != observed_deletions.get(pid):
            raise ValueError("placement deletion marker disagrees with command stream")
    final_volume = sum(length for _, length in active.values())
    if not active or final_volume <= 0:
        raise ValueError("microstream must finish with positive live volume")
    if (peak != witness.get("peak_volume_m") or peak != metadata.get("peak_volume_m")
            or final_volume != witness.get("final_volume_m") or final_volume != metadata.get("final_volume_m")
            or len(active) != metadata.get("final_live_count")
            or not SECTION_M * (sections - 1) < peak <= capacity):
        raise ValueError("peak/final occupancy does not prove the declared rounded capacity")
    termination = metadata.get("termination", {})
    if termination.get("appended_insertions") != 0 or termination.get("appended_deletions") != 0:
        raise ValueError("microstream termination may not append undeclared commands")
    if len(commands) > MAX_OPERATIONS or metadata.get("operations") != len(commands):
        raise ValueError("microstream length is outside its declared bound")
    return True

