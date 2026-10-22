#include "allocator.hpp"

void fail(const char*) { __builtin_trap(); }

int main() {
    pipes_custom_bf::Allocator state;
    state.begin();
    state.pipes.push_back(pipes_custom_bf::Pipe{5, 2});
    state.T = 20;
    state.setOperationCount(1);
    state.reconstruct();
    const int x = state.bf(2);
    const int digs = state.place(2, x);
    const int deleted = state.remove(2);
    return (x == 0 && digs == 0 && deleted == 0 &&
            state.gapCount() == 2u && state.operationCount() == 3u) ? 0 : 1;
}
