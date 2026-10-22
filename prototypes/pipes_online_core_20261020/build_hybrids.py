"""Apply frozen causal core deltas to the separately audited handoff repair."""
import datetime, json
from build_primary import HERE, build, sha

exact = (HERE/'diagnostics/handoff_exact/solution.cpp').read_text()
build('handoff_exact', exact, 'Same old hybrid policy, exact shadow adoption at equal physical state; no core tuning.')
before = '''const bool ordinaryLargeMode = !parityCohortMode &&
            activePipeCount > kMcMaxActivePipes;'''
after = '''// The opportunity-cost DP needs observed demand and deletion evidence,
        // not thousands of live objects. Keep the established large-population path.
        const bool ordinaryLargeMode = !parityCohortMode &&
            (activePipeCount > kMcMaxActivePipes ||
             (activePipeCount >= 128 && primalStep >= 256 &&
              primalRecentDeletes >= 32));'''
assert exact.count(before)==1
observed=exact.replace(before,after)
build('hybrid_observed',observed,'Exact-handoff hybrid with the already frozen primal_observed core.')
recent=observed.replace('std::array<int, kHistoryWindow> primalEventHistory{};', 'std::array<int, 256> primalEventHistory{};')
recent=recent.replace('(2.0 * static_cast<double>(kHistoryWindow)));','(2.0 * static_cast<double>(primalEventHistory.size())));')
build('hybrid_recent',recent,'Exact-handoff hybrid with the already frozen primal_recent core.')
(HERE/'calibration-hybrids-freeze.json').write_text(json.dumps(dict(created_at=datetime.datetime.now(datetime.timezone.utc).isoformat(),
    evidence='Core-only calibration observed. No threshold changes; apply the same two frozen cores to one independently DEV-tested exact-state handoff repair.',
    sources={n:sha(HERE/'candidates'/n/'solution.cpp') for n in ['handoff_exact','hybrid_observed','hybrid_recent']}),indent=2)+'\n')
