from pathlib import Path

HERE = Path(__file__).resolve().parent
s = (HERE / 'solution.cpp').read_text()
old = '    std::uint64_t exactSlotStale = 0;'
assert s.count(old) == 1
s = s.replace(old, old + '''
    bool exactSlotRegime = false;
    bool exactSlotRetired = false;
    std::uint64_t exactSlotStartedAt = 0;
    std::uint64_t exactSlotRetiredAt = 0;''')
begin = s.index('    bool exactSlotGrowthConfidence() const {')
end = s.index('    std::int64_t consumeExactAddress', begin)
s = s[:begin] + '''    bool exactSlotGrowthConfidence() {
        if (exactSlotRetired) return false;
        int adds = 0;
        for (int count : primalRecentRequests) adds += count;
        // Committed growth regime: keep object-size ownership coherent even
        // if a short rank window fluctuates. Retire on observed demand drift
        // or loss of net growth; no future trace boundary is used.
        if (exactSlotRegime) {
            if (unitDominantRecentProfile() || adds <= primalRecentDeletes) {
                exactSlotRegime = false;
                exactSlotRetired = true;
                exactSlotRetiredAt = primalStep + 1;
                return false;
            }
            return true;
        }
        if (activePipeCount < 128 || recentLengths.size() < 128 ||
            recentDeleteRanksPermille.size() < 48 || unitDominantRecentProfile()) {
            return false;
        }
        std::size_t young = 0;
        for (int rank : recentDeleteRanksPermille) if (rank <= 50) ++young;
        if (young * 100 < recentDeleteRanksPermille.size() * 80 ||
            adds <= primalRecentDeletes) return false;
        exactSlotRegime = true;
        exactSlotStartedAt = primalStep + 1;
        return true;
    }

''' + s[end:]
old = '                      << " stale=" << allocator.exactSlotStale << \'\\n\';'
assert s.count(old) == 1
s = s.replace(old, '''                      << " stale=" << allocator.exactSlotStale
                      << " regime_start=" << allocator.exactSlotStartedAt
                      << " retired_at=" << allocator.exactSlotRetiredAt << '\\n';''')
(HERE / 'sticky_solution.cpp').write_text(s)
print(HERE / 'sticky_solution.cpp')
