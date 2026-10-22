// Offline-only search for Open15 case 11. It reads every future deletion.
// This is a placement-plan generator, not an online policy.
#include <algorithm>
#include <fstream>
#include <iostream>
#include <map>
#include <numeric>
#include <random>
#include <set>
#include <string>
#include <vector>

using namespace std;

struct GapSet {
  int cap;
  map<int, int> gaps;
  set<pair<int, int>> by_size;

  explicit GapSet(int c) : cap(c) { add(0, c); }
  void erase(map<int, int>::iterator it) {
    by_size.erase({it->second - it->first, it->first});
    gaps.erase(it);
  }
  void add(int left, int right) {
    if (left >= right) return;
    auto it = gaps.lower_bound(left);
    if (it != gaps.begin()) {
      auto prev = std::prev(it);
      if (prev->second == left) {
        left = prev->first;
        erase(prev);
      }
    }
    it = gaps.lower_bound(left);
    if (it != gaps.end() && it->first == right) {
      right = it->second;
      erase(it);
    }
    gaps[left] = right;
    by_size.insert({right - left, left});
  }
  bool take_at(int x, int len) {
    auto it = gaps.upper_bound(x);
    if (it == gaps.begin()) return false;
    --it;
    const int left = it->first, right = it->second;
    if (x < left || x + len > right) return false;
    erase(it);
    add(left, x);
    add(x + len, right);
    return true;
  }
  bool place(int len, int policy, int offset_policy, mt19937& rng, int& x) {
    auto first = by_size.lower_bound({len, -1});
    if (first == by_size.end()) return false;
    auto chosen = first;
    if (policy == 1) {
      for (auto it = gaps.begin(); it != gaps.end(); ++it) {
        if (it->second - it->first >= len) {
          chosen = by_size.find({it->second - it->first, it->first});
          break;
        }
      }
    } else if (policy == 2) {
      chosen = std::prev(by_size.end());
      if (chosen->first < len) return false;
    } else if (policy == 3) {
      vector<set<pair<int, int>>::const_iterator> candidates;
      for (auto it = first; it != by_size.end(); ++it) candidates.push_back(it);
      uniform_int_distribution<size_t> d(0, candidates.size() - 1);
      chosen = candidates[d(rng)];
    } else if (policy == 4) {
      vector<set<pair<int, int>>::const_iterator> candidates;
      for (auto it = first; it != by_size.end() && candidates.size() < 5; ++it)
        candidates.push_back(it);
      uniform_int_distribution<size_t> d(0, candidates.size() - 1);
      chosen = candidates[d(rng)];
    } else if (policy == 5) {
      vector<set<pair<int, int>>::const_iterator> candidates;
      auto it = std::prev(by_size.end());
      for (int k = 0; k < 5 && it != by_size.begin(); ++k, --it)
        if (it->first >= len) candidates.push_back(it);
      if (it->first >= len) candidates.push_back(it);
      if (candidates.empty()) return false;
      uniform_int_distribution<size_t> d(0, candidates.size() - 1);
      chosen = candidates[d(rng)];
    }
    const int left = chosen->second;
    const int right = left + chosen->first;
    int max_left = right - len;
    if (offset_policy == 0) x = left;
    else if (offset_policy == 1) x = max_left;
    else if (offset_policy == 2) {
      uniform_int_distribution<int> d(left, max_left);
      x = d(rng);
    } else {
      int span = max_left - left;
      uniform_int_distribution<int> d(left, left + span / 3);
      x = d(rng);
    }
    return take_at(x, len);
  }
};

int main(int argc, char** argv) {
  if (argc != 5) {
    cerr << "usage: search_reverse input output target iterations\n";
    return 2;
  }
  ifstream in(argv[1]);
  int width, n;
  if (!(in >> width >> n)) return 3;
  vector<int> cmd(n), len(1), birth(1, -1), death(1, n), id_at(n, 0);
  for (int t = 0; t < n; ++t) {
    if (!(in >> cmd[t])) return 4;
    if (cmd[t] > 0) {
      int id = (int)len.size();
      id_at[t] = id;
      len.push_back(cmd[t]);
      birth.push_back(t);
      death.push_back(n);
    } else if (cmd[t] < 0) {
      death[-cmd[t]] = t;
      id_at[t] = -cmd[t];
    }
  }
  const int target = stoi(argv[3]);
  const int iterations = stoi(argv[4]);
  vector<int> survivors;
  for (int i = 1; i < (int)len.size(); ++i)
    if (death[i] == n) survivors.push_back(i);
  ofstream out(argv[2]);
  if (!out) return 5;

  mt19937 rng(20261019);
  for (int iteration = 0; iteration < iterations; ++iteration) {
    vector<int> order = survivors;
    const int survivor_policy = iteration % 10;
    if (survivor_policy == 1) reverse(order.begin(), order.end());
    else if (survivor_policy == 2)
      stable_sort(order.begin(), order.end(), [&](int a, int b) { return len[a] > len[b]; });
    else if (survivor_policy == 3)
      stable_sort(order.begin(), order.end(), [&](int a, int b) { return len[a] < len[b]; });
    else if (survivor_policy == 4) {
      shuffle(order.begin(), order.end(), rng);
    } else if (survivor_policy == 5)
      stable_sort(order.begin(), order.end(), [&](int a, int b) { return death[a] > death[b]; });
    else if (survivor_policy == 6)
      stable_sort(order.begin(), order.end(), [&](int a, int b) { return death[a] < death[b]; });
    else if (survivor_policy == 7)
      stable_sort(order.begin(), order.end(), [&](int a, int b) {
        return 1LL * len[a] * (death[a] - birth[a]) > 1LL * len[b] * (death[b] - birth[b]);
      });
    else if (survivor_policy == 8)
      stable_sort(order.begin(), order.end(), [&](int a, int b) {
        return 1LL * len[a] * (death[a] - birth[a]) < 1LL * len[b] * (death[b] - birth[b]);
      });
    else if (survivor_policy == 9) {
      shuffle(order.begin(), order.end(), rng);
      if (!order.empty()) rotate(order.begin(), order.begin() + iteration % order.size(), order.end());
    }

    vector<int> pos(len.size(), -1);
    GapSet gaps(target);
    bool ok = true;
    int p = 0;
    // PID 1 is pinned at zero when it survives until the end.
    if (death[1] == n) {
      if (!gaps.take_at(0, len[1])) ok = false;
      else { pos[1] = 0; p = len[1]; }
    }
    for (int id : order) {
      if (!ok) break;
      if (id == 1) continue;
      pos[id] = p;
      if (!gaps.take_at(p, len[id])) { ok = false; break; }
      p += len[id];
    }
    const int policy = iteration % 6;
    const int offset_policy = (iteration / 6) % 4;
    for (int t = n - 1; t >= 0 && ok; --t) {
      const int c = cmd[t];
      if (c > 0) {
        int id = id_at[t];
        if (pos[id] < 0 || !gaps.take_at(pos[id], len[id])) ok = false;
      } else if (c < 0) {
        int id = -c;
        if (pos[id] >= 0) { ok = false; break; }
        if (id == 1) {
          if (!gaps.take_at(0, len[id])) ok = false;
          else pos[id] = 0;
        } else if (!gaps.place(len[id], policy, offset_policy, rng, pos[id])) {
          ok = false;
        }
      }
    }
    if (!ok) continue;
    int extent = 0;
    for (int id = 1; id < (int)len.size(); ++id)
      extent = max(extent, pos[id] + len[id]);
    if (extent <= target) {
      for (int id = 1; id < (int)len.size(); ++id) out << pos[id] << '\n';
      cerr << "FOUND iteration=" << iteration << " extent=" << extent
           << " target=" << target << " survivor_policy=" << survivor_policy
           << " gap_policy=" << policy << " offset_policy=" << offset_policy
           << " seed=20261019\n";
      return 0;
    }
  }
  cerr << "NO_PLAN iterations=" << iterations << " target=" << target << '\n';
  return 1;
}
