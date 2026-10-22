from pathlib import Path
import hashlib,json
D=Path(__file__).resolve().parent;P=D.parents[1]
s=(P/'baseline/solution.cpp').read_text().replace('#include <utility>','#include <utility>\n#include <tuple>')
a,b=s.split('class Allocator {',1)
def rep(old,new):
 global b
 assert b.count(old)==1,(old,b.count(old));b=b.replace(old,new)
rep('public:\n','''public:
    std::uint64_t releaseEpoch = 0;
    std::uint64_t recencyDifferentSelections = 0;
    std::map<std::int64_t, std::uint64_t> gapFreedAt;
    std::set<std::tuple<std::int64_t, std::uint64_t, std::int64_t>> freeBySizeAge;
''')
rep('        addFreeGap(pipe.start, pipe.start + pipe.length, pipe.sizeCohort);','        addFreeGap(pipe.start, pipe.start + pipe.length, pipe.sizeCohort, ++releaseEpoch);')
rep('''        auto it = gaps.lower_bound({length, 0});
        if (it == gaps.end()) return freeByStart.end();''','''        // LIFO free lists use observed free recency, not predicted lifetime.
        // At this scale the parent MC is already disabled, so no forecast
        // silently uses a different recycler policy.
        const bool recycleRecent = !parityCohortMode &&
            activePipeCount > kMcMaxActivePipes && hasLifoDeletionConfidence();
        auto it = gaps.lower_bound({length, 0});
        if (it == gaps.end()) return freeByStart.end();''')
rep('''        while (it != gaps.end()) {
            const std::int64_t gapLength = it->first;''','''        while (it != gaps.end()) {
            const std::int64_t gapLength = it->first;
            std::int64_t representativeStart = it->second;
            if (recycleRecent) {
                auto age = freeBySizeAge.upper_bound({gapLength,
                    std::numeric_limits<std::uint64_t>::max(),
                    std::numeric_limits<std::int64_t>::max()});
                --age;
                representativeStart = std::get<2>(*age);
            }''')
rep('''                 ((highSide && it->second > best->first) ||
                  (!highSide && it->second < best->first)))) {''','''                 ((highSide && representativeStart > best->first) ||
                  (!highSide && representativeStart < best->first)))) {''')
rep('                best = freeByStart.find(it->second);','                best = freeByStart.find(representativeStart);')
rep('''        return best;
    }

    bool hasSameLengthRecentRun''','''        if (recycleRecent && best != freeByStart.end()) {
            const auto first = gaps.lower_bound({best->second - best->first, 0});
            if (first->second != best->first) ++recencyDifferentSelections;
        }
        return best;
    }

    bool hasSameLengthRecentRun''')
rep('''        const int cohort = gapCohort.at(start);
        const std::int64_t placementStart = highSide''','''        const int cohort = gapCohort.at(start);
        const std::uint64_t freedAt = gapFreedAt.at(start);
        const std::int64_t placementStart = highSide''')
rep('''        if (start < placementStart) addFreeGap(start, placementStart, cohort);
        const std::int64_t placementEnd = placementStart + static_cast<std::int64_t>(length);
        if (placementEnd < end) addFreeGap(placementEnd, end, cohort);''','''        if (start < placementStart) addFreeGap(start, placementStart, cohort, freedAt);
        const std::int64_t placementEnd = placementStart + static_cast<std::int64_t>(length);
        if (placementEnd < end) addFreeGap(placementEnd, end, cohort, freedAt);''')
rep('''        freeBySize.erase({gapLength, start});''','''        freeBySizeAge.erase({gapLength, gapFreedAt.at(start), start});
        gapFreedAt.erase(start);
        freeBySize.erase({gapLength, start});''')
rep('''    void addFreeGap(std::int64_t start, std::int64_t end, int cohort) {''','''    void addFreeGap(std::int64_t start, std::int64_t end, int cohort,
                    std::uint64_t freedAt = 0) {''')
rep('''                if (gapCohort.at(previous->first) != cohort) cohort = -1;
                start = previous->first;''','''                if (gapCohort.at(previous->first) != cohort) cohort = -1;
                freedAt = std::max(freedAt, gapFreedAt.at(previous->first));
                start = previous->first;''')
rep('''            if (gapCohort.at(it->first) != cohort) cohort = -1;
            end = std::max(end, it->second);''','''            if (gapCohort.at(it->first) != cohort) cohort = -1;
            freedAt = std::max(freedAt, gapFreedAt.at(it->first));
            end = std::max(end, it->second);''')
rep('''        freeBySize.emplace(gapLength, start);
        gapCohort.emplace(start, cohort);''','''        freeBySize.emplace(gapLength, start);
        freeBySizeAge.emplace(gapLength, freedAt, start);
        gapFreedAt.emplace(start, freedAt);
        gapCohort.emplace(start, cohort);''')
rep('''        if (command == 0) {
#if defined(MC_ROLLOUT_DIAGNOSTICS)''','''        if (command == 0) {
            std::cerr << "recency_different_selections="
                      << allocator.recencyDifferentSelections << '\\n';
#if defined(MC_ROLLOUT_DIAGNOSTICS)''')
s=a+'class Allocator {'+b;(D/'candidate.cpp').write_text(s)
(D/'design.json').write_text(json.dumps(dict(hypothesis='Recent free first among equal-size/equal-cost gaps at large near-LIFO scale. Split remnants inherit observed release age; merges use latest component release. Untouched tail has age zero. No future lifetime prediction.',source_sha256=hashlib.sha256(s.encode()).hexdigest(),activation='existing LIFO confidence, active>existing MC limit4096, no parity cohort',screen='one full Open15; no threshold/seed sweep'),indent=2))
