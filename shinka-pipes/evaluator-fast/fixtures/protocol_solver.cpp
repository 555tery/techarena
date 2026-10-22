// Transport fixtures only: an intentionally simple append-only solver.
#include <chrono>
#include <iostream>
#include <string>
#include <thread>
#include <vector>
using namespace std;

int main(int argc, char** argv) {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);
    string mode = argc > 1 ? argv[1] : "valid";
    int command, trench = 0, placements = 0;
    bool first = true;
    vector<int> positions(1, -1);
    while (cin >> command) {
        if (!command) {
            if (mode == "after_zero") cout << "0\n" << flush;
            if (mode == "no_exit") this_thread::sleep_for(chrono::seconds(3));
            return mode == "nonzero_exit" ? 7 : 0;
        }
        if (first) {
            if (mode == "eof") return 0;
            if (mode == "no_flush") {
                cout << "1 0\n";
                this_thread::sleep_for(chrono::seconds(3));
                return 0;
            }
            if (mode == "partial") {
                cout << "1 " << flush;
                this_thread::sleep_for(chrono::seconds(3));
                return 0;
            }
            if (mode == "missing_lf") { cout << "1 0" << flush; return 0; }
            if (mode == "empty") { cout << "\n" << flush; return 0; }
            if (mode == "extra") { cout << "1 0 3\n" << flush; return 0; }
            if (mode == "one_token") { cout << "1\n" << flush; return 0; }
            if (mode == "noninteger") { cout << "1.5 0\n" << flush; return 0; }
            if (mode == "nonascii") { cout << "\xff 0\n" << flush; return 0; }
            if (mode == "too_long") { cout << "1 0" << string(4093, ' ') << "\n" << flush; return 0; }
            if (mode == "unterminated_long") {
                cout << string(4200, ' ') << flush;
                this_thread::sleep_for(chrono::seconds(3));
                return 0;
            }
            if (mode == "out_of_trench") { cout << "0 0\n" << flush; return 0; }
            if (mode == "negative_dig") { cout << "-1 0\n" << flush; return 0; }
            if (mode == "out_of_range") { cout << "1 100000001\n" << flush; return 0; }
            if (mode == "stderr_pressure") cerr << string(262144, 'x') << flush;
        }
        string response;
        if (command > 0) {
            ++placements;
            int digs = (command + 19) / 20, shift = trench;
            if (mode == "overlap" && placements == 2) { digs = 0; shift = 0; }
            response = to_string(digs) + " " + to_string(shift);
            positions.push_back(shift);
            trench += digs * 20;
        } else {
            response = to_string(positions.at(-command));
            if (mode == "wrong_delete") response = "999";
            if (mode == "delete_extra") response += " 1";
        }
        if (mode == "signed") {
            auto split = response.find(' ');
            response = split == string::npos ? "+000" + response
                : "+000" + response.substr(0, split) + " +000" + response.substr(split + 1);
        }
        if (mode == "max_line" && first) response += string(4095 - response.size(), ' ');
        response += "\n";
        if (mode == "fragmented") {
            for (char c : response) cout << c << flush;
        } else {
            cout << response << flush;
        }
        first = false;
    }
    return 0;
}
