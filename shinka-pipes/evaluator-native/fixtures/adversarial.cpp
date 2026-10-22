#include <chrono>
#include <ctime>
#include <iostream>
#include <string>
#include <vector>
using namespace std;

int main(int argc, char** argv) {
    ios::sync_with_stdio(false); cin.tie(nullptr);
    string mode = argv[1];
    int command, trench = 0;
    bool first = true;
    vector<int> positions(1, -1);
    volatile char* memory = nullptr;
    while (cin >> command) {
        if (!command) {
            if (mode == "zero_flood") cout << string(262144, 'x') << '\n' << flush;
            delete[] memory;
            return 0;
        }
        if (first) {
            if (mode == "cpu") {
                clock_t until = clock() + CLOCKS_PER_SEC / 10;
                volatile unsigned value = 1;
                while (clock() < until) value = value * 1664525U + 1013904223U;
            }
            if (mode == "memory") {
                // macOS may compress older pages before wait4 records RSS.
                // Use a wide margin over 256 MiB; the measured RSS is asserted.
                constexpr size_t bytes = 1024ULL * 1024 * 1024;
                memory = new char[bytes];
                auto words = reinterpret_cast<volatile unsigned long long*>(memory);
                unsigned long long state = 123456789;
                for (size_t i = 0; i < bytes / sizeof(*words); ++i) {
                    state ^= state << 13; state ^= state >> 7; state ^= state << 17;
                    words[i] = state;
                }
            }
            if (mode == "prefill") { cout << "1 0\n1 20\n0\n1 40\n20\n" << flush; first = false; continue; }
            if (mode == "huge_integer") { cout << string(4000, '9') << " 0\n" << flush; return 0; }
            if (mode == "huge_zero") { cout << "+" << string(4080, '0') << "1 +0000\n" << flush; positions.push_back(0); trench=20; first=false; continue; }
        }
        if (mode == "prefill") continue;
        if (command > 0) {
            int digs = (command + 19) / 20;
            cout << digs << ' ' << trench << '\n' << flush;
            positions.push_back(trench); trench += 20 * digs;
        } else cout << positions.at(-command) << '\n' << flush;
        first = false;
    }
}
