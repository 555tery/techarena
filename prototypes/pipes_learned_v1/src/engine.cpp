#include "allocator.hpp"
#include <fstream>
#include <iomanip>
#include <iostream>
#include <sstream>
#include <string>
#if defined(USE_LEARNED)
#include "trained_model.hpp"
#endif

namespace {
using namespace prototype;
#if defined(OFFLINE_LABELS)
struct Input { double weight=1;std::vector<int> commands; };
Input readInput(const std::string& path) {
    std::ifstream in(path);Input result;int n=0;if(!(in>>result.weight>>n) || n<0 || n>200000)throw std::runtime_error("input header");
    result.commands.resize(static_cast<std::size_t>(n));for(int& c:result.commands)if(!(in>>c) || c==0 || c>40)throw std::runtime_error("input commands");
    return result;
}
#endif
std::uint64_t nnCalls=0,nnChanges=0;
Action choose(const State& state,int length,const std::string& mode) {
    if(mode=="right")return state.greedy(length,true);
    const Action control=state.greedy(length);
#if defined(USE_LEARNED)
    if(mode=="model" && (state.pipes.size()-1)%8==0) {
        const auto actions=state.candidates(length);if(actions.size()<2)return control;
        ++nnCalls;
        const float base=learned_model::score(state.features(length,actions[0]));
        float best=base;std::size_t index=0;
        for(std::size_t i=1;i<actions.size();++i) {
            const float score=learned_model::score(state.features(length,actions[i]));
            if(score<best) {best=score;index=i;}
        }
        if(index>0 && base-best>learned_model::kMargin) {++nnChanges;return actions[index];}
    }
#else
    if(mode=="model")throw std::runtime_error("model not compiled");
#endif
    return control;
}
#if defined(OFFLINE_LABELS)
Meter continuation(State state,const std::vector<int>& commands,std::size_t next) {
    for(std::size_t j=next;j<commands.size();++j) {
        const int c=commands[j];if(c>0)state.place(c,state.greedy(c));else state.remove(-c);
    }
    state.validate();return state.trench;
}
void header(std::ostream& out) {
    out<<"stream,state,action,is_base,target_trench,base_trench,kind";
    for(int j=0;j<128;++j)out<<",f"<<j;out<<'\n';
}
int label(int argc,char** argv) {
    if(argc!=9)throw std::runtime_error("label input output stream cadence max_states rollin coverage_output");
    const auto input=readInput(argv[2]);std::ofstream out(argv[3]);const std::string stream=argv[4];
    const int warmup=std::stoi(argv[5]),maxStates=std::stoi(argv[6]);const std::string rollin=argv[7];
    const auto totalPlacements=static_cast<std::size_t>(std::count_if(input.commands.begin(),input.commands.end(),[](int c){return c>0;}));
    const std::size_t stride=std::max<std::size_t>(1,(totalPlacements>2*static_cast<std::size_t>(warmup)?totalPlacements-2*static_cast<std::size_t>(warmup):1)/static_cast<std::size_t>(std::max(1,maxStates)));
    std::size_t nextSample=static_cast<std::size_t>(warmup);
    const bool coverageEnabled=std::string(argv[8])!="-";
    std::ofstream coverage;
    if(coverageEnabled) {coverage.open(argv[8]);coverage<<"stream,state,command,shortlist,exhaustive,base_trench,best_shortlist,best_exhaustive\n";}
    header(out);
    out<<std::setprecision(9);State state;int states=0,rows=0,signal=0,coverageStates=0;
    std::uint64_t operations=0;double gain=0;
    for(std::size_t i=0;i<input.commands.size();++i) {
        const int c=input.commands[i];
        if(c<0) {state.remove(-c);continue;}
        const auto placed=state.pipes.size()-1;
        if(placed>=nextSample && states<maxStates) {
            nextSample+=stride;
            const auto actions=state.candidates(c);
            if(actions.size()>1) {
                state.validate();std::vector<Meter> outcomes;
                for(const auto& action:actions) {
                    State branch=state;branch.place(c,action);
                    outcomes.push_back(continuation(std::move(branch),input.commands,i+1));
                    operations+=input.commands.size()-i-1;
                }
                const Meter base=outcomes[0],best=*std::min_element(outcomes.begin(),outcomes.end());
                gain+=static_cast<double>(base-best);if(base-best>=20)++signal;
                for(std::size_t a=0;a<actions.size();++a) {
                    out<<stream<<','<<states<<','<<a<<','<<(a==0?1:0)<<','<<outcomes[a]<<','<<base<<','<<actions[a].kind;
                    const auto x=state.features(c,actions[a]);for(float f:x)out<<','<<f;out<<'\n';++rows;
                }
                if(coverageEnabled && coverageStates<1) {
                    const auto expanded=state.exhaustive(c);
                    if(!expanded.empty()) {
                        Meter exhaustiveBest=std::numeric_limits<Meter>::max();
                        for(const auto& action:expanded) {
                            State branch=state;branch.place(c,action);
                            exhaustiveBest=std::min(exhaustiveBest,continuation(std::move(branch),input.commands,i+1));
                            operations+=input.commands.size()-i-1;
                        }
                        coverage<<stream<<','<<states<<','<<i<<','<<actions.size()<<','<<expanded.size()<<','<<base<<','<<best<<','<<exhaustiveBest<<'\n';++coverageStates;
                    }
                }
                ++states;
            }
        }
        state.place(c,choose(state,c,rollin));
    }
    state.validate();
    std::cout<<"{\"stream\":\""<<stream<<"\",\"states\":"<<states<<",\"rows\":"<<rows<<",\"signal_states\":"<<signal<<",\"mean_one_step_hindsight_gain_m\":"<<(states?gain/states:0)<<",\"suffix_commands\":"<<operations<<",\"final_rollin_trench\":"<<state.trench<<"}\n";
    return 0;
}
#endif
} // namespace
int main(int argc,char** argv) {
    try {
#if defined(OFFLINE_LABELS)
        if(argc>1 && std::string(argv[1])=="label")return label(argc,argv);
#endif
        std::string mode="greedy";
#if defined(USE_LEARNED)
        mode="model";
#endif
        if(argc>1)mode=argv[1];
        if(mode!="greedy" && mode!="right" && mode!="model")throw std::runtime_error("unknown mode");
        std::ios::sync_with_stdio(false);std::cin.tie(nullptr);
        State state;int command=0;
        while(std::cin>>command) {
            if(command==0) {state.validate();std::cerr<<"nn_calls="<<nnCalls<<" nn_changes="<<nnChanges<<"\n";return 0;}
            if(command>0) {const auto action=choose(state,command,mode);state.place(command,action);std::cout<<action.digs<<' '<<action.start<<'\n'<<std::flush;}
            else {const auto start=state.remove(-command);std::cout<<start<<'\n'<<std::flush;}
        }
        return 0;
    } catch(const std::exception& error) {std::cerr<<"prototype error: "<<error.what()<<'\n';return 2;}
}
