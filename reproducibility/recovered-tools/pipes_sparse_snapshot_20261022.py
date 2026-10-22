"""Pure Cangjie source transformer. Does not read or write Cangjie files.

Use apply(source_text); sparse DP support is frozen with the rate snapshot.
Dense paths, schedule, and floating-point expression bodies are preserved.
"""
import re
import textwrap


def _once(source, old, new):
    if source.count(old) != 1:
        raise ValueError(f"Expected one source anchor: {old[:100]!r}")
    return source.replace(old, new, 1)


def _closing_brace(source, opening):
    # Called only on the numerical DP blocks, which contain no brace literals.
    depth = 0
    for index in range(opening, len(source)):
        if source[index] == "{":
            depth += 1
        elif source[index] == "}":
            depth -= 1
            if depth == 0:
                return index
    raise ValueError("Unclosed numerical block")


def _patch_method(source, method, expected_branches, rate_pointer):
    signature = f"func {method}("
    if source.count(signature) != 1:
        raise ValueError(f"Missing or duplicate method: {method}")
    start = source.index(signature)
    end = source.index("\n    }", start) + len("\n    }")
    part = source[start:end]
    pointer_anchor = f"            let {rate_pointer} = causalRequestRate.borrowData()"
    part = _once(part, pointer_anchor, pointer_anchor + "\n" +
                 "            let snapshotActiveLengths = causalActiveLengths.borrowData()\n" +
                 "            let snapshotActiveCount = causalActiveLengthCount")
    pattern = re.compile(r"(?m)^( +)if \((g|gap) >= 40 && lastRequest > 8\) \{")
    matches = list(pattern.finditer(part))
    if len(matches) != expected_branches:
        raise ValueError(f"Unexpected dense branches in {method}: {len(matches)}")
    # Reverse edits keep the original match offsets valid.
    for match in reversed(matches):
        indentation, gap = match.group(1), match.group(2)
        dense_end = _closing_brace(part, match.end() - 1)
        fallback = re.match(r" else \{\s*for \(request in firstRequest\.\.=top\) \{",
                            part[dense_end + 1:])
        if fallback is None:
            raise ValueError(f"Missing ascending fallback in {method}")
        loop_open = dense_end + 1 + fallback.end() - 1
        loop_end = _closing_brace(part, loop_open)
        # Copy the existing arithmetic body exactly, changing indentation only.
        body = textwrap.dedent(part[loop_open + 1:loop_end]).strip("\n")
        body = textwrap.indent(body, indentation + "        ")
        sparse = (
            indentation + "if (snapshotActiveCount <= 8) {\n" +
            indentation + "    for (supportIndex in 0..snapshotActiveCount) {\n" +
            indentation + "        let request = snapshotActiveLengths.read(supportIndex)\n" +
            indentation + f"        if (request > {gap}) {{ break }}\n" +
            body + "\n" +
            indentation + "    }\n" +
            indentation + "} else if (" + gap + " >= 40 && lastRequest > 8) {"
        )
        part = part[:match.start()] + sparse + part[match.end():]
    return source[:start] + part + source[end:]


def apply(source_text):
    """Return transformed text, or raise if the expected source shape differs.

    Independent of LAZY_SLAB/emission implementation. Intentionally not idempotent:
    applying twice raises rather than duplicating snapshot state or branches.
    """
    if "causalActiveLengthCount" in source_text:
        raise ValueError("Sparse snapshot patch already present")
    source = _once(
        source_text,
        "    private let causalRequestRate = FastFloatBuffer(41)",
        "    private let causalRequestRate = FastFloatBuffer(41)\n"
        "    private let causalActiveLengths = FastIntBuffer(41)\n"
        "    private var causalActiveLengthCount: Int64 = 0",
    )
    source = _once(
        source,
        "            causalRequestRate.fill(0.0)",
        "            causalRequestRate.fill(0.0)\n"
        "            let snapshotActiveLengths = causalActiveLengths.borrowData()\n"
        "            var snapshotActiveCount: Int64 = 0",
    )
    old_rate = "                rate.write(request, Float64(recentRequests.read(request)) / Float64(iMax(1, fitting)))"
    source = _once(
        source, old_rate,
        "                let snapshotRate = Float64(recentRequests.read(request)) / Float64(iMax(1, fitting))\n"
        "                rate.write(request, snapshotRate)\n"
        "                if (snapshotRate != 0.0) {\n"
        "                    snapshotActiveLengths.write(snapshotActiveCount, request)\n"
        "                    snapshotActiveCount++\n"
        "                }",
    )
    source = _once(
        source,
        "            let expiry = 2.0 * Float64(primalRecentDeletes) / Float64(iMax(1, activePipeCount))",
        "            causalActiveLengthCount = snapshotActiveCount\n"
        "            let expiry = 2.0 * Float64(primalRecentDeletes) / Float64(iMax(1, activePipeCount))",
    )
    source = _patch_method(source, "materializePrimalGapValues", 3, "rate")
    source = _patch_method(source, "rebuildCausalGapValues", 2, "requestRates")
    return source
