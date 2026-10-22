"""Shared, frozen definitions for the joint-deletion signal study."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable

HORIZON = 128
PAIR_CAP = 256
PROTOCOL_VERSION = "joint-deletion-signal-v3"
GROUPED_LOG_OR = 2.0
FROZEN_SOURCE_SHA256 = (
    "c4b737b9a14588dd9895450acaff804b140691ef4d41bf1a0d68b6f13232a991"
)
FROZEN_BINARY_SHA256 = (
    "dabb6910bde7550dbf4ab03d6d7b450d0a91f53a90dc06e52d6b271c8602000c"
)


@dataclass(frozen=True)
class Pipe:
    pid: int
    length: int
    start: int
    placed_at: int
    length_occurrence_parity: int


@dataclass(frozen=True)
class PipeFeatures:
    length: int
    age_band: int
    newest_rank_quartile: int
    length_occurrence_parity: int


@dataclass(frozen=True)
class Pair:
    left: Pipe
    right: Pipe
    relation: int


def age_band(age_commands: int) -> int:
    if age_commands < 128:
        return 0
    if age_commands < 512:
        return 1
    if age_commands < 2048:
        return 2
    return 3


def features(pipe: Pipe, snapshot_t: int, active: Iterable[Pipe]) -> PipeFeatures:
    return feature_map(active, snapshot_t)[pipe.pid]


def feature_map(active: Iterable[Pipe], snapshot_t: int) -> dict[int, PipeFeatures]:
    active_by_pid = sorted(active, key=lambda item: item.pid)
    if not active_by_pid:
        return {}
    result: dict[int, PipeFeatures] = {}
    count = len(active_by_pid)
    for index, pipe in enumerate(active_by_pid):
        if count <= 1:
            newest_rank_quartile = 0
        else:
            newer = count - 1 - index
            fraction = newer / (count - 1)
            newest_rank_quartile = min(3, int(4 * fraction))
        result[pipe.pid] = PipeFeatures(
            length=pipe.length,
            age_band=age_band(snapshot_t - pipe.placed_at),
            newest_rank_quartile=newest_rank_quartile,
            length_occurrence_parity=pipe.length_occurrence_parity,
        )
    return result


def adjacent_disjoint_pairs(active: Iterable[Pipe]) -> list[Pair]:
    ordered = sorted(active, key=lambda item: (item.start, item.pid))
    pairs: list[Pair] = []
    index = 0
    while index + 1 < len(ordered):
        left = ordered[index]
        right = ordered[index + 1]
        if left.start + left.length == right.start:
            pairs.append(
                Pair(left=left, right=right, relation=int(left.length == right.length))
            )
            index += 2
        else:
            index += 1
    if len(pairs) <= PAIR_CAP:
        return pairs
    count = len(pairs)
    # Exact integer form of floor((j + 1/2) * count / PAIR_CAP).
    selected = [((2 * slot + 1) * count) // (2 * PAIR_CAP) for slot in range(PAIR_CAP)]
    return [pairs[index] for index in selected]


def synthetic_hazard(length: int, age_commands: int) -> float:
    length_band = (length - 1) // 5
    probability = 0.08 + 0.012 * length_band + 0.02 * age_band(age_commands)
    return min(0.35, probability)


def splitmix64(value: int) -> int:
    mask = (1 << 64) - 1
    value = (value + 0x9E3779B97F4A7C15) & mask
    value = ((value ^ (value >> 30)) * 0xBF58476D1CE4E5B9) & mask
    value = ((value ^ (value >> 27)) * 0x94D049BB133111EB) & mask
    return (value ^ (value >> 31)) & mask


def uniform_draw(seed: int, epoch: int, key: int) -> float:
    """A deterministic stateless U[0,1) draw indexed by seed/epoch/key."""
    mixed = splitmix64(
        (seed & ((1 << 64) - 1))
        ^ splitmix64(epoch + 0xD1B54A32D192ED03)
        ^ splitmix64(key + 0x94D049BB133111EB)
    )
    return (mixed >> 11) / float(1 << 53)
