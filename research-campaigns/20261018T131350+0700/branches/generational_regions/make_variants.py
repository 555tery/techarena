from pathlib import Path
import sys

branch = Path(__file__).resolve().parent
campaign = branch.parents[1]
base = campaign / 'baseline/solution.cpp'
source = base.read_text()

def replace_once(text, old, new, label):
    count = text.count(old)
    if count != 1:
        raise SystemExit(f'{label}: expected one match, found {count}')
    return text.replace(old, new, 1)

# Add one compile-time width so only the epoch size varies across the screen.
source = replace_once(source,
'''[[maybe_unused]] constexpr std::int64_t kMcMinimumMeanSavingM = 1;''',
'''[[maybe_unused]] constexpr std::int64_t kMcMinimumMeanSavingM = 1;
#ifndef GENERATIONAL_REGION_WINDOW
#define GENERATIONAL_REGION_WINDOW 2048
#endif
constexpr int kBirthRegionWindow = GENERATIONAL_REGION_WINDOW;''',
'window constant')

source = replace_once(source,
'''struct Pipe {
    std::int64_t start = 0;
    int length = 0;
    bool active = false;
    int sizeCohort = 0;
};''',
'''struct Pipe {
    std::int64_t start = 0;
    int length = 0;
    bool active = false;
    int sizeCohort = 0;
    int birthRegion = -1;
};''',
'Pipe metadata')

start = source.index('class Allocator {')
pre, alloc = source[:start], source[start:]

def ar(old, new, label):
    global alloc
    alloc = replace_once(alloc, old, new, label)

ar('''    std::map<std::int64_t, int> gapCohort;
    std::array<std::set<std::pair<std::int64_t, std::int64_t>>, 2> freeBySizeCohort;''',
'''    std::map<std::int64_t, int> gapCohort;
    std::map<std::int64_t, int> gapRegion;
    std::map<int, std::array<std::set<std::pair<std::int64_t, std::int64_t>>, 3>>
        freeByRegionSize;
    std::array<std::set<std::pair<std::int64_t, std::int64_t>>, 2> freeBySizeCohort;''',
'region indexes')

ar('''        const int sizeCohort = static_cast<int>(
            lengthOccurrenceCount[static_cast<std::size_t>(length)] % 2);
        if (activePipeCount > kMcMaxActivePipes) lifoLaneDisabledForScale = true;''',
'''        const int sizeCohort = static_cast<int>(
            lengthOccurrenceCount[static_cast<std::size_t>(length)] % 2);
        const int birthRegion = (static_cast<int>(pipes.size()) - 1) / kBirthRegionWindow;
        if (activePipeCount > kMcMaxActivePipes) lifoLaneDisabledForScale = true;''',
'birth region in place')

ar('''            pipes.push_back(Pipe{start, length, true, sizeCohort});''',
'''            pipes.push_back(Pipe{start, length, true, sizeCohort, birthRegion});''',
'slab pipe birth tag')
ar('''                if (occupiedEnd < trenchLength) addFreeGap(occupiedEnd, trenchLength, -1);''',
'''                if (occupiedEnd < trenchLength) addFreeGap(occupiedEnd, trenchLength, -1, -1);''',
'slab gap region')

ar('''        if (predictedNextClass > length &&
            ((static_cast<int>(pipes.size()) & 1) != predictedDeletedParity)) {
            const auto projectedChoice = chooseCounterfactualCapacityGap(
                length, predictedNextClass, highSide, sizeCohort, gap);
            if (projectedChoice.first != freeByStart.end()) {
                gap = projectedChoice.first;
                highSide = projectedChoice.second;
                counterfactualCapacityChoice = true;
            }
        }
        if (gap != freeByStart.end()) {''',
'''        if (predictedNextClass > length &&
            ((static_cast<int>(pipes.size()) & 1) != predictedDeletedParity)) {
            const auto projectedChoice = chooseCounterfactualCapacityGap(
                length, predictedNextClass, highSide, sizeCohort, gap);
            if (projectedChoice.first != freeByStart.end()) {
                gap = projectedChoice.first;
                highSide = projectedChoice.second;
                counterfactualCapacityChoice = true;
            }
        }
        bool birthRegionRoute = false;
        if (gap == freeByStart.end() || gapRegion.at(gap->first) != birthRegion) {
            const auto regional = bestFittingGapInRegion(
                length, highSide, sizeCohort, birthRegion);
            if (regional != freeByStart.end()) {
                gap = regional;
                birthRegionRoute = true;
            }
        }
        if (gap != freeByStart.end()) {''',
'birth region route')

ar('''            const std::int64_t selectedStart = (additiveNextAlignment ||
                counterfactualCapacityChoice)
                ? gap->first
                : chooseGapWithRollout(length, highSide, sizeCohort, gap);''',
'''            const std::int64_t selectedStart = (additiveNextAlignment ||
                counterfactualCapacityChoice || birthRegionRoute)
                ? gap->first
                : chooseGapWithRollout(length, highSide, sizeCohort, gap);''',
'regional route bypasses local rollout')

ar('''            const std::int64_t tailLength = trenchLength - tailStart;
            const std::int64_t deficit = std::max<std::int64_t>(0, length - tailLength);''',
'''            const std::int64_t tailLength = trenchLength - tailStart;
            const std::int64_t deficit = std::max<std::int64_t>(0, length - tailLength);
            const int oldTailRegion = tail == freeByStart.end()
                ? -1 : gapRegion.at(tail->first);
            const int remainderRegion = (tail == freeByStart.end() || preserveForeignTail)
                ? birthRegion
                : (oldTailRegion == birthRegion ? birthRegion : -1);''',
'growth-tail region')

ar('''                if (tailStart < start) addFreeGap(tailStart, start, tailCohort);''',
'''                if (tailStart < start) addFreeGap(tailStart, start, tailCohort, remainderRegion);''',
'growth lower remainder')
ar('''                    addFreeGap(remainderStart, trenchLength, tailCohort);''',
'''                    addFreeGap(remainderStart, trenchLength, tailCohort, remainderRegion);''',
'growth upper remainder')

ar('''        pipes.push_back(Pipe{start, length, true, sizeCohort});''',
'''        pipes.push_back(Pipe{start, length, true, sizeCohort, birthRegion});''',
'ordinary pipe birth tag')
ar('''        addFreeGap(pipe.start, pipe.start + pipe.length, pipe.sizeCohort);''',
'''        addFreeGap(pipe.start, pipe.start + pipe.length, pipe.sizeCohort,
                   pipe.birthRegion);''',
'pipe release tag')

# Region-aware best fit is used only when the global baseline-selected gap belongs
# to a different generation. The existing gap score and size-cohort preferences
# are reused unchanged.
ar('''    StartIter bestFittingGap(int length, bool highSide, int sizeCohort) {
        if (parityCohortMode) {''',
'''    StartIter bestFittingGapInRegion(int length, bool highSide, int sizeCohort,
                                      int birthRegion) {
        const auto found = freeByRegionSize.find(birthRegion);
        if (found == freeByRegionSize.end()) return freeByStart.end();
        const auto& groups = found->second;
        if (parityCohortMode) {
            StartIter preferred = bestFittingGapFromSet(
                groups[static_cast<std::size_t>(sizeCohort)], length, highSide);
            if (preferred != freeByStart.end()) return preferred;
            return bestFittingGapFromSet(groups[2], length, highSide);
        }
        StartIter best = freeByStart.end();
        std::int64_t bestScore = std::numeric_limits<std::int64_t>::max();
        for (const auto& group : groups) {
            const StartIter candidate = bestFittingGapFromSet(group, length, highSide);
            if (candidate == freeByStart.end()) continue;
            const std::int64_t candidateScore =
                scoreGap(candidate->second - candidate->first, length);
            if (candidateScore < bestScore ||
                (candidateScore == bestScore && best != freeByStart.end() &&
                 ((highSide && candidate->first > best->first) ||
                  (!highSide && candidate->first < best->first)))) {
                best = candidate;
                bestScore = candidateScore;
            }
        }
        return best;
    }

    StartIter bestFittingGap(int length, bool highSide, int sizeCohort) {
        if (parityCohortMode) {''',
'regional best-fit helper')

# Replace only the main Allocator gap maintenance functions.
ar('''    std::int64_t consumeAtSide(StartIter it, int length, bool highSide) {
        const std::int64_t start = it->first;
        const std::int64_t end = it->second;
        const int cohort = gapCohort.at(start);''',
'''    std::int64_t consumeAtSide(StartIter it, int length, bool highSide) {
        const std::int64_t start = it->first;
        const std::int64_t end = it->second;
        const int cohort = gapCohort.at(start);
        const int region = gapRegion.at(start);''',
'consume carries region')
ar('''        if (start < placementStart) addFreeGap(start, placementStart, cohort);
        const std::int64_t placementEnd = placementStart + static_cast<std::int64_t>(length);
        if (placementEnd < end) addFreeGap(placementEnd, end, cohort);''',
'''        if (start < placementStart) addFreeGap(start, placementStart, cohort, region);
        const std::int64_t placementEnd = placementStart + static_cast<std::int64_t>(length);
        if (placementEnd < end) addFreeGap(placementEnd, end, cohort, region);''',
'consumed split carries region')

ar('''    void eraseGap(StartIter it) {
        const std::int64_t start = it->first;
        const std::int64_t end = it->second;
        const std::int64_t gapLength = end - start;
        const int cohort = gapCohort.at(start);
        freeBySize.erase({gapLength, start});''',
'''    void eraseGap(StartIter it) {
        const std::int64_t start = it->first;
        const std::int64_t end = it->second;
        const std::int64_t gapLength = end - start;
        const int cohort = gapCohort.at(start);
        const int region = gapRegion.at(start);
        freeBySize.erase({gapLength, start});''',
'erase region index prelude')
ar('''        } else {
            freeBySizeShared.erase({gapLength, start});
        }
        gapCohort.erase(start);
        freeByStart.erase(it);
    }

    void addFreeGap(std::int64_t start, std::int64_t end, int cohort) {''',
'''        } else {
            freeBySizeShared.erase({gapLength, start});
        }
        if (region >= 0) {
            auto regional = freeByRegionSize.find(region);
            if (regional != freeByRegionSize.end()) {
                const std::size_t group = cohort >= 0 && cohort <= 1
                    ? static_cast<std::size_t>(cohort) : 2U;
                regional->second[group].erase({gapLength, start});
                const bool empty = regional->second[0].empty() &&
                    regional->second[1].empty() && regional->second[2].empty();
                if (empty) freeByRegionSize.erase(regional);
            }
        }
        gapCohort.erase(start);
        gapRegion.erase(start);
        freeByStart.erase(it);
    }

    void addFreeGap(std::int64_t start, std::int64_t end, int cohort, int region) {''',
'erase region index and signature')

ar('''            if (previous->second >= start) {
                if (gapCohort.at(previous->first) != cohort) cohort = -1;
                start = previous->first;''',
'''            if (previous->second >= start) {
                if (gapCohort.at(previous->first) != cohort) cohort = -1;
                if (gapRegion.at(previous->first) != region) region = -1;
                start = previous->first;''',
'merge previous region')
ar('''        while (it != freeByStart.end() && it->first <= end) {
            if (gapCohort.at(it->first) != cohort) cohort = -1;
            end = std::max(end, it->second);''',
'''        while (it != freeByStart.end() && it->first <= end) {
            if (gapCohort.at(it->first) != cohort) cohort = -1;
            if (gapRegion.at(it->first) != region) region = -1;
            end = std::max(end, it->second);''',
'merge next region')
ar('''        freeByStart.emplace(start, end);
        const std::int64_t gapLength = end - start;
        freeBySize.emplace(gapLength, start);
        gapCohort.emplace(start, cohort);
        if (cohort >= 0 && cohort <= 1) {''',
'''        freeByStart.emplace(start, end);
        const std::int64_t gapLength = end - start;
        freeBySize.emplace(gapLength, start);
        gapCohort.emplace(start, cohort);
        gapRegion.emplace(start, region);
        if (region >= 0) {
            const std::size_t group = cohort >= 0 && cohort <= 1
                ? static_cast<std::size_t>(cohort) : 2U;
            freeByRegionSize[region][group].emplace(gapLength, start);
        }
        if (cohort >= 0 && cohort <= 1) {''',
'add region index')

source = pre + alloc

widths = [int(arg) for arg in sys.argv[1:]] or [512, 2048, 8192]
for width in widths:
    if width < 128 or width > 200000:
        raise SystemExit(f'invalid region window: {width}')
    variant = source.replace('#define GENERATIONAL_REGION_WINDOW 2048',
                             f'#define GENERATIONAL_REGION_WINDOW {width}')
    if f'#define GENERATIONAL_REGION_WINDOW {width}' not in variant:
        raise SystemExit(f'could not set region window {width}')
    target = branch / f'solution-window-{width}.cpp'
    target.write_text(variant)
    print(target.name)
