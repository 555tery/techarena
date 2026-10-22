#include "policy.hpp"
#include <fstream>
#include <iomanip>
#include <iostream>
#include <string>

int main(int argc,char** argv) {
    try {
        trajectory::Weights weights{};
        if(argc>1) {
            std::ifstream file(argv[1]);
            for(double& w:weights) if(!(file>>w)) throw std::runtime_error("invalid weights file");
        } else {
            for(int j=0;j<trajectory::Parameters;++j) weights[static_cast<std::size_t>(j)]=std::sin(j+1)*0.3;
        }
        prototype::State state;trajectory::Counters counters;
        int command;
        while(std::cin>>command && command!=0) {
            if(command>0) {
                const auto action=trajectory::choose(state,command,weights,true,counters);
                state.place(command,action);
                std::cout<<action.digs<<' '<<action.start<<'\n';
            } else std::cout<<state.remove(-command)<<'\n';
            state.validate();
        }
        std::cerr<<"check T="<<state.trench<<" F="<<state.occupied<<" changed="<<counters.changed<<'\n';
        if(argc==1) {
            std::ofstream parity("parity_rows.tsv");parity<<std::setprecision(17);
            for(int row=0;row<256;++row) {
                trajectory::Features x{};
                for(int j=0;j<trajectory::Input;++j) x[static_cast<std::size_t>(j)]=std::sin((row+1)*(j+3)*0.17)*2;
                parity<<trajectory::score(x,weights);
                for(double value:x) parity<<'\t'<<value;
                parity<<'\n';
            }
        }
    } catch(const std::exception& e) {std::cerr<<e.what()<<'\n';return 2;}
}
