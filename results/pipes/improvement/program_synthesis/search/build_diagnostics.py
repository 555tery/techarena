#!/usr/bin/env python3
"""Create an instrumented copy of frozen tree #33 for gate-switch counts."""

from pathlib import Path

HERE = Path(__file__).resolve().parents[0].parent
SOURCE = HERE / "src/tree_033_simplified.cpp"
OUTPUT = HERE / "src/tree_033_diagnostics.cpp"


def main():
    source = SOURCE.read_text()
    source = source.replace(
        "    std::size_t mcRolloutsRun = 0;\n",
        "    std::size_t mcRolloutsRun = 0;\n"
        "#if defined(SYNTH_POLICY_DIAGNOSTICS)\n"
        "    std::size_t synthEligible = 0;\n"
        "    std::size_t synthAllowed = 0;\n"
        "    std::size_t synthSkipped = 0;\n"
        "    std::size_t synthGateFlips = 0;\n"
        "    bool synthGateSeen = false;\n"
        "    bool synthLastGate = false;\n"
        "#endif\n")
    source = source.replace(
        "        if (!synthesisTreeAllows(length, baselineGap)) return baselineGap->first;\n",
        "#if defined(SYNTH_POLICY_DIAGNOSTICS)\n"
        "        ++synthEligible;\n"
        "#endif\n"
        "        const bool synthAllow = synthesisTreeAllows(length, baselineGap);\n"
        "#if defined(SYNTH_POLICY_DIAGNOSTICS)\n"
        "        if (synthGateSeen && synthAllow != synthLastGate) ++synthGateFlips;\n"
        "        synthGateSeen = true;\n"
        "        synthLastGate = synthAllow;\n"
        "        if (synthAllow) ++synthAllowed; else ++synthSkipped;\n"
        "#endif\n"
        "        if (!synthAllow) return baselineGap->first;\n")
    source = source.replace(
        "#if defined(MC_ROLLOUT_DIAGNOSTICS)\n",
        "#if defined(SYNTH_POLICY_DIAGNOSTICS)\n"
        "            std::cerr << \"synth_eligible=\" << allocator.synthEligible\n"
        "                      << \" synth_allowed=\" << allocator.synthAllowed\n"
        "                      << \" synth_skipped=\" << allocator.synthSkipped\n"
        "                      << \" synth_gate_flips=\" << allocator.synthGateFlips << '\\n';\n"
        "#endif\n"
        "#if defined(MC_ROLLOUT_DIAGNOSTICS)\n")
    OUTPUT.write_text(source)
    print(OUTPUT)


if __name__ == "__main__":
    main()
