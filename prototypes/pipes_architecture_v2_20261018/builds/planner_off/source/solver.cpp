#include "scenario_planner.hpp"
#include <iostream>

int main() {
    std::ios::sync_with_stdio(false);std::cin.tie(nullptr);
    prototype::State state;h1::Model model;h1::Planner planner;
    try {
        int command;
        while(std::cin>>command && command!=0) {
            if(command>0) {
                if(command>40)throw std::runtime_error("invalid length");
                const auto action=planner.choose(state,model,command);
                state.place(command,action);
                model.insertion(command,static_cast<int>(state.pipes.size())-1,state.clock);
                std::cout<<action.digs<<' '<<action.start<<'\n'<<std::flush;
            } else {
                const int id=-command;
                if(id<=0 || static_cast<std::size_t>(id)>=state.pipes.size())throw std::runtime_error("invalid PID");
                planner.deletion(state,id);
                model.deletion(state,id);
                const auto start=state.remove(id);
                std::cout<<start<<'\n'<<std::flush;
            }
#if PLANNER_VALIDATE
            state.validate();
#endif
        }
        planner.report();
    } catch(const std::exception& e) {
        std::fprintf(stderr,"H1 ERROR: %s\n",e.what());return 2;
    }
    return 0;
}
