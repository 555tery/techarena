"""Correct a history-count guard and test one declared causal combination."""
import datetime, json
from build_primary import HERE, build, sha

base = (HERE/'candidates/primal_moderate/solution.cpp').read_text()
assert base.count('primalEventHistory.size() >= 256') == 1
# std::array::size() is capacity, not the number of observations.
fixed = base.replace('primalEventHistory.size() >= 256', 'primalStep >= 256')
build('primal_observed', fixed, 'Primal moderate with actual observed-event count, correcting the array-capacity guard. Original measured revision retained.')
short = fixed.replace('std::array<int, kHistoryWindow> primalEventHistory{};', 'std::array<int, 256> primalEventHistory{};')
short = short.replace('(2.0 * static_cast<double>(kHistoryWindow)));', '(2.0 * static_cast<double>(primalEventHistory.size())));')
assert short != fixed
build('primal_recent', short, 'One declared combination: moderate-population primal DP plus separate 256-event demand window. Existing side/cohort/MC histories unchanged.')
(HERE/'development-followup.json').write_text(json.dumps(dict(created_at=datetime.datetime.now(datetime.timezone.utc).isoformat(),
    observed_results='primal_moderate DEV +0.01071141336 mean, Open15 -0.03336297455; parity decay rejected due to DEV loss >0.10.',
    correction='primalEventHistory is fixed-size array; count gate must use primalStep. Do not overwrite already measured revision.',
    combination='One allowed causal combination; test on DEV192 and Open15 only, no fresh results yet.',
    candidates={n:sha(HERE/'candidates'/n/'solution.cpp') for n in ['primal_observed','primal_recent']}), indent=2)+'\n')
