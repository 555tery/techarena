"""Pure candidate transformer: recycle a contiguous predicted-deleted band.

No files, compilation, imports of evaluation code, or solver runs on import.
Use incumbent RESERVATION_POLICY=1, LAZY_SLAB=1, REPLAY_GUARD=5.
The Cangjie input is the released guard-generalization source (lazy policy).
"""

def _once(source, old, new):
    count = source.count(old)
    if count != 1:
        raise ValueError(f'Anchor occurrence count {count}: {old[:120]!r}')
    return source.replace(old, new, 1)


def _method(source, begin, end, edits):
    if source.count(begin) != 1:
        raise ValueError(f'Method anchor is not unique: {begin!r}')
    a = source.index(begin)
    b = source.index(end, a)
    part = source[a:b]
    for old, new in edits:
        part = _once(part, old, new)
    return source[:a] + part + source[b:]


def apply_cpp(source):
    source = _once(source,
        '    std::int64_t cohortSlabBase = 0;',
        '    std::int64_t cohortSlabBase = 0;\n'
        '    std::int64_t cohortSlabDeletedBase = 0;\n'
        '    std::int64_t cohortSlabSurvivorBase = 0;')
    source = _method(source, '    void place(int length) {\n        lifetimeModel.advance();', '    void remove(std::int64_t pid) {', [
        ('                    start = cohortSlabBase +\n                        static_cast<std::int64_t>(cohortSlabDeletedUsed) * length;',
         '                    start = cohortSlabDeletedBase +\n                        static_cast<std::int64_t>(cohortSlabDeletedUsed) * length;'),
        ('                    start = cohortSlabBase +\n                        static_cast<std::int64_t>(cohortSlabDeleteCount +\n                                                  cohortSlabSurvivorUsed) * length;',
         '                    start = cohortSlabSurvivorBase +\n                        static_cast<std::int64_t>(cohortSlabSurvivorUsed) * length;'),
    ])
    source = _method(source, '    void releaseCohortReservation() {', '    void beginCohortSlab(int length) {', [
        ('const auto deletedBegin = cohortSlabBase +', 'const auto deletedBegin = cohortSlabDeletedBase +'),
        ('std::min(trenchLength,cohortSlabBase + std::int64_t(cohortSlabDeleteCount) * n) : cohortSlabBase + std::int64_t(cohortSlabDeleteCount) * n;',
         'std::min(trenchLength,cohortSlabDeletedBase + std::int64_t(cohortSlabDeleteCount) * n) : cohortSlabDeletedBase + std::int64_t(cohortSlabDeleteCount) * n;'),
        ('const auto survivorBegin = cohortSlabBase + std::int64_t(cohortSlabDeleteCount + cohortSlabSurvivorUsed) * n;',
         'const auto survivorBegin = cohortSlabSurvivorBase + std::int64_t(cohortSlabSurvivorUsed) * n;'),
    ])
    source = _method(source, '    void beginCohortSlab(int length) {', '    void recordObservation(const Observation& event) {', [
        ('        std::int64_t reusableCapacity = 0;', '''        // Reserve an existing compatible span for the predicted deleted half.
        // This lets survivors extend directly from the actual trench boundary.
        const int deletedSizeCohort = survivorSizeCohort ^ 1;
        const std::int64_t deletedBandLength = std::int64_t(deleteCount) * length;
        auto recycled = freeByStart.end();
        std::int64_t recycledLength = 0;
        for (auto it = freeByStart.begin(); it != freeByStart.end(); ++it) {
            const auto gapLength = it->second - it->first;
            if (gapLength < deletedBandLength) continue;
            const int owner = gapCohort.at(it->first);
            if (parityCohortMode && owner >= 0 && owner != deletedSizeCohort) continue;
            if (recycled == freeByStart.end() || gapLength < recycledLength) {
                recycled = it;
                recycledLength = gapLength;
            }
        }
        std::int64_t reusableCapacity = 0;'''),
        ('            const std::int64_t gapCapacity = (gapEnd - gapStart) / length;',
         '            const std::int64_t gapCapacity = (gapEnd - gapStart) / length -\n'
         '                (recycled != freeByStart.end() && gapStart == recycled->first ? deleteCount : 0);'),
        ('        const int tailPipeCount = expectedCount - survivorGapCount;',
         '        const int tailPipeCount = expectedCount - survivorGapCount -\n'
         '            (recycled != freeByStart.end() ? deleteCount : 0);'),
        ('        cohortSlabActive = true;\n        cohortSlabExpanded = false;', '''        const bool hasRecycledBand = recycled != freeByStart.end();
        cohortSlabDeletedBase = hasRecycledBand ? recycled->first : trenchLength;
        cohortSlabSurvivorBase = trenchLength + (hasRecycledBand ? 0 : deletedBandLength);
        if (hasRecycledBand) {
            const auto start = recycled->first;
            const auto end = recycled->second;
            const int owner = gapCohort.at(start);
            const auto freedAt = gapFreedAt.at(start);
            eraseGap(recycled);
            addFreeGap(start + deletedBandLength, end, owner, freedAt);
        }
        cohortSlabActive = true;
        // A recycled reservation is already physical even before the first dig.
        cohortSlabExpanded = hasRecycledBand;'''),
    ])
    return source


def apply_cj(source):
    source = _once(source,
        '    public var cohortSlabBase: Int64 = 0',
        '    public var cohortSlabBase: Int64 = 0\n'
        '    public var cohortSlabDeletedBase: Int64 = 0\n'
        '    public var cohortSlabSurvivorBase: Int64 = 0')
    source = _method(source, '    public func place(length: Int64): Unit {\n        lifetimeModel.advance()', '    public func remove(pid: Int64): Unit {', [
        ('start = cohortSlabBase + cohortSlabDeletedUsed * length',
         'start = cohortSlabDeletedBase + cohortSlabDeletedUsed * length'),
        ('start = cohortSlabBase + (cohortSlabDeleteCount + cohortSlabSurvivorUsed) * length',
         'start = cohortSlabSurvivorBase + cohortSlabSurvivorUsed * length'),
    ])
    source = _method(source, '    private func releaseCohortReservation(): Unit {', '    public func beginCohortSlab(length: Int64): Unit {', [
        ('let deletedBegin = cohortSlabBase +', 'let deletedBegin = cohortSlabDeletedBase +'),
        ('let deletedEnd = iMin(trenchLength, cohortSlabBase + cohortSlabDeleteCount * length)',
         'let deletedEnd = iMin(trenchLength, cohortSlabDeletedBase + cohortSlabDeleteCount * length)'),
        ('let survivorBegin = cohortSlabBase + (cohortSlabDeleteCount + cohortSlabSurvivorUsed) * length',
         'let survivorBegin = cohortSlabSurvivorBase + cohortSlabSurvivorUsed * length'),
    ])
    source = _method(source, '    public func beginCohortSlab(length: Int64): Unit {', '    public func recordObservation(event: Observation): Unit {', [
        ('        var reusableCapacity: Int64 = 0', '''        // Recycle one compatible contiguous band for predicted deletions.
        let deletedSizeCohort = survivorSizeCohort ^ 1
        let deletedBandLength = deleteCount * length
        var recycled: Int64 = 0
        var recycledLength: Int64 = 0
        var scan = freeByStart.first()
        while (scan != 0) {
            let gapLength = freeByStart.value(scan) - freeByStart.keyA(scan)
            let owner = gapOwner[scan]
            if (gapLength >= deletedBandLength && (!parityCohortMode || owner < 0 || owner == deletedSizeCohort)) {
                if (recycled == 0 || gapLength < recycledLength) {
                    recycled = scan
                    recycledLength = gapLength
                }
            }
            scan = freeByStart.next(scan)
        }
        var reusableCapacity: Int64 = 0'''),
        ('            reusableCapacity = iMin(survivorCount, reusableCapacity + (gapEnd - gapStart) / length)',
         '            let gapCapacity = (gapEnd - gapStart) / length - (if (it == recycled) { deleteCount } else { 0 })\n'
         '            reusableCapacity = iMin(survivorCount, reusableCapacity + gapCapacity)'),
        ('        let tailPipeCount = expectedCount - survivorGapCount',
         '        let tailPipeCount = expectedCount - survivorGapCount - (if (recycled != 0) { deleteCount } else { 0 })'),
        ('        cohortSlabActive = true\n        cohortSlabExpanded = false', '''        let hasRecycledBand = recycled != 0
        cohortSlabDeletedBase = if (hasRecycledBand) { freeByStart.keyA(recycled) } else { trenchLength }
        cohortSlabSurvivorBase = trenchLength + (if (hasRecycledBand) { 0 } else { deletedBandLength })
        if (hasRecycledBand) {
            let start = freeByStart.keyA(recycled)
            let end = freeByStart.value(recycled)
            let owner = gapOwner[recycled]
            let freedAt = gapRelease[recycled]
            eraseGap(recycled)
            addFreeGap(start + deletedBandLength, end, owner, freedAt)
        }
        cohortSlabActive = true
        // Existing reserved space must be released even if no dig occurs.
        cohortSlabExpanded = hasRecycledBand'''),
    ])
    return source
