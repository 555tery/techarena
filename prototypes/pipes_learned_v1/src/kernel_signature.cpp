#ifndef ALLOCATOR_HEADER
#define ALLOCATOR_HEADER "allocator.hpp"
#endif
#include ALLOCATOR_HEADER
#include <cstring>
#include <iostream>
#include <random>

int main() {
    using namespace prototype;
    std::mt19937 random(82711999);
    std::uint64_t signature=1469598103934665603ULL, actions=0;
    const auto add=[&](std::uint64_t value){signature^=value;signature*=1099511628211ULL;};
    for(int trial=0;trial<32;++trial) {
        State state;std::vector<int> alive;
        for(int step=0;step<1200;++step) {
            if(alive.empty() || random()%100<62) {
                const int length=1+static_cast<int>(random()%40);
                const auto candidates=state.candidates(length);
                for(const auto& action:candidates) {
                    ++actions;add(static_cast<std::uint64_t>(action.start));
                    add(static_cast<std::uint64_t>(action.digs));add(static_cast<std::uint64_t>(action.kind));
                    for(float f:state.features(length,action)) {
                        std::uint32_t bits=0;std::memcpy(&bits,&f,sizeof(bits));add(bits);
                    }
                }
                if(step%13==0)for(const auto& action:state.exhaustive(length)) {
                    add(static_cast<std::uint64_t>(action.start));add(static_cast<std::uint64_t>(action.digs));
                }
                const auto& chosen=candidates[static_cast<std::size_t>(random())%candidates.size()];
                state.place(length,chosen);alive.push_back(static_cast<int>(state.pipes.size())-1);
            } else {
                const auto index=static_cast<std::size_t>(random())%alive.size();
                state.remove(alive[index]);alive[index]=alive.back();alive.pop_back();
            }
        }
        state.validate();add(static_cast<std::uint64_t>(state.trench));
    }
    std::cout<<signature<<' '<<actions<<'\n';
}
