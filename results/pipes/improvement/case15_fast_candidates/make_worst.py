from pathlib import Path
p = Path('results/pipes/improvement/case15_fast_candidates/source/fragmented_worst_fit.cpp')
s = Path('results/pipes/final/solution.cpp').read_text()
s = s.replace('    std::int64_t trenchLength = 0;\n',
              '    std::int64_t trenchLength = 0;\n    std::int64_t activeLength = 0;\n')
s = s.replace('        ++activePipeCount;\n        ++lengthOccurrenceCount[static_cast<std::size_t>(length)];\n',
              '        ++activePipeCount;\n        activeLength += length;\n        ++lengthOccurrenceCount[static_cast<std::size_t>(length)];\n')
s = s.replace('        --activePipeCount;\n        addFreeGap(pipe.start, pipe.start + pipe.length, pipe.sizeCohort);\n',
              '        --activePipeCount;\n        activeLength -= pipe.length;\n        addFreeGap(pipe.start, pipe.start + pipe.length, pipe.sizeCohort);\n')
anchor = '    StartIter bestFittingGapFromSet(\n'
helper = '''    bool fragmentedStateForWorstFit() const {
        if (freeByStart.size() < 256 || freeBySize.empty()) return false;
        const std::int64_t totalFree = trenchLength - activeLength;
        const std::int64_t largestGap = freeBySize.rbegin()->first;
        return totalFree >= 8 * largestGap;
    }

    StartIter largestFittingGapFromSet(
        const std::set<std::pair<std::int64_t, std::int64_t>>& gaps,
        int length,
        bool highSide) {
        if (gaps.empty()) return freeByStart.end();
        const std::int64_t size = gaps.rbegin()->first;
        if (size < length) return freeByStart.end();
        const auto first = gaps.lower_bound({size,
            std::numeric_limits<std::int64_t>::min()});
        const auto after = gaps.upper_bound({size,
            std::numeric_limits<std::int64_t>::max()});
        const std::int64_t start = highSide ? std::prev(after)->second : first->second;
        return freeByStart.find(start);
    }

'''
assert s.count(anchor) == 1
s = s.replace(anchor, helper + anchor)
old = '''        auto it = gaps.lower_bound({length, 0});
        if (it == gaps.end()) return freeByStart.end();
        if (recentLengths.empty()) return freeByStart.find(it->second);
'''
new = '''        auto it = gaps.lower_bound({length, 0});
        if (it == gaps.end()) return freeByStart.end();
        if (fragmentedStateForWorstFit())
            return largestFittingGapFromSet(gaps, length, highSide);
        if (recentLengths.empty()) return freeByStart.find(it->second);
'''
assert s.count(old) == 1
p.write_text(s.replace(old, new))
