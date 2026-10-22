"""Last predeclared hypothesis: confidence-gated size-transition demand."""
import datetime, json
from build_primary import HERE, build, sha

s=(HERE/'candidates/baseline/solution.cpp').read_text()
def patch(a,b):
    global s
    assert s.count(a)==1,a
    s=s.replace(a,b)

patch('    std::array<int, 256> primalEventHistory{};', '''    // Insertion-sequence transitions are observations, not public identities.
    std::array<std::array<std::uint16_t, 41>, 41> demandTransitions{};
    std::array<int, 41> demandTransitionTotals{};
    std::deque<std::pair<int,int>> demandTransitionHistory;
    std::deque<unsigned char> demandPredictionHistory;
    int demandPredictionHits = 0;
    int lastDemandLength = 0;
    int primalConditionLength = 0;
    int primalModelCondition = 0;
    std::array<int, 256> primalEventHistory{};''')

patch('    void recordPrimalEvent(int event) {\n        if (event > 0) lifetimeModel.observeBirth(event);', '''    bool conditionalDemandReady(int length) const {
        const int total = demandTransitionTotals[length];
        if (total < 16 || demandPredictionHistory.size() < 32 ||
            demandPredictionHits * 5 < int(demandPredictionHistory.size()) * 4) return false;
        const auto& row = demandTransitions[length];
        return int(*std::max_element(row.begin()+1,row.end())) * 5 >= total * 4;
    }

    void recordDemandTransition(int length) {
        if (lastDemandLength > 0) {
            auto& row = demandTransitions[lastDemandLength];
            // Score each prediction before observing its answer. Confidence
            // expires through a bounded window when the pattern is broken.
            if (demandTransitionTotals[lastDemandLength] >= 8) {
                const int predicted = int(std::max_element(row.begin()+1,row.end())-row.begin());
                const unsigned char hit = predicted == length;
                demandPredictionHistory.push_back(hit);demandPredictionHits += hit;
                if (demandPredictionHistory.size() > 64) {
                    demandPredictionHits -= demandPredictionHistory.front();
                    demandPredictionHistory.pop_front();
                }
            }
            ++row[length];++demandTransitionTotals[lastDemandLength];
            demandTransitionHistory.emplace_back(lastDemandLength,length);
            if (demandTransitionHistory.size() > 2048) {
                const auto expired = demandTransitionHistory.front();
                demandTransitionHistory.pop_front();
                --demandTransitions[expired.first][expired.second];
                --demandTransitionTotals[expired.first];
            }
        }
        lastDemandLength = length;
    }

    void recordPrimalEvent(int event) {
        if (event > 0) {
            lifetimeModel.observeBirth(event);
            recordDemandTransition(event);
        }''')

patch('''    void rebuildPrimalGapValues(int maxGap) {
        std::array<double, 41> rate{};''', '''    void rebuildPrimalGapValues(int maxGap) {
        std::array<double, 41> rate{};
        double observedDemand = 0.0;
        for (int request=1;request<=40;++request) observedDemand += primalRecentRequests[request];''')
patch('''                rate[static_cast<std::size_t>(gap)] =
                    static_cast<double>(primalRecentRequests[static_cast<std::size_t>(gap)]) /
                    static_cast<double>(std::max<std::int64_t>(1, fitting));''','''                double demand = static_cast<double>(primalRecentRequests[static_cast<std::size_t>(gap)]);
                if (primalConditionLength > 0) {
                    const double conditional = observedDemand *
                        demandTransitions[primalConditionLength][gap] /
                        static_cast<double>(demandTransitionTotals[primalConditionLength]);
                    // Keep three quarters of the unconditional demand estimate.
                    demand = 0.75 * demand + 0.25 * conditional;
                }
                rate[static_cast<std::size_t>(gap)] = demand /
                    static_cast<double>(std::max<std::int64_t>(1, fitting));''')
patch('        primalModelStep = primalStep;', '        primalModelCondition = primalConditionLength;\n        primalModelStep = primalStep;')
patch('''        if (primalModelDirty || primalStep - primalModelStep >= 64 ||
            maxGap > primalComputedLimit) {''','''        if (primalModelDirty || primalStep - primalModelStep >= 64 ||
            maxGap > primalComputedLimit || primalModelCondition != primalConditionLength) {''')
patch('''        StartIter best = legacyBest;
        // The opportunity-cost DP''','''        StartIter best = legacyBest;
        primalConditionLength = conditionalDemandReady(length) ? length : 0;
        // The opportunity-cost DP''')
build('conditional_demand',s,'Observed transition demand (2048 insertion transitions), prequential accuracy>=80% on32..64 predictions and row>=16/>=80%, shrink25% into current DP. No IDs or public responses.')
(HERE/'conditional-hypothesis.json').write_text(json.dumps(dict(created_at=datetime.datetime.now(datetime.timezone.utc).isoformat(),
    new_fresh_outcomes_observed=False,source_sha256=sha(HERE/'candidates/conditional_demand/solution.cpp'),
    fixed_parameters='row>=16, rowmax>=80%, prequential32..64 with>=80%, transition ring2048, mixture25%; one variant, no sweep',
    motivation='Global histograms lose order. Recognizable insertion motifs may alter next-size demand. Use honest rolling prediction errors to shut down after pattern violations, shrink to preserve unconditional evidence.'),indent=2)+'\n')
