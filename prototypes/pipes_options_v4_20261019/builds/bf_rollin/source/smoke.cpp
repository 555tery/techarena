#include "policy.hpp"
#include <cassert>
#include <iostream>
static std::array<double,4> anchored(const std::array<float,128>&){return {{0,0,0,1}};}
int main() {
    using namespace options_v4;
    State state,bf;Cursor cursor;Counters counters;
    const int commands[]={7,7,6,-2,5,-1,-3,15};
    const Meter expected[]={0,13,7,15,0};int placed=0;
    for(int command:commands) {
        if(command>0) {
            const auto c=choose(state,command,cursor,counters,anchored,true);
            assert(c.action.start==expected[placed++]);state.place(command,c.action);
            bf.place(command,bf.greedy(command));
        } else {state.remove(-command);afterDeletion(state,cursor,counters);bf.remove(-command);}
        state.validate();bf.validate();
    }
    assert(state.trench==20 && bf.trench==40);
    assert(counters.decisions==2 && counters.continuation_placements==3 && counters.active_crossed_deletions==1);
    State large;large.place(40,large.greedy(40));large.place(40,large.greedy(40));large.remove(1);large.remove(2);
    assert(optionAction(large,39,2).start==0);large.validate();
    State limit;Cursor active;Counters guard;
    for(int i=0;i<14;++i){const auto c=choose(limit,1,active,guard,anchored,true);limit.place(1,c.action);}
    assert(guard.cancellations==1 && active.remaining==0 && guard.fallback==1);
    std::cout<<"{\"status\":\"pass\",\"anchored_trench\":20,\"bf_trench\":40,\"continuation_placements\":3,\"active_crossed_deletions\":1,\"guard_cancellations\":1,\"bucket40_checked\":true}\n";
}
