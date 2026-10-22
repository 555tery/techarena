"""Pure source transforms for current-positive-conditioned historical MC blocks.

No file access or execution on import. Source blocks remain entirely historical;
only the matching query virtually appends the already known current request.
This is a policy hypothesis, not an output-equivalent optimization.
"""


def _once(text, old, new):
    if text.count(old) != 1:
        raise ValueError(f"Expected one old anchor: {old[:110]!r}")
    return text.replace(old, new, 1)


def _method(text, start, end, replacements):
    if text.count(start) != 1:
        raise ValueError(f"Missing or duplicate method anchor: {start!r}")
    begin = text.index(start)
    finish = text.index(end, begin)
    part = text[begin:finish]
    for old, new in replacements:
        part = _once(part, old, new)
    return text[:begin] + part + text[finish:]


def apply_cpp(source):
    """Patch C++ core; all RNG, budget, block-source and fallback code stays."""
    source = _method(
        source,
        "    std::array<Observation, kMcDepth> sampleScenario(std::uint32_t& randomState) const {",
        "    RolloutState makeRolloutState() const {",
        [
            (
                "sampleScenario(std::uint32_t& randomState) const {",
                "sampleScenario(std::uint32_t& randomState, int currentLength) const {",
            ),
            (
                "        const std::size_t n = observedHistory.size();",
                "        const std::size_t n = observedHistory.size();\n"
                "        const Observation currentObservation{1, currentLength};",
            ),
            (
                "            const std::size_t contextBegin = n - context;",
                "            const std::size_t contextBegin = n + 1 - context;",
            ),
            (
                "                    if (!observationKeyEqual(observedHistory[contextBegin + offset],\n"
                "                                             observedHistory[start - context + offset])) {",
                "                    const std::size_t queryIndex = contextBegin + offset;\n"
                "                    const Observation& queryObservation = queryIndex == n\n"
                "                        ? currentObservation : observedHistory[queryIndex];\n"
                "                    if (!observationKeyEqual(queryObservation,\n"
                "                                             observedHistory[start - context + offset])) {",
            ),
        ],
    )
    return _once(
        source,
        "            scenarios[trial] = sampleScenario(randomState);",
        "            scenarios[trial] = sampleScenario(randomState, length);",
    )


def apply_cj(source):
    """Patch Cangjie core; RNG remains the existing per-allocator field."""
    source = _method(
        source,
        "    public func sampleScenario(): Array<Observation> {",
        "    public func makeRolloutState(): RolloutState {",
        [
            (
                "    public func sampleScenario(): Array<Observation> {",
                "    public func sampleScenario(currentLength: Int64): Array<Observation> {",
            ),
            (
                "        let n = observedHistory.size",
                "        let n = observedHistory.size\n"
                "        let currentObservation = Observation(1, currentLength)",
            ),
            (
                "            let contextBegin = n - context",
                "            let contextBegin = n + 1 - context",
            ),
            (
                "                    if (!observationKeyEqual(observedHistory.get(contextBegin + offset), observedHistory.get(start - context + offset))) { matches = false; break }",
                "                    let queryIndex = contextBegin + offset\n"
                "                    let queryObservation = if (queryIndex == n) { currentObservation } else { observedHistory.get(queryIndex) }\n"
                "                    if (!observationKeyEqual(queryObservation, observedHistory.get(start - context + offset))) { matches = false; break }",
            ),
        ],
    )
    return _once(
        source,
        "        for (trial in 0..kMcTrials) { scenarios[trial] = sampleScenario() }",
        "        for (trial in 0..kMcTrials) { scenarios[trial] = sampleScenario(length) }",
    )
