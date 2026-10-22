#!/usr/bin/env python3
"""Token/reversal and tiny native-scratch-to-local scalar equivalence audit."""
from pathlib import Path
import hashlib
import json
import math
import random
import re
import runpy
import textwrap

BASE = Path(__file__).resolve().parents[1]
REFERENCE = runpy.run_path(str(BASE / "audit/dp_unrolled_differential.py"), run_name="reference_only")
bits, divide = REFERENCE["bits"], REFERENCE["divide"]
lex = re.compile(r'"(?:[^"\\]|\\.)*"|[A-Za-z_]\w*|\d+\.\d+|\d+|==|!=|>=|<=|\.\.=|\.\.|<<|>>|\+=|-=|&&|\|\||[^\s]')


def closing(text, start):
    depth = 0
    for i in range(start, len(text)):
        depth += (text[i] == "{") - (text[i] == "}")
        if depth == 0:
            return i
    raise AssertionError("brace")


def cached_model(rates, previous, gap, expiry):
    cached_rates = tuple(rates)
    first, last = 1, 40
    while last > 0 and rates[last] == 0.0:
        last -= 1
    while first <= last and rates[first] == 0.0:
        first += 1
    large = gap >= 40
    requests = range(1, 41) if large else range(first, min(gap, last) + 1)
    get_rate = lambda q: cached_rates[q] if large else rates[q]
    if expiry == 0.0:
        value = 0.0
        for q in requests:
            if get_rate(q) > 0.0:
                reward = float(q) + previous[gap - q]
                value = value if value > reward else reward
        return (bits(value),)
    cached_rewards = [0.0] * 41
    # Poison the old shared scratch; any unwritten read is caught separately.
    scratch = [math.nan] * 41
    written = 0
    active = 0
    numerator, denominator, minimum = 0.0, expiry, math.inf
    trace = []
    for q in requests:
        rate = get_rate(q)
        if rate != 0.0:
            rr = float(q) + previous[gap - q]
            if rr < minimum:
                minimum = rr
            if large:
                cached_rewards[q] = rr
            else:
                scratch[q] = rr
            written |= 1 << q
            numerator += rate * rr
            denominator += rate
            active |= 1 << q
            trace.append(("add", q, bits(numerator), bits(denominator)))
    estimate = divide(numerator, denominator)
    trace.append(("estimate", bits(estimate)))
    while estimate > minimum:
        minimum, removed = math.inf, False
        for q in requests:
            bit = 1 << q
            if active & bit:
                assert written & bit, "reward read before same-gap write"
                rr = cached_rewards[q] if large else scratch[q]
                if rr < estimate:
                    numerator -= get_rate(q) * rr
                    denominator -= get_rate(q)
                    active &= ~bit
                    removed = True
                    trace.append(("remove", q, bits(numerator), bits(denominator)))
                elif rr < minimum:
                    minimum = rr
        if not removed:
            break
        estimate = divide(numerator, denominator)
        trace.append(("estimate", bits(estimate)))
    return (bits(numerator), bits(denominator), bits(estimate), active, trace)


def main():
    parent_path = BASE / "candidate-age-bin-tree/solution.cj"
    path = BASE / "candidate-dp-scalars/solution.cj"
    parent, source = parent_path.read_text(), path.read_text()
    assert not re.search(r"\b(?:cachedRate|cachedReward|requestRate|requestReward|bit|rr)\d+\b", parent)
    # Check and remove just the80 rate and80 reward declarations independently.
    rate_pattern = re.compile(r"^ +let cachedRate(\d+) = (rate|requestRates)\.read\((\d+)\)\n", re.M)
    reward_pattern = re.compile(r"^ +var cachedReward(\d+): Float64 = 0\.0\n", re.M)
    rate_declarations = list(rate_pattern.finditer(source))
    reward_declarations = list(reward_pattern.finditer(source))
    assert len(rate_declarations) == len(reward_declarations) == 80
    for pointer in ("rate", "requestRates"):
        assert [int(m[1]) for m in rate_declarations if m[2] == pointer] == list(range(1, 41))
    assert all(m[1] == m[3] for m in rate_declarations)
    assert [int(m[1]) for m in reward_declarations] == list(range(1, 41)) * 2
    stripped = reward_pattern.sub("", rate_pattern.sub("", source))
    changes, block_count = [], 0
    mutability = []
    for method, following, gap, pointer in [
        ("rebuildPrimalGapValues", "ensurePrimalGapValues", "g", "rate"),
        ("rebuildCausalGapValues", "causalValueAt", "gap", "requestRates"),
    ]:
        pa = parent.index("    public func " + method + "(")
        pz = parent.index("    public func " + following + "(", pa)
        sa = stripped.index("    public func " + method + "(")
        sz = stripped.index("    public func " + following + "(", sa)
        old, new = parent[pa:pz], stripped[sa:sz]
        a = source.index("    public func " + method + "(")
        z = source.index("    public func " + following + "(", a)
        actual_method = source[a:z]
        cache = actual_method.index("let cachedRate1 =")
        assert not re.search(r"\b" + pointer + r"\.(?:write|fill)\(", actual_method[cache:])
        assert "causalRequestRate.fill(" not in actual_method[cache:]
        assert not re.search(r"cachedRate\d+\s*(?:\+=|-=|=(?!=))", re.sub(r"let cachedRate\d+ = [^\n]+", "", actual_method))
        if pointer == "rate":
            assert actual_method.index("causalRequestRate.fill(0.0)") < actual_method.index("rate.write(gap,") < cache
        loop_start = actual_method.index("for (g in" if gap == "g" else "for (model in")
        assert cache < loop_start
        reward_init = actual_method.index("var cachedReward1:")
        assert loop_start < reward_init < actual_method.index("let reward = dpRewardScratch.borrowData()")
        mutability.append({"method": method, "cache_after_rate_writes": True,
                           "cache_before_gap_or_model_loop": True, "no_later_rate_writes": True,
                           "rewards_initialized_inside_each_gap": True})
        oms = list(re.finditer(r"^( +)for \(request in firstRequest\.\.=top\) \{", old, re.M))
        nms = list(re.finditer(r"^( +)if \(" + gap + r" >= 40\) \{", new, re.M))
        assert len(oms) == len(nms) == (3 if gap == "g" else 2)
        for om, nm in zip(oms, nms):
            oe, ne = closing(old, om.end() - 1), closing(new, nm.end() - 1)
            oldloop = old[om.start():oe + 1]
            body = textwrap.dedent(old[om.end():oe]).strip()
            tokens = lex.findall(new[nm.end():ne])
            cursor = 0
            for q in range(1, 41):
                expected = body
                skip = "if (requestRate == 0.0) { continue }"
                if skip in expected:
                    prefix, suffix = expected.split(skip)
                    expected = prefix + "if (requestRate != 0.0) {" + suffix + "}"
                expected = re.sub(r"\brequest\b", str(q), expected)
                # Storage mapping: scalar loads are copies; local reward stores
                # and reads replace exactly the same indexed scratch accesses.
                expected = expected.replace(f"{pointer}.read({q})", f"cachedRate{q}")
                expected = expected.replace(f"reward.write({q}, requestReward)", f"cachedReward{q} = requestReward")
                expected = expected.replace(f"reward.read({q})", f"cachedReward{q}")
                for name in ("requestRate", "requestReward", "bit", "rr"):
                    expected = re.sub(r"\b" + name + r"\b", name + str(q), expected)
                expected_tokens = lex.findall(expected)
                assert tokens[cursor:cursor + len(expected_tokens)] == expected_tokens
                cursor += len(expected_tokens)
                block_count += 1
            assert cursor == len(tokens)
            em = re.match(r" else \{\n", new[ne + 1:]); assert em
            eo = ne + 1 + em.end() - 2
            ee = closing(new, eo)
            old_from_else = "\n".join(line[4:] for line in new[eo + 1:ee].strip("\n").splitlines()).rstrip()
            assert old_from_else == oldloop
            changes.append((sa + nm.start(), sa + ee + 1, oldloop))
    restored = stripped
    for a, z, old in sorted(changes, reverse=True):
        restored = restored[:a] + old + restored[z:]
    assert restored == parent
    assert source.count("dpRewardScratch") == 3  # declaration and two local borrows
    assert source.count("private let causalRequestRate = FastFloatBuffer(41)") == 1
    assert source.count("private let dpRewardScratch = FastFloatBuffer(41)") == 1
    rng = random.Random(20261021)
    values = [0.0, -0.0, 1e-300, 1e-100, .001, .125, 1.0, 1e100, 1e300,
              -.5, math.inf, -math.inf, math.nan]
    cases = 0
    for i in range(300):
        rates = [0.0] + [rng.choice(values if i % 7 == 0 else values[:9]) if rng.random() < .4 else 0.0 for _ in range(40)]
        previous = [rng.choice(values) if i % 17 == 0 else rng.random() * 512 for _ in range(513)]
        for gap in (1, 39, 40, 41, 512):
            expiry = rng.choice([0.0, -0.0, 1e-300, .001, .25, 1e300, math.inf, math.nan])
            assert REFERENCE["scalar"](rates, previous, gap, expiry, False) == cached_model(rates, previous, gap, expiry)
            cases += 1
    audit = {
        "schema": "dp-scalars-independent-equivalence-v1", "status": "PASS source and bounded Float64 differential",
        "parent_sha256": hashlib.sha256(parent.encode()).hexdigest(),
        "source_sha256": hashlib.sha256(source.encode()).hexdigest(),
        "generator_sha256": hashlib.sha256((BASE / "prepare_dp_scalars.py").read_bytes()).hexdigest(),
        "script_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        "source": {"constant_blocks_token_checked": block_count, "rate_declarations_checked": 80,
                   "reward_declarations_checked": 80, "small_gap_original_verbatim": True,
                   "whole_parent_reverse_exact": restored == parent, "nine_changes": "5 loop branches +2 rate-cache groups +2 reward-local groups"},
        "rates": mutability,
        "ownership": "The41-rate and41-reward buffers are distinct private let FastFloatBuffer owners. Primal initializes rates before caching; no writes/reassignment occur afterward through end of the DP, and causal has no rate writes. DP loops contain no callbacks. lifetimeModel.fit runs after all primal value calculations and owns unrelated model storage.",
        "rewards": "Active starts0 each gap. Every set bit follows its corresponding reward assignment in the same initialization block; elimination only clears bits. Every reward read is inside that bit guard. Small-gap code keeps old scratch path; large-gap code uses fresh locals only. Shared scratch has no consumers outside these two methods (one declaration and exactly two borrows in entire source). Next gap/model/rebuild again requires same-gap write before read, so changed final scratch contents are unobservable.",
        "differential": {"cases": cases, "mismatches": 0, "checked": "Float64 bits for final numerator/denominator/estimate, each accumulation/removal and estimate trace, active mask and zero-expiry max-fold; poisoned scratch and explicit same-gap written mask. Gaps1/39/40/41/512; sparse/zero/NaN/Inf/negative/extreme rates."},
        "fp_order": "All200 blocks token-equal after exact variable/storage mapping; immutable scalar copies add no arithmetic, and reward reads/writes preserve Float64 values. Ascending order and every existing FP expression remain unchanged. NaN/±0 guard behavior is identical.",
        "limits": ["Source and Python audit do not prove target O2 machine-bit parity or backend behavior. Unrolling/local scalars may expose folding/contraction or register pressure; preserve FP flags and validate target outputs.", "Python differential uses a scalar model, not Cangjie execution/full DP tables. No Cangjie compile, solver or CPU benchmark."],
        "compiled": False, "solver_executed": False, "CPU_benchmark_executed": False,
    }
    output = BASE / "audit/dp-scalars-equivalence.json"
    output.write_text(json.dumps(audit, ensure_ascii=False, indent=2) + "\n")
    print(json.dumps({"audit": str(output), "blocks": block_count, "cases": cases, "mismatches": 0}))


if __name__ == "__main__":
    main()
