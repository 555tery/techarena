#include <algorithm>
#include <array>
#include <cstdint>
#include <deque>
#include <fstream>
#include <iostream>
#include <iterator>
#include <map>
#include <sstream>
#include <stdexcept>
#include <string>
#include <vector>

namespace {

enum Reason : int { kPlacementResidual = 0, kDeletionHole = 1, kMixedMerged = 2 };

const char* reasonName(int reason) {
    if (reason == kPlacementResidual) return "placement_residual";
    if (reason == kDeletionHole) return "deletion_hole";
    return "mixed_merged";
}

struct Gap {
    std::int64_t end = 0;
    std::uint64_t id = 0;
    int bornOp = 0;
    int reason = kPlacementResidual;
    int lineageMask = 0;  // bit 0: placement-derived; bit 1: deletion-derived.
};

struct Pipe {
    std::int64_t start = -1;
    int length = 0;
    bool active = false;
};

struct Episode {
    std::uint64_t id;
    std::int64_t start;
    std::int64_t end;
    int bornOp;
    int reason;
    int lineageMask;
    int closedOp;
    std::string closeCause;
};

struct CostChoice {
    int length = 0;
    std::int64_t baselineStart = 0;
    std::int64_t baselineLength = 0;
    std::int64_t baselineScore = 0;
    std::int64_t baselineSlack = 0;
    std::int64_t baselineMisses = 0;
};

class Replay {
public:
    Replay(const std::string& inputPath, const std::string& answerPath,
           const std::string& costPath, const std::string& outDir)
        : outDir_(outDir) {
        std::ifstream input(inputPath);
        double weight = 0;
        int n = 0;
        if (!(input >> weight >> n)) throw std::runtime_error("bad input header");
        n_ = n;
        commands_.resize(static_cast<std::size_t>(n));
        for (int i = 0; i < n; ++i) {
            if (!(input >> commands_[static_cast<std::size_t>(i)]))
                throw std::runtime_error("truncated commands");
            if (commands_[static_cast<std::size_t>(i)] > 0) {
                ++placementCount_;
                ++allLengthFrequency_[static_cast<std::size_t>(commands_[static_cast<std::size_t>(i)])];
            }
        }
        std::ifstream answers(answerPath);
        if (!answers) throw std::runtime_error("cannot open judge output");
        answers_ = std::move(answers);
        std::ifstream costLog(costPath);
        if (!costLog) throw std::runtime_error("cannot open cost audit log");
        std::string line;
        while (std::getline(costLog, line)) {
            std::istringstream row(line);
            std::string marker;
            row >> marker;
            if (marker != "COST") continue;
            int op = 0, highSide = 0, cohort = 0, parity = 0;
            CostChoice choice;
            std::int64_t selectedStart = 0, selectedLength = 0;
            std::int64_t historySize = 0;
            if (!(row >> op >> choice.length >> highSide >> cohort >> parity
                      >> choice.baselineStart >> choice.baselineLength >> choice.baselineScore
                      >> selectedStart >> selectedLength >> historySize
                      >> choice.baselineSlack >> choice.baselineMisses))
                throw std::runtime_error("malformed COST audit row");
            if (!costChoices_.emplace(op, choice).second)
                throw std::runtime_error("duplicate COST audit operation");
        }
        pipes_.emplace_back();
    }

    void run() {
        std::ofstream placements(outDir_ + "/placements.csv");
        placements << "op,pid,length,digs,pipe_start,selected_gap_start,selected_gap_end,"
                      "selected_gap_reason,lineage_mask,gap_age_ops,history_size,slack,misses,"
                      "slack_cost,penalty_cost,total_cost,bestfit_gap_start,bestfit_gap_length,"
                      "bestfit_reason,bestfit_lineage_mask,bestfit_score,bestfit_slack,bestfit_misses\n";

        for (int op = 1; op <= n_; ++op) {
            const int command = commands_[static_cast<std::size_t>(op - 1)];
            if (command > 0) {
                std::int64_t digs = 0, start = 0;
                if (!(answers_ >> digs >> start)) throw std::runtime_error("missing placement answer");
                place(op, command, digs, start, placements);
            } else {
                std::int64_t reportedStart = 0;
                if (!(answers_ >> reportedStart)) throw std::runtime_error("missing deletion answer");
                remove(op, -command, reportedStart);
            }
            verifyInvariant(op);
        }

        std::string extra;
        if (answers_ >> extra) throw std::runtime_error("extra tokens in judge output");
        for (auto& [start, gap] : gaps_) {
            (void)start;
            episodes_.push_back(Episode{gap.id, start, gap.end, gap.bornOp,
                                        gap.reason, gap.lineageMask, n_, "eof_censored"});
        }
        writeOutputs();
    }

private:
    void addGap(std::int64_t start, std::int64_t end, int op, int reason, int lineage) {
        if (start >= end) return;
        auto next = gaps_.lower_bound(start);
        if (next != gaps_.end() && next->first < end)
            throw std::runtime_error("overlap inserting gap");
        if (next != gaps_.begin()) {
            auto prev = std::prev(next);
            if (prev->second.end > start) throw std::runtime_error("overlap with previous gap");
        }
        const std::uint64_t id = ++nextGapId_;
        gaps_.emplace(start, Gap{end, id, op, reason, lineage});
        currentFreeLength_ += end - start;
    }

    void closeGap(std::map<std::int64_t, Gap>::iterator it, int op,
                  const std::string& cause) {
        const std::int64_t start = it->first;
        const Gap gap = it->second;
        currentFreeLength_ -= gap.end - start;
        episodes_.push_back(Episode{gap.id, start, gap.end, gap.bornOp,
                                    gap.reason, gap.lineageMask, op, cause});
        gaps_.erase(it);
    }

    std::map<std::int64_t, Gap>::iterator containing(std::int64_t start,
                                                    std::int64_t end) {
        auto it = gaps_.upper_bound(start);
        if (it == gaps_.begin()) return gaps_.end();
        --it;
        return it->first <= start && it->second.end >= end ? it : gaps_.end();
    }

    void place(int op, int length, std::int64_t digs, std::int64_t start,
               std::ofstream& placements) {
        const std::int64_t oldTrench = trenchLength_;
        const std::int64_t newTrench = oldTrench + digs * 20;
        if (digs > 0) {
            auto tail = gaps_.empty() ? gaps_.end() : std::prev(gaps_.end());
            if (tail != gaps_.end() && tail->second.end == oldTrench) {
                const std::int64_t tailStart = tail->first;
                const int lineage = tail->second.lineageMask | 1;
                closeGap(tail, op, "tail_extended_by_dig");
                addGap(tailStart, newTrench, op, kMixedMerged, lineage);
            } else {
                addGap(oldTrench, newTrench, op, kPlacementResidual, 1);
            }
            trenchLength_ = newTrench;
        }

        auto gapIt = containing(start, start + length);
        if (gapIt == gaps_.end()) throw std::runtime_error("placed pipe not inside a free interval");
        const std::int64_t gapStart = gapIt->first;
        const std::int64_t gapEnd = gapIt->second.end;
        const Gap parent = gapIt->second;
        const std::int64_t gapLength = gapEnd - gapStart;
        const std::int64_t slack = gapLength - length;
        std::int64_t misses = 0;
        if (slack > 0 && slack <= 40) {
            for (int request = static_cast<int>(slack) + 1; request <= 40; ++request)
                misses += recentFrequency_[static_cast<std::size_t>(request)];
        }
        const std::int64_t slackCost = slack * static_cast<std::int64_t>(recentLengths_.size());
        const std::int64_t penaltyCost = 60 * misses;
        const std::int64_t totalCost = slackCost + penaltyCost;
        std::string bestfitReason = "none";
        int bestfitLineage = 0;
        std::int64_t bestfitStart = -1;
        std::int64_t bestfitLength = -1;
        std::int64_t bestfitScore = -1;
        std::int64_t bestfitSlack = -1;
        std::int64_t bestfitMisses = -1;
        auto choiceIt = costChoices_.find(op);
        if (choiceIt != costChoices_.end()) {
            const CostChoice& choice = choiceIt->second;
            if (choice.length != length) throw std::runtime_error("COST length mismatch");
            auto bestfitIt = gaps_.find(choice.baselineStart);
            if (bestfitIt == gaps_.end() ||
                bestfitIt->second.end - bestfitIt->first != choice.baselineLength)
                throw std::runtime_error("COST baseline gap not present at placement");
            bestfitReason = reasonName(bestfitIt->second.reason);
            bestfitLineage = bestfitIt->second.lineageMask;
            bestfitStart = choice.baselineStart;
            bestfitLength = choice.baselineLength;
            bestfitScore = choice.baselineScore;
            bestfitSlack = choice.baselineSlack;
            bestfitMisses = choice.baselineMisses;
        }
        placements << op << ',' << pipes_.size() << ',' << length << ',' << digs << ',' << start << ','
                   << gapStart << ',' << gapEnd << ',' << reasonName(parent.reason) << ','
                   << parent.lineageMask << ',' << (op - parent.bornOp) << ','
                   << recentLengths_.size() << ',' << slack << ',' << misses << ','
                   << slackCost << ',' << penaltyCost << ',' << totalCost << ','
                   << bestfitStart << ',' << bestfitLength << ',' << bestfitReason << ','
                   << bestfitLineage << ',' << bestfitScore << ',' << bestfitSlack << ','
                   << bestfitMisses << '\n';

        closeGap(gapIt, op, "placement_consumed_or_split");
        if (gapStart < start)
            addGap(gapStart, start, op, kPlacementResidual, parent.lineageMask | 1);
        if (start + length < gapEnd)
            addGap(start + length, gapEnd, op, kPlacementResidual, parent.lineageMask | 1);

        pipes_.push_back(Pipe{start, length, true});
        activePipeLength_ += length;
        ++lengthOccurrenceCount_[static_cast<std::size_t>(length)];
        recentLengths_.push_back(length);
        ++recentFrequency_[static_cast<std::size_t>(length)];
        if (recentLengths_.size() > 2048) {
            --recentFrequency_[static_cast<std::size_t>(recentLengths_.front())];
            recentLengths_.pop_front();
        }
    }

    void remove(int op, int pid, std::int64_t reportedStart) {
        if (pid <= 0 || static_cast<std::size_t>(pid) >= pipes_.size())
            throw std::runtime_error("invalid pid in input");
        Pipe& pipe = pipes_[static_cast<std::size_t>(pid)];
        if (!pipe.active || pipe.start != reportedStart)
            throw std::runtime_error("delete output does not match active pipe position");
        const std::int64_t start = pipe.start;
        const std::int64_t end = start + pipe.length;
        std::int64_t gapStart = start;
        std::int64_t gapEnd = end;
        int lineage = 2;
        int parents = 0;

        auto next = gaps_.lower_bound(start);
        if (next != gaps_.begin()) {
            auto left = std::prev(next);
            if (left->second.end == start) {
                gapStart = left->first;
                lineage |= left->second.lineageMask;
                closeGap(left, op, "merged_by_deletion");
                ++parents;
            }
        }
        auto right = gaps_.find(end);
        if (right != gaps_.end()) {
            gapEnd = right->second.end;
            lineage |= right->second.lineageMask;
            closeGap(right, op, "merged_by_deletion");
            ++parents;
        }
        addGap(gapStart, gapEnd, op, parents == 0 ? kDeletionHole : kMixedMerged, lineage);

        pipe.active = false;
        activePipeLength_ -= pipe.length;
    }

    void verifyInvariant(int op) const {
        std::int64_t sum = activePipeLength_ + currentFreeLength_;
        if (sum != trenchLength_)
            throw std::runtime_error("free+occupied invariant failed at op " + std::to_string(op));
        std::int64_t previousEnd = -1;
        for (const auto& [start, gap] : gaps_) {
            if (start < previousEnd || gap.end <= start || gap.end > trenchLength_)
                throw std::runtime_error("gap ordering/bounds invariant failed at op " + std::to_string(op));
            previousEnd = gap.end;
        }
    }

    int fullDemandFit(std::int64_t gapLength) const {
        int count = 0;
        for (int len = 1; len <= 40; ++len)
            if (len <= gapLength) count += allLengthFrequency_[static_cast<std::size_t>(len)];
        return count;
    }

    int recentDemandFit(std::int64_t gapLength) const {
        int count = 0;
        for (int len = 1; len <= 40; ++len)
            if (len <= gapLength) count += recentFrequency_[static_cast<std::size_t>(len)];
        return count;
    }

    void writeOutputs() const {
        std::ofstream eps(outDir_ + "/gap_episodes.csv");
        eps << "id,start,end,length,birth_op,end_op,lifetime_ops,reason,lineage_mask,close_cause,"
               "right_censored,whole_trace_demands_fit,whole_trace_fit_fraction\n";
        for (const auto& e : episodes_) {
            const std::int64_t len = e.end - e.start;
            const int fit = fullDemandFit(len);
            eps << e.id << ',' << e.start << ',' << e.end << ',' << len << ',' << e.bornOp << ','
                << e.closedOp << ',' << (e.closedOp - e.bornOp) << ',' << reasonName(e.reason) << ','
                << e.lineageMask << ',' << e.closeCause << ',' << (e.closeCause == "eof_censored")
                << ',' << fit << ',' << static_cast<double>(fit) / placementCount_ << '\n';
        }

        std::ofstream cur(outDir_ + "/current_gaps.csv");
        cur << "start,end,length,id,birth_op,age_at_eof_ops,reason,lineage_mask,"
               "whole_trace_demands_fit,whole_trace_fit_fraction,recent2048_demands_fit,recent_fit_fraction\n";
        for (const auto& [start, gap] : gaps_) {
            const std::int64_t len = gap.end - start;
            const int full = fullDemandFit(len);
            const int recent = recentDemandFit(len);
            cur << start << ',' << gap.end << ',' << len << ',' << gap.id << ',' << gap.bornOp << ','
                << (n_ - gap.bornOp) << ',' << reasonName(gap.reason) << ',' << gap.lineageMask << ','
                << full << ',' << static_cast<double>(full) / placementCount_ << ','
                << recent << ',' << static_cast<double>(recent) / recentLengths_.size() << '\n';
        }

        std::ofstream meta(outDir_ + "/replay_meta.json");
        meta << "{\n  \"operations\": " << n_
             << ",\n  \"placements\": " << placementCount_
             << ",\n  \"trench_length_m\": " << trenchLength_
             << ",\n  \"occupied_length_m\": " << activePipeLength_
             << ",\n  \"free_length_m\": " << currentFreeLength_
             << ",\n  \"current_interval_count\": " << gaps_.size()
             << ",\n  \"interval_episodes\": " << episodes_.size()
             << ",\n  \"recent_window_size\": " << recentLengths_.size() << "\n}\n";
    }

    std::string outDir_;
    int n_ = 0;
    int placementCount_ = 0;
    std::vector<int> commands_;
    std::ifstream answers_;
    std::map<std::int64_t, Gap> gaps_;
    std::map<int, CostChoice> costChoices_;
    std::vector<Pipe> pipes_;
    std::vector<Episode> episodes_;
    std::int64_t trenchLength_ = 0;
    std::int64_t activePipeLength_ = 0;
    std::int64_t currentFreeLength_ = 0;
    std::uint64_t nextGapId_ = 0;
    std::array<int, 41> allLengthFrequency_{};
    std::array<int, 41> lengthOccurrenceCount_{};
    std::array<int, 41> recentFrequency_{};
    std::vector<int> recentLengthsStorage_;
    std::deque<int> recentLengths_;
};

}  // namespace

int main(int argc, char** argv) {
    if (argc != 5) {
        std::cerr << "usage: interval_origin_replay input.in judge_output.txt cost_log outdir\n";
        return 2;
    }
    try {
        Replay replay(argv[1], argv[2], argv[3], argv[4]);
        replay.run();
    } catch (const std::exception& e) {
        std::cerr << e.what() << '\n';
        return 1;
    }
}
