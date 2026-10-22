#!/usr/bin/env python3
"""Independent bounded source and scalar-Float64 audit; never invokes Cangjie."""
import hashlib
import json
import math
from pathlib import Path
import random
import re
import struct
import textwrap

BASE = Path(__file__).resolve().parents[1]


def closing(s, start):
    depth = 0
    for i in range(start, len(s)):
        depth += (s[i] == "{") - (s[i] == "}")
        if depth == 0:
            return i
    raise AssertionError("unbalanced")


def tokens(s):
    return re.sub(r"\s+", "", s)


def bits(x):
    return struct.pack("!d", x).hex()


def divide(a, b):
    if b == 0.0:
        if a == 0.0 or math.isnan(a):
            return math.nan
        return math.copysign(math.inf, a * math.copysign(1.0, b))
    return a / b


def scalar(rates, previous, gap, expiry, expanded):
    first, last = 1, 40
    while last > 0 and rates[last] == 0.0:
        last -= 1
    while first <= last and rates[first] == 0.0:
        first += 1
    requests = range(1, 41) if expanded and gap >= 40 else range(first, min(gap, last) + 1)
    if expiry == 0.0:
        value = 0.0
        for q in requests:
            if rates[q] > 0.0:
                reward = float(q) + previous[gap - q]
                value = value if value > reward else reward
        return (bits(value),)
    active = 0
    reward = {}
    minimum = math.inf
    numerator, denominator = 0.0, expiry
    trace = []
    for q in requests:
        rate = rates[q]
        # Old continue and new enclosing !=0 guard have identical predicates.
        if (rate != 0.0) if expanded else not (rate == 0.0):
            rr = float(q) + previous[gap - q]
            if rr < minimum:
                minimum = rr
            reward[q] = rr
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
                rr = reward[q]  # KeyError would detect stale scratch access.
                if rr < estimate:
                    numerator -= rates[q] * rr
                    denominator -= rates[q]
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
    parent_path = BASE / "candidate-lifetime-fast/solution.cj"
    output_path = BASE / "candidate-dp-unrolled/solution.cj"
    parent, output = parent_path.read_text(), output_path.read_text()
    changes = []
    checked_blocks = 0
    for method, following, gap in [
        ("rebuildPrimalGapValues", "ensurePrimalGapValues", "g"),
        ("rebuildCausalGapValues", "causalValueAt", "gap"),
    ]:
        pa = parent.index("    public func " + method + "(")
        pz = parent.index("    public func " + following + "(", pa)
        oa = output.index("    public func " + method + "(")
        oz = output.index("    public func " + following + "(", oa)
        old_section, new_section = parent[pa:pz], output[oa:oz]
        old_matches = list(re.finditer(r"^( +)for \(request in firstRequest\.\.=top\) \{", old_section, re.M))
        new_matches = list(re.finditer(r"^( +)if \(" + gap + r" >= 40\) \{", new_section, re.M))
        assert len(old_matches) == len(new_matches) == (3 if gap == "g" else 2)
        for old_match, new_match in zip(old_matches, new_matches):
            old_end = closing(old_section, old_match.end() - 1)
            new_end = closing(new_section, new_match.end() - 1)
            old_loop = old_section[old_match.start():old_end + 1]
            old_body = textwrap.dedent(old_section[old_match.end():old_end]).strip()
            large_body = new_section[new_match.end():new_end]
            blocks = list(re.finditer(r"^ +if \(true\) \{", large_body, re.M))
            assert len(blocks) == 40
            for q, block in enumerate(blocks, 1):
                stop = closing(large_body, block.end() - 1)
                actual = large_body[block.end():stop]
                expected = re.sub(r"\brequest\b", str(q), old_body)
                zero = "if (requestRate == 0.0) { continue }"
                if zero in expected:
                    prefix, suffix = expected.split(zero)
                    expected = prefix + "if (requestRate != 0.0) {" + suffix + "}"
                assert tokens(actual) == tokens(expected), (method, q)
                checked_blocks += 1
            suffix = new_section[new_end + 1:]
            else_match = re.match(r" else \{\n", suffix)
            assert else_match
            else_open = new_end + 1 + else_match.end() - 2
            else_end = closing(new_section, else_open)
            small_body = new_section[else_open + 1:else_end]
            # Else loop is original text with exactly four extra leading spaces.
            restored_old = "\n".join(line[4:] for line in small_body.strip("\n").splitlines()).rstrip()
            assert restored_old == old_loop
            changes.append((oa + new_match.start(), oa + else_end + 1, old_loop))
    restored = output
    for start, end, old in sorted(changes, reverse=True):
        restored = restored[:start] + old + restored[end:]
    assert restored == parent
    rng = random.Random(20261020)
    palette = [0.0, -0.0, 1e-300, 1e-100, 0.001, 0.25, 1.0, 1e100, 1e300,
               -0.1, math.inf, -math.inf, math.nan]
    cases = []
    for i in range(1000):
        rates = [0.0] + [rng.choice(palette if i % 5 == 0 else palette[:9]) if rng.random() < .35 else 0.0 for _ in range(40)]
        previous = [rng.choice(palette) if i % 11 == 0 else rng.random() * 512 for _ in range(513)]
        cases.append((rates, previous, rng.choice([1, 39, 40, 41, 512]), rng.choice([0.0, -0.0, 1e-300, .001, 1.0, 1e300, math.inf, math.nan])))
    for q in range(1, 41):
        rates = [0.0] * 41
        rates[q] = .125
        for gap in [39, 40, 512]:
            cases.append((rates, [0.0] * 513, gap, .001))
    cases.extend([([0.0] * 41, [0.0] * 513, 512, x) for x in [0.0, .001]])
    for case in cases:
        assert scalar(*case, False) == scalar(*case, True)
    result = {
        "schema": "dp-unrolled-independent-audit-v1", "status": "PASS source and bounded Float64 differential",
        "parent_sha256": hashlib.sha256(parent.encode()).hexdigest(),
        "source_sha256": hashlib.sha256(output.encode()).hexdigest(),
        "script_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        "source_checks": {"loops": len(changes), "constant_blocks_checked": checked_blocks,
                          "small_gap_original_verbatim": True, "whole_source_reverse_exact": restored == parent},
        "scalar_differential": {"cases": len(cases), "mismatches": 0,
                                "compared": "Final numerator/denominator/estimate Float64 bits, active bits, every actual accumulation/removal update, estimate sequence; expiry-zero max-fold bits. No complete DP tables."},
        "support": "Primal fills rates0..40 then sets each1..40; causal uses that same unmodified rate owner. first/last scan excludes only values ==0, hence added requests outside support have +0/-0. Initial blocks do no FP update, zero-expiry blocks fail >0; removal active bits are unset and scratch is not read.",
        "nan": "NaN is not equal to0, is not trimmed by support scans, and is included by both old !=skip and new !=0 guard. The source rewrite does not assume finite math. Signed zero is skipped in both; all-zero support yields no scratch access or updates.",
        "bounds": "Expanded branch requires gap>=40, so gap-request>=0 for every request1..40. Original cap gives primal index<=511 and causal row index<=1024 for predecessor reads; final writes<=512/1025. Rates/reward1..40 are allocated; bit shifts1..40 fit signed Int64. Float64(request) conversions1..40 are exact.",
        "fp_order": "All200 constant bodies independently match original token streams after request substitution and sole zero-continue guard inversion. Ascending request order, arithmetic expressions and serial accumulator dependencies are unchanged; no reassociation/FMA introduced at source level.",
        "optimizer_limit": "Source order and Python tests do not prove target O2 machine-code bit parity. Unrolling/constants can expose compiler optimizations; do not enable --fast-math (documented potentially losing precision). Constant conversions are exact; any FMA/contraction or optimizer bug remains compiler-level verification, not a source-level mismatch found here.",
        "official_compile_option_source": "https://docs.cangjie-lang.cn/en/docs/1.0.0/user_manual/source_en/Appendix/compile_options.html",
        "limits": "Python Float64 follows host IEEE arithmetic, not Cangjie lowering/GC/target code. Tests include invalid-domain NaN/Inf/negative rates as extra control-flow probes; these are not claims about reachable allocator states. No Cangjie compile, solver or benchmark.",
        "cangjie_compiled": False, "solver_executed": False, "CPU_benchmark_executed": False,
    }
    destination = BASE / "audit/dp-unrolled-equivalence.json"
    destination.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n")
    print(json.dumps({"audit": str(destination), "blocks": checked_blocks, "cases": len(cases), "mismatches": 0}))


if __name__ == "__main__":
    main()
