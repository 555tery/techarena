#!/usr/bin/env python3
"""Build an isolated diagnostic runner from the frozen Pipes allocator."""

from pathlib import Path

ROOT = Path(__file__).resolve().parents[4]
source = ROOT / "results/pipes/final/solution.cpp"
out = Path(__file__).with_name("longbeam.cpp")
text = source.read_text()

text = text.replace("#include <deque>\n", "#include <deque>\n#include <fstream>\n#include <memory>\n#include <sstream>\n#include <stdexcept>\n#include <string>\n#include <tuple>\n#include <unordered_set>\n")

fenwick_old = '''    void fenwickAdd(int index, int delta) {
        const int limit = static_cast<int>(activeFenwick.size());
        for (int position = index; position < limit; position += position & -position) {
            activeFenwick[static_cast<std::size_t>(position)] += delta;
        }
    }
'''.replace("\n+", "\n")
fenwick_new = '''    void fenwickAdd(int index, int delta) {
        while (index >= static_cast<int>(activeFenwick.size())) {
            const int position = static_cast<int>(activeFenwick.size());
            const int lowbit = position & -position;
            const int prior = fenwickPrefix(position - 1) - fenwickPrefix(position - lowbit);
            activeFenwick.push_back(prior);
        }
        const int limit = static_cast<int>(activeFenwick.size());
        for (int position = index; position < limit; position += position & -position) {
            activeFenwick[static_cast<std::size_t>(position)] += delta;
        }
    }
'''.replace("\n+", "\n")
if fenwick_old not in text:
    raise SystemExit("fenwickAdd marker not found")
text = text.replace(fenwick_old, fenwick_new, 1)

diag_type = '''struct DiagnosticAction {
    std::int64_t digs = 0;
    std::int64_t start = 0;
};

'''
marker = "class Allocator {\npublic:\n"
if marker not in text:
    raise SystemExit("Allocator marker not found")
text = text.replace(marker, diag_type + marker, 1)

methods = r'''    void compactFenwickForDiagnostic() {
        activeFenwick.assign(pipes.size(), 0);
        for (std::size_t pid = 1; pid < pipes.size(); ++pid) {
            if (pipes[pid].active) fenwickAdd(static_cast<int>(pid), 1);
        }
    }

    std::vector<DiagnosticAction> diagnosticActions(int length, int cap) const {
        std::vector<DiagnosticAction> result;
        std::set<std::pair<std::int64_t, std::int64_t>> unique;
        const int sizeCohort = static_cast<int>(
            lengthOccurrenceCount[static_cast<std::size_t>(length)] % 2);
        const bool smoothDisabled = runLeftDisabledBySmoothTrend ||
            hasSmoothSizeTrendWith(length);
        const bool runLeft = !smoothDisabled && hasSameLengthRecentRun(length);
        const bool highSide = runLeft
            ? (sizeCohort != 0)
            : (alternatingDeleteMode
                ? ((static_cast<int>(pipes.size()) & 1) != predictedDeletedParity)
                : (parityCohortMode
                    ? sizeCohort == 0
                    : (length <= kRightEdgeMaxPipeLength || hasSameLengthRecentRun(length))));

        auto add = [&](std::int64_t digs, std::int64_t start) {
            if (start < 0 || start + length > trenchLength + digs * kDigLength) return;
            if (unique.emplace(digs, start).second) result.push_back({digs, start});
        };

        auto baseline = const_cast<Allocator*>(this)->bestFittingGap(length, highSide, sizeCohort);
        std::vector<std::tuple<std::int64_t, std::int64_t, std::int64_t>> fitting;
        for (const auto& [start, end] : freeByStart) {
            const std::int64_t gapLength = end - start;
            if (gapLength < length) continue;
            fitting.emplace_back(scoreGap(gapLength, length), start, end);
        }
        std::sort(fitting.begin(), fitting.end(), [highSide](const auto& lhs, const auto& rhs) {
            if (std::get<0>(lhs) != std::get<0>(rhs)) return std::get<0>(lhs) < std::get<0>(rhs);
            return highSide ? std::get<1>(lhs) > std::get<1>(rhs)
                            : std::get<1>(lhs) < std::get<1>(rhs);
        });

        if (!fitting.empty()) {
            std::vector<std::pair<std::int64_t, std::int64_t>> selected;
            const std::size_t per_rank = static_cast<std::size_t>(std::max(1, cap / 4));
            for (std::size_t i = 0; i < fitting.size() && i < per_rank; ++i)
                selected.emplace_back(std::get<1>(fitting[i]), std::get<2>(fitting[i]));
            auto by_size = fitting;
            std::sort(by_size.begin(), by_size.end(), [](const auto& lhs, const auto& rhs) {
                const auto lsize = std::get<2>(lhs) - std::get<1>(lhs);
                const auto rsize = std::get<2>(rhs) - std::get<1>(rhs);
                if (lsize != rsize) return lsize > rsize;
                return std::get<1>(lhs) < std::get<1>(rhs);
            });
            for (std::size_t i = 0; i < by_size.size() && i < per_rank; ++i)
                selected.emplace_back(std::get<1>(by_size[i]), std::get<2>(by_size[i]));
            if (baseline != freeByStart.end()) selected.emplace_back(baseline->first, baseline->second);
            auto tail = const_cast<Allocator*>(this)->tailGap();
            if (tail != freeByStart.end() && tail->second - tail->first >= length)
                selected.emplace_back(tail->first, tail->second);
            if (!fitting.empty()) {
                auto address = fitting;
                std::sort(address.begin(), address.end(), [](const auto& lhs, const auto& rhs) {
                    return std::get<1>(lhs) < std::get<1>(rhs);
                });
                selected.emplace_back(std::get<1>(address.front()), std::get<2>(address.front()));
                selected.emplace_back(std::get<1>(address.back()), std::get<2>(address.back()));
            }
            std::sort(selected.begin(), selected.end());
            selected.erase(std::unique(selected.begin(), selected.end()), selected.end());
            for (const auto& [left, right] : selected) {
                add(0, left);
                add(0, right - length);
            }
            if (baseline != freeByStart.end()) {
                const std::int64_t start = highSide
                    ? baseline->second - length : baseline->first;
                add(0, start);
            }
            if (result.size() > static_cast<std::size_t>(cap)) {
                std::vector<DiagnosticAction> clipped;
                const std::int64_t base_start = baseline != freeByStart.end()
                    ? (highSide ? baseline->second - length : baseline->first)
                    : result.front().start;
                for (const auto& action : result) {
                    if (action.digs == 0 && action.start == base_start) {
                        clipped.push_back(action);
                        break;
                    }
                }
                for (const auto& action : result) {
                    if (clipped.size() >= static_cast<std::size_t>(cap)) break;
                    if (action.digs == 0 && action.start == base_start) continue;
                    clipped.push_back(action);
                }
                result = std::move(clipped);
            }
            return result;
        }

        auto tail = const_cast<Allocator*>(this)->tailGap();
        int tailCohort = parityCohortMode ? sizeCohort : -1;
        bool preserveForeignTail = false;
        if (parityCohortMode && tail != freeByStart.end()) {
            tailCohort = gapCohort.at(tail->first);
            preserveForeignTail = tailCohort >= 0 && tailCohort != sizeCohort;
            if (preserveForeignTail) tailCohort = sizeCohort;
        }
        const std::int64_t tailStart =
            tail == freeByStart.end() || preserveForeignTail ? trenchLength : tail->first;
        const std::int64_t tailLength = trenchLength - tailStart;
        const std::int64_t deficit = std::max<std::int64_t>(0, length - tailLength);
        const std::int64_t digs = (deficit + kDigLength - 1) / kDigLength;
        const std::int64_t newLength = trenchLength + digs * kDigLength;
        for (std::int64_t start = tailStart; start + length <= newLength; ++start)
            add(digs, start);
        if (result.size() > static_cast<std::size_t>(cap)) {
            std::vector<DiagnosticAction> clipped;
            if (!result.empty()) clipped.push_back(result.front());
            if (result.size() > 1 && clipped.size() < static_cast<std::size_t>(cap))
                clipped.push_back(result.back());
            for (std::size_t i = 1; i + 1 < result.size() &&
                 clipped.size() < static_cast<std::size_t>(cap); ++i) {
                if (i % std::max<std::size_t>(1, result.size() /
                        std::max(1, cap - static_cast<int>(clipped.size()))) == 0)
                    clipped.push_back(result[i]);
            }
            result = std::move(clipped);
        }
        return result;
    }

    void placeDiagnostic(int length, const DiagnosticAction& action) {
        const int sizeCohort = static_cast<int>(
            lengthOccurrenceCount[static_cast<std::size_t>(length)] % 2);
        if (hasSmoothSizeTrendWith(length)) runLeftDisabledBySmoothTrend = true;
        const bool runLeftActive = !runLeftDisabledBySmoothTrend &&
            hasSameLengthRecentRun(length);
        const bool highSide = runLeftActive
            ? (sizeCohort != 0)
            : (alternatingDeleteMode
                ? ((static_cast<int>(pipes.size()) & 1) != predictedDeletedParity)
                : (parityCohortMode
                    ? sizeCohort == 0
                    : (length <= kRightEdgeMaxPipeLength || hasSameLengthRecentRun(length))));
        auto baselineGap = bestFittingGap(length, highSide, sizeCohort);
        if (baselineGap != freeByStart.end())
            (void)chooseGapWithRollout(length, highSide, sizeCohort, baselineGap);

        const std::int64_t start = action.start;
        const std::int64_t end = start + length;
        if (action.digs == 0) {
            auto it = freeByStart.upper_bound(start);
            if (it == freeByStart.begin()) throw std::runtime_error("forced placement has no containing gap");
            --it;
            if (it->first > start || it->second < end)
                throw std::runtime_error("forced placement is outside a free gap");
            const std::int64_t gapStart = it->first;
            const std::int64_t gapEnd = it->second;
            const int cohort = gapCohort.at(gapStart);
            eraseGap(it);
            if (gapStart < start) addFreeGap(gapStart, start, cohort);
            if (end < gapEnd) addFreeGap(end, gapEnd, cohort);
        } else {
            const std::int64_t oldTrench = trenchLength;
            const std::int64_t newTrench = oldTrench + action.digs * kDigLength;
            auto tail = tailGap();
            int tailCohort = parityCohortMode ? sizeCohort : -1;
            bool preserveForeignTail = false;
            if (parityCohortMode && tail != freeByStart.end()) {
                tailCohort = gapCohort.at(tail->first);
                preserveForeignTail = tailCohort >= 0 && tailCohort != sizeCohort;
                if (preserveForeignTail) tailCohort = sizeCohort;
            }
            const std::int64_t tailStart =
                tail == freeByStart.end() || preserveForeignTail ? oldTrench : tail->first;
            if (start < tailStart || end > newTrench)
                throw std::runtime_error("forced trench placement is outside expandable tail");
            if (!preserveForeignTail && tail != freeByStart.end()) eraseGap(tail);
            trenchLength = newTrench;
            if (!preserveForeignTail && tailStart < start)
                addFreeGap(tailStart, start, tailCohort);
            if (end < newTrench) addFreeGap(end, newTrench, tailCohort);
        }
        const int pid = static_cast<int>(pipes.size());
        pipes.push_back(Pipe{start, length, true, sizeCohort});
        fenwickAdd(pid, 1);
        ++activePipeCount;
        ++lengthOccurrenceCount[static_cast<std::size_t>(length)];
        recordLength(length);
        recordObservation(Observation{1, length});
    }

'''
private_marker = "\nprivate:\n    using StartIter = std::map<std::int64_t, std::int64_t>::iterator;"
if private_marker not in text:
    raise SystemExit("Allocator private marker not found")
text = text.replace(private_marker, "\n" + methods + private_marker, 1)

main_start = text.rfind("int main() {")
if main_start < 0:
    raise SystemExit("main marker not found")
driver = r'''class NullBuffer final : public std::streambuf {
protected:
    int overflow(int ch) override { return ch; }
};

int main(int argc, char** argv) {
    if (argc != 8) {
        std::cerr << "usage: longbeam INPUT TRACE OUT START COUNT WIDTH ACTION_CAP\n";
        return 2;
    }
    const std::string input_path = argv[1];
    const std::string trace_path = argv[2];
    const std::string output_path = argv[3];
    const int start_op = std::stoi(argv[4]);
    const int window_count = std::stoi(argv[5]);
    const int width = std::stoi(argv[6]);
    const int action_cap = std::stoi(argv[7]);

    std::ifstream in(input_path);
    double weight = 0.0;
    int n = 0;
    in >> weight >> n;
    std::vector<std::int64_t> ops(static_cast<std::size_t>(n));
    for (auto& op : ops) in >> op;
    if (!in || start_op < 1 || window_count < 1 || start_op + window_count - 1 > n)
        throw std::runtime_error("invalid input/window");

    std::ifstream tr(trace_path);
    std::vector<std::int64_t> expected;
    std::int64_t value;
    while (tr >> value) expected.push_back(value);
    if (!tr.eof()) throw std::runtime_error("bad trace");

    Allocator base;
    std::unique_ptr<Allocator> initial;
    std::vector<DiagnosticAction> baseline_actions(static_cast<std::size_t>(n));
    std::size_t answer_cursor = 0;
    for (int i = 0; i < n; ++i) {
        if (i + 1 == start_op) {
            base.compactFenwickForDiagnostic();
            initial.reset(new Allocator(base));
        }
        std::ostringstream capture;
        std::streambuf* old = std::cout.rdbuf(capture.rdbuf());
        if (ops[static_cast<std::size_t>(i)] > 0)
            base.place(static_cast<int>(ops[static_cast<std::size_t>(i)]));
        else
            base.remove(-ops[static_cast<std::size_t>(i)]);
        std::cout.rdbuf(old);
        std::istringstream actual_stream(capture.str());
        std::vector<std::int64_t> actual;
        while (actual_stream >> value) actual.push_back(value);
        const std::size_t need = ops[static_cast<std::size_t>(i)] > 0 ? 2 : 1;
        if (answer_cursor + need > expected.size())
            throw std::runtime_error("baseline answer stream too short");
        if (ops[static_cast<std::size_t>(i)] > 0)
            baseline_actions[static_cast<std::size_t>(i)] =
                {expected[answer_cursor], expected[answer_cursor + 1]};
        if (actual.size() != need)
            throw std::runtime_error("unexpected baseline response shape at op " + std::to_string(i + 1));
        for (std::size_t k = 0; k < need; ++k) {
            if (actual[k] != expected[answer_cursor + k])
                throw std::runtime_error("baseline mismatch at op " + std::to_string(i + 1));
        }
        answer_cursor += need;
    }
    if (answer_cursor != expected.size()) throw std::runtime_error("baseline answer token mismatch");
    if (!initial) throw std::runtime_error("initial window state missing");
    const std::int64_t baseline_final = base.trenchLength;
    const std::int64_t initial_trench = initial->trenchLength;
    const std::size_t begin = static_cast<std::size_t>(start_op - 1);
    const std::size_t stop = begin + static_cast<std::size_t>(window_count);

    std::set<int> future_deleted;
    for (std::size_t i = begin; i < stop; ++i)
        if (ops[i] < 0) future_deleted.insert(static_cast<int>(-ops[i]));
    std::array<int, 41> future_lengths{};
    for (std::size_t i = begin; i < stop; ++i)
        if (ops[i] > 0) ++future_lengths[static_cast<std::size_t>(ops[i])];

    NullBuffer null_buffer;
    std::streambuf* original_stdout = std::cout.rdbuf(&null_buffer);
    Allocator control = *initial;
    struct Choice { int op_index; DiagnosticAction action; };
    struct Node { Allocator state; std::vector<Choice> path; };
    std::vector<Choice> control_path;
    std::vector<Node> beam;
    beam.push_back(Node{*initial, {}});
    std::uint64_t expanded = 0;

    auto signature = [](const Allocator& s) {
        std::string key;
        auto put = [&](auto x) {
            key.append(reinterpret_cast<const char*>(&x), sizeof(x));
        };
        put(s.trenchLength);
        put(s.mcDecisionsUsed);
        for (const auto& [left, right] : s.freeByStart) {
            put(left); put(right); put(s.gapCohort.at(left));
        }
        const std::int64_t sentinel = -1;
        put(sentinel);
        for (std::size_t pid = 1; pid < s.pipes.size(); ++pid) {
            if (!s.pipes[pid].active) continue;
            const std::int64_t p = static_cast<std::int64_t>(pid);
            put(p); put(s.pipes[pid].start); put(s.pipes[pid].sizeCohort);
        }
        return key;
    };

    struct Ranked { std::size_t index; std::int64_t trench; std::int64_t capacity;
                    std::int64_t max_gap; std::int64_t tail; std::size_t gaps; };
    auto rank_node = [&](const Node& node) {
        const Allocator& s = node.state;
        std::vector<std::pair<std::int64_t, std::int64_t>> intervals;
        intervals.reserve(s.freeByStart.size() + future_deleted.size());
        for (const auto& [left, right] : s.freeByStart) intervals.emplace_back(left, right);
        for (int pid : future_deleted) {
            if (pid > 0 && static_cast<std::size_t>(pid) < s.pipes.size() && s.pipes[pid].active)
                intervals.emplace_back(s.pipes[pid].start,
                                       s.pipes[pid].start + s.pipes[pid].length);
        }
        std::sort(intervals.begin(), intervals.end());
        std::vector<std::pair<std::int64_t, std::int64_t>> merged;
        for (const auto& iv : intervals) {
            if (merged.empty() || iv.first > merged.back().second) merged.push_back(iv);
            else merged.back().second = std::max(merged.back().second, iv.second);
        }
        std::int64_t capacity = 0, max_gap = 0, tail = 0;
        for (const auto& [left, right] : merged) {
            const auto len = right - left;
            max_gap = std::max(max_gap, len);
            if (right == s.trenchLength) tail = len;
            for (int l = 1; l <= 40; ++l)
                capacity += static_cast<std::int64_t>(future_lengths[static_cast<std::size_t>(l)]) *
                            (len / l);
        }
        return std::tuple<std::int64_t, std::int64_t, std::int64_t,
                          std::int64_t, std::size_t>(
            s.trenchLength, -capacity, -max_gap, -tail, s.freeByStart.size());
    };

    for (std::size_t i = begin; i < stop; ++i) {
        const std::int64_t op = ops[i];
        std::vector<Node> generated;
        if (op > 0) {
            for (const Node& node : beam) {
                auto actions = node.state.diagnosticActions(static_cast<int>(op), action_cap);
                for (const auto& action : actions) {
                    Node child{node.state, node.path};
                    child.state.placeDiagnostic(static_cast<int>(op), action);
                    child.path.push_back(Choice{static_cast<int>(i + 1), action});
                    generated.push_back(std::move(child));
                }
            }
        } else {
            for (const Node& node : beam) {
                Node child{node.state, node.path};
                child.state.remove(-op);
                generated.push_back(std::move(child));
            }
        }
        if (op < 0) future_deleted.erase(static_cast<int>(-op));
        else --future_lengths[static_cast<std::size_t>(op)];

        if (op > 0) {
            // The baseline control remains available in every beam layer.
            control.place(static_cast<int>(op));
            control_path.push_back(Choice{static_cast<int>(i + 1), baseline_actions[i]});
        } else {
            control.remove(-op);
        }

        std::unordered_set<std::string> seen;
        std::vector<Node> unique;
        unique.reserve(generated.size() + 1);
        for (auto& node : generated) {
            auto key = signature(node.state);
            if (seen.insert(std::move(key)).second) unique.push_back(std::move(node));
        }
        auto control_key = signature(control);
        if (seen.insert(control_key).second) unique.push_back(Node{control, control_path});
        expanded += generated.size();

        std::sort(unique.begin(), unique.end(), [&](const Node& lhs, const Node& rhs) {
            return rank_node(lhs) < rank_node(rhs);
        });
        if (unique.size() > static_cast<std::size_t>(width)) unique.resize(static_cast<std::size_t>(width));
        beam = std::move(unique);
    }

    std::int64_t best_final = std::numeric_limits<std::int64_t>::max();
    std::size_t best_index = 0;
    bool best_is_baseline_control = false;
    std::vector<std::int64_t> finalist_trenches;
    for (std::size_t j = 0; j < beam.size(); ++j) {
        Allocator replay = beam[j].state;
        replay.compactFenwickForDiagnostic();
        for (std::size_t i = stop; i < ops.size(); ++i) {
            if (ops[i] > 0) replay.place(static_cast<int>(ops[i]));
            else replay.remove(-ops[i]);
        }
        finalist_trenches.push_back(replay.trenchLength);
        if (replay.trenchLength < best_final) { best_final = replay.trenchLength; best_index = j; }
    }
    Allocator baseline_replay = control;
    baseline_replay.compactFenwickForDiagnostic();
    for (std::size_t i = stop; i < ops.size(); ++i) {
        if (ops[i] > 0) baseline_replay.place(static_cast<int>(ops[i]));
        else baseline_replay.remove(-ops[i]);
    }
    const std::int64_t baseline_control_replay_trench = baseline_replay.trenchLength;
    if (baseline_control_replay_trench != baseline_final)
        throw std::runtime_error("baseline control suffix replay diverges from the verified trace");
    finalist_trenches.push_back(baseline_control_replay_trench);
    if (baseline_control_replay_trench < best_final) {
        best_final = baseline_control_replay_trench;
        best_is_baseline_control = true;
    }
    std::cout.rdbuf(original_stdout);

    std::ofstream out(output_path);
    out << "{\n  \"scope\": \"offline bounded beam inside one command block; exact frozen allocator policy replays the entire remaining suffix; future data used only for diagnostic beam ranking\",\n";
    out << "  \"input\": \"" << input_path << "\",\n  \"trace\": \"" << trace_path << "\",\n";
    out << "  \"commands\": " << n << ", \"window_start_op_1based\": " << start_op
        << ", \"window_count\": " << window_count << ", \"beam_width\": " << width
        << ", \"action_cap\": " << action_cap << ",\n";
    out << "  \"baseline_final_trench_m\": " << baseline_final << ",\n";
    out << "  \"window_initial_trench_m\": " << initial_trench << ",\n";
    out << "  \"baseline_control_window_final_trench_m\": " << control.trenchLength << ",\n";
    out << "  \"mc_decisions_at_window_start\": " << initial->mcDecisionsUsed << ",\n";
    out << "  \"expanded_states_generated\": " << expanded << ",\n";
    out << "  \"finalist_replay_trench_m\": [";
    for (std::size_t i = 0; i < finalist_trenches.size(); ++i) out << (i ? ", " : "") << finalist_trenches[i];
    out << "],\n  \"best_full_suffix_witness_trench_m\": " << best_final
        << ",\n  \"full_suffix_witness_saving_m\": " << baseline_final - best_final << ",\n";
    out << "  \"best_is_baseline_control\": " << (best_is_baseline_control ? "true" : "false") << ",\n";
    out << "  \"baseline_control_replay_trench_m\": " << baseline_control_replay_trench << ",\n";
    out << "  \"winner_path\": [";
    const auto& path = best_is_baseline_control ? control_path : beam[best_index].path;
    for (std::size_t i = 0; i < path.size(); ++i) {
        out << (i ? ", " : "") << "{\"op\":" << path[i].op_index
            << ",\"digs\":" << path[i].action.digs
            << ",\"start\":" << path[i].action.start << "}";
    }
    out << "]\n}\n";
    std::cerr << "baseline=" << baseline_final << " best=" << best_final
              << " saving=" << baseline_final - best_final << " expanded=" << expanded
              << " finalists=" << beam.size() << " winner=" << best_index << '\n';
    return 0;
}
'''
text = text[:main_start] + driver
out.write_text(text)
print(out)
