"""Use completed long runs as causal evidence for an earlier repeated-size route."""
import hashlib
from pathlib import Path
ROOT = Path(__file__).resolve().parents[2]
parent = ROOT / 'releases/988927c690b4034f3a26c839ee00bc2c0d0956e6ea9f5b6369c9d45e961242e4/solution.cpp'
assert hashlib.sha256(parent.read_bytes()).hexdigest() == '988927c690b4034f3a26c839ee00bc2c0d0956e6ea9f5b6369c9d45e961242e4'
text = parent.read_text()
helper = '''bool hasLearnedRepeatedSizeRun(const std::deque<int>& history, int length) {
    auto it = history.rbegin();
    std::size_t current = 0;
    while (it != history.rend() && *it == length) {
        if (++current >= kSameLengthRightRun) return true;
        ++it;
    }
    // The current request must confirm an already observed repeat. Prior runs
    // are complete insertion-size runs; they contain no future observations.
    if (current == 0) return false;
    for (int previous = 0; previous < 2; ++previous) {
        if (it == history.rend()) return false;
        const int size = *it;
        std::size_t count = 0;
        while (it != history.rend() && *it == size) { ++count; ++it; }
        if (count < kSameLengthRightRun) return false;
    }
    return true;
}

'''
anchor = 'int predictNextGeometricSize(const std::deque<int>& history, int currentLength) {'
assert text.count(anchor) == 1
text = text.replace(anchor, helper + anchor, 1)
old = '''    bool hasSameLengthRecentRun(int length) const {
        if (recentLengths.size() < kSameLengthRightRun) return false;
        auto it = recentLengths.rbegin();
        for (std::size_t seen = 0; seen < kSameLengthRightRun; ++seen, ++it) {
            if (*it != length) return false;
        }
        return true;
    }
'''
assert text.count(old) == 2
text = text.replace(old, '''    bool hasSameLengthRecentRun(int length) const {
        return hasLearnedRepeatedSizeRun(recentLengths, length);
    }
''')
anchor = '    CensoredLifetimeModel lifetimeModel;\n'
assert text.count(anchor) == 1
text = text.replace(anchor, anchor + '    std::uint64_t earlyRepeatedSizeRoutes = 0;\n')
anchor = '        const bool sameSizeRun = hasSameLengthRecentRun(length);\n'
# Both simulator and allocator use the same predicate. Only the real allocator
# has observedRunCount and records activation diagnostics.
offset = text.index('class Allocator {')
prefix, allocator = text[:offset], text[offset:]
assert allocator.count(anchor) == 1
allocator = allocator.replace(anchor, anchor + '''        if (sameSizeRun && observedRunCount <= static_cast<int>(kSameLengthRightRun)) {
            ++earlyRepeatedSizeRoutes;
        }
''')
text = prefix + allocator
anchor = '            std::cerr << "recency_different_selections="\n'
assert text.count(anchor) == 1
text = text.replace(anchor, '''            std::cerr << "early_repeated_size_routes=" << allocator.earlyRepeatedSizeRoutes << '\\n';
''' + anchor)
destination = Path(__file__).with_name('solution.cpp')
assert not destination.exists()
destination.write_text(text)
print(hashlib.sha256(destination.read_bytes()).hexdigest())
