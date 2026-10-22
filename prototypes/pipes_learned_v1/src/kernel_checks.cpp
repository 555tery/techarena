#include "allocator.hpp"
#include <cassert>
#include <iostream>
#include <random>
using namespace prototype;
int main() {
    std::mt19937 random(81732999);
    int examined=0;
    for(int trial=0;trial<32;++trial) {
        State state;std::vector<int> alive;std::vector<int> cells;
        for(int step=0;step<800;++step) {
            const bool insert=alive.empty() || random()%100<62;
            if(insert) {
                const int length=1+static_cast<int>(random()%40);
                const auto originalGaps=state.gaps;
                const auto actions=state.candidates(length);
                const auto baseline=state.greedy(length);
                assert(!actions.empty() && actions.size()<=32);
                assert(actions[0].start==baseline.start && actions[0].digs==baseline.digs);
                if(step%17==0)for(const auto& action:actions) {
                    const auto x=state.features(length,action);
                    for(float value:x)assert(std::isfinite(value));
                    State branch=state;branch.place(length,action);branch.validate();
                    assert(state.gaps==originalGaps);
                    for(int j=0;j<length;++j) {
                        const auto coordinate=static_cast<std::size_t>(action.start+j);
                        assert(coordinate>=cells.size() || cells[coordinate]==0);
                    }
                    ++examined;
                }
                const auto chosen=step%3==0?state.greedy(length,true):baseline;
                state.place(length,chosen);
                cells.resize(static_cast<std::size_t>(state.trench),0);
                const int pid=static_cast<int>(state.pipes.size())-1;
                for(int j=0;j<length;++j) {auto& cell=cells[static_cast<std::size_t>(chosen.start+j)];assert(cell==0);cell=pid;}
                alive.push_back(pid);
            } else {
                const auto index=static_cast<std::size_t>(random()%alive.size());
                const int pid=alive[index];alive[index]=alive.back();alive.pop_back();
                const auto pipe=state.pipes[static_cast<std::size_t>(pid)];
                assert(state.remove(pid)==pipe.start);
                for(int j=0;j<pipe.length;++j) {auto& cell=cells[static_cast<std::size_t>(pipe.start+j)];assert(cell==pid);cell=0;}
            }
            state.validate();
            Meter count=0;for(int value:cells)if(value)++count;
            assert(count==state.occupied);
        }
    }
    std::cout<<"25600 commands and "<<examined<<" forced branches independently checked\n";
}
