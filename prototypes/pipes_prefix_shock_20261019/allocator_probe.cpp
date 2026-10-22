// Diagnostic controls only. The tape is a frozen public-future plan.
// guarded checks every command and retains physical state on mismatch.
// blind intentionally replays even after a different input command.
#include <algorithm>
#include <fstream>
#include <iostream>
#include <map>
#include <set>
#include <stdexcept>
#include <string>
#include <utility>
#include <vector>
using namespace std;

class Allocator {
    map<int, int> gaps;
    set<pair<int, int>> sizes;
    vector<pair<int, int>> pipes{{-1, 0}};
    int trench = 0;

    void erase(map<int, int>::iterator it) {
        sizes.erase({it->second - it->first, it->first});
        gaps.erase(it);
    }
    void add(int left, int right) {
        if (left == right) return;
        auto it = gaps.lower_bound(left);
        if (it != gaps.begin() && prev(it)->second == left) {
            auto before = prev(it);
            left = before->first;
            erase(before);
        }
        it = gaps.lower_bound(left);
        if (it != gaps.end() && it->first == right) {
            right = it->second;
            erase(it);
        }
        gaps[left] = right;
        sizes.insert({right - left, left});
    }
    void reserve(int pos, int length) {
        auto it = gaps.upper_bound(pos);
        if (it == gaps.begin()) throw runtime_error("missing placement gap");
        --it;
        int left = it->first, right = it->second;
        if (pos < left || pos + length > right) throw runtime_error("occupied placement");
        erase(it);
        add(left, pos);
        add(pos + length, right);
    }

public:
    void reply(int command, int planned = -1) {
        if (command < 0) {
            int pid = -command;
            auto [pos, length] = pipes.at(pid);
            if (pos < 0) throw runtime_error("invalid PID");
            add(pos, pos + length);
            pipes[pid] = {-1, 0};
            cout << pos << '\n' << flush;
            return;
        }
        int pos = planned;
        if (pos < 0) {
            auto it = sizes.lower_bound({command, -1});
            if (it != sizes.end()) pos = it->second;
            else {
                pos = trench;
                if (!gaps.empty() && prev(gaps.end())->second == trench)
                    pos = prev(gaps.end())->first;
            }
        }
        int new_trench = max(trench, ((pos + command + 19) / 20) * 20);
        int digs = (new_trench - trench) / 20;
        if (new_trench > trench) add(trench, new_trench);
        trench = new_trench;
        reserve(pos, command);
        pipes.push_back({pos, command});
        cout << digs << ' ' << pos << '\n' << flush;
    }
};

int main(int argc, char** argv) {
    if (argc != 3) return 2;
    string mode = argv[1];
    if (mode != "bestfit" && mode != "guarded" && mode != "blind") return 2;
    ifstream input(argv[2]);
    int n = 0;
    if (!(input >> n)) return 2;
    vector<pair<int, int>> tape(n);
    for (auto& [command, pos] : tape) if (!(input >> command >> pos)) return 2;
    ios::sync_with_stdio(false);
    cin.tie(nullptr);
    Allocator state;
    int command, index = 0;
    bool following = mode != "bestfit";
    while (cin >> command && command != 0) {
        if (mode == "blind" && index < n) {
            state.reply(tape[index].first, tape[index].second);
        } else {
            if (index >= n || command != tape[index].first) following = false;
            state.reply(command, following ? tape[index].second : -1);
        }
        ++index;
    }
}
