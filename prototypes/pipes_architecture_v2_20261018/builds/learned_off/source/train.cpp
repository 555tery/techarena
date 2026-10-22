#include "policy.hpp"
#include <filesystem>
#include <fstream>
#include <iomanip>
#include <iostream>
#include <numeric>
#include <sstream>
#include <string>

using trajectory::Weights;
struct Stream {std::string family,path,hash;std::vector<int> commands;};
struct Result {prototype::Meter trench=0,final=0;double reward=0;trajectory::Counters counters;};

Result episode(const Stream& stream,const Weights& weights,bool enabled) {
    prototype::State state;trajectory::Counters counters;
    for(std::size_t i=0;i<stream.commands.size();++i) {
        const int command=stream.commands[i];
        if(command>0) state.place(command,trajectory::choose(state,command,weights,enabled,counters));
        else state.remove(-command);
        if(i%128==0) state.validate();
    }
    state.validate();
    if(state.trench<=0) throw std::runtime_error("empty terminal trench");
    return {state.trench,state.occupied,static_cast<double>(state.occupied)/state.trench,counters};
}

void saveWeights(const std::filesystem::path& path,const Weights& weights) {
    std::ofstream file(path);file<<std::setprecision(17);
    for(double w:weights) file<<w<<'\n';
    if(!file) throw std::runtime_error("cannot write weights");
}

struct Random {
    std::uint64_t state=2026101802ULL;
    double uniform() {
        state^=state>>12;state^=state<<25;state^=state>>27;
        const std::uint64_t bits=state*2685821657736338717ULL;
        return (static_cast<double>(bits>>11)+0.5)/9007199254740992.0;
    }
    double normal() {return std::sqrt(-2*std::log(uniform()))*std::cos(6.283185307179586476925286766559*uniform());}
};

int main(int argc,char** argv) {
    try {
        if(argc!=3) throw std::runtime_error("usage: train STREAMS.tsv OUT_DIRECTORY");
        std::ifstream manifest(argv[1]);
        std::vector<Stream> streams;
        std::string line;
        while(std::getline(manifest,line)) {
            std::istringstream row(line);Stream s;
            if(!std::getline(row,s.family,'\t') || !std::getline(row,s.path,'\t') || !std::getline(row,s.hash,'\t'))
                throw std::runtime_error("bad stream manifest row");
            std::ifstream file(s.path);double fixtureWeight=0;int n=0,command=0;
            if(!(file>>fixtureWeight>>n) || n!=2000) throw std::runtime_error("training input requires weight header and n=2000");
            for(int i=0;i<n;++i) {
                if(!(file>>command) || command==0) throw std::runtime_error("invalid or missing training command");
                s.commands.push_back(command);
            }
            if(file>>command) throw std::runtime_error("trailing training input token");
            streams.push_back(std::move(s));
        }
        if(streams.size()!=24) throw std::runtime_error("require exactly24 streams");
        std::vector<std::string> families;
        std::vector<std::vector<std::size_t>> familyStreams;
        for(std::size_t i=0;i<streams.size();++i) {
            auto it=std::find(families.begin(),families.end(),streams[i].family);
            if(it==families.end()) {families.push_back(streams[i].family);familyStreams.emplace_back();it=std::prev(families.end());}
            familyStreams[static_cast<std::size_t>(it-families.begin())].push_back(i);
        }
        if(families.size()!=6) throw std::runtime_error("require six families");
        for(const auto& entries:familyStreams) if(entries.size()!=4) throw std::runtime_error("require four streams per family");
        const std::filesystem::path output(argv[2]);
        std::filesystem::create_directories(output/"policies");
        std::ofstream history(output/"episodes.csv"),generations(output/"generations.csv");
        history<<"episode,generation,candidate,policy_file,input_file,input_sha256,family,F,T,reward,control_reward,paired_delta,legal,placements,eligible,decisions,changed,candidates,interior,tail,right_endpoint\n";
        generations<<"generation,replicate,rank0_candidate,rank0_delta,rank1_candidate,rank1_delta,mean_std,min_std,max_std\n";
        history<<std::setprecision(17);generations<<std::setprecision(17);
        int episodes=0;
        const auto record=[&](int gen,int candidate,const std::string& policy,const Stream& stream,const Result& r,double control) {
            history<<++episodes<<','<<gen<<','<<candidate<<','<<policy<<','<<stream.path<<','<<stream.hash<<','<<stream.family<<','
                <<r.final<<','<<r.trench<<','<<r.reward<<','<<control<<','<<r.reward-control<<",true,"
                <<r.counters.placements<<','<<r.counters.eligible<<','<<r.counters.decisions<<','<<r.counters.changed<<','
                <<r.counters.candidates<<','<<r.counters.interior<<','<<r.counters.tail<<','<<r.counters.rightEndpoint<<'\n';
            history.flush();
        };
        Weights mean{},deviation{};deviation.fill(0.35);
        saveWeights(output/"policies/control.weights",mean);
        std::vector<double> controls;
        for(const auto& stream:streams) {
            const auto r=episode(stream,mean,false);controls.push_back(r.reward);
            record(0,-1,"policies/control.weights",stream,r,r.reward);
        }
        Random rng;
        for(int gen=1;gen<=8;++gen) {
            std::array<Weights,8> population;
            std::array<double,8> fitness{};
            for(int candidate=0;candidate<8;++candidate) {
                auto& weights=population[static_cast<std::size_t>(candidate)];
                for(int j=0;j<trajectory::Parameters;++j) weights[static_cast<std::size_t>(j)]=mean[static_cast<std::size_t>(j)]+deviation[static_cast<std::size_t>(j)]*rng.normal();
                const std::string policy="policies/gen"+std::to_string(gen)+"_candidate"+std::to_string(candidate)+".weights";
                saveWeights(output/policy,weights);
                for(const auto& entries:familyStreams) {
                    const auto index=entries[static_cast<std::size_t>((gen-1)%4)];
                    const auto r=episode(streams[index],weights,true);
                    fitness[static_cast<std::size_t>(candidate)]+=(r.reward-controls[index])/6;
                    record(gen,candidate,policy,streams[index],r,controls[index]);
                }
            }
            std::array<int,8> ranking{};std::iota(ranking.begin(),ranking.end(),0);
            std::stable_sort(ranking.begin(),ranking.end(),[&](int a,int b){return fitness[static_cast<std::size_t>(a)]>fitness[static_cast<std::size_t>(b)];});
            for(int j=0;j<trajectory::Parameters;++j) {
                const auto index=static_cast<std::size_t>(j);
                const double a=population[static_cast<std::size_t>(ranking[0])][index],b=population[static_cast<std::size_t>(ranking[1])][index];
                const double eliteMean=(a+b)/2,eliteVariance=((a-eliteMean)*(a-eliteMean)+(b-eliteMean)*(b-eliteMean))/2;
                mean[index]=0.65*mean[index]+0.35*eliteMean;
                deviation[index]=std::max(0.06,std::sqrt(0.65*deviation[index]*deviation[index]+0.35*eliteVariance));
            }
            if(gen==4 || gen==8) saveWeights(output/("checkpoint_gen"+std::to_string(gen)+".weights"),mean);
            double average=0;for(double sd:deviation) average+=sd/trajectory::Parameters;
            generations<<gen<<','<<(gen-1)%4<<','<<ranking[0]<<','<<fitness[static_cast<std::size_t>(ranking[0])]<<','
                <<ranking[1]<<','<<fitness[static_cast<std::size_t>(ranking[1])]<<','<<average<<','
                <<*std::min_element(deviation.begin(),deviation.end())<<','<<*std::max_element(deviation.begin(),deviation.end())<<'\n';
            generations.flush();
            std::cerr<<"generation="<<gen<<" episodes="<<episodes<<" best_train_paired="<<fitness[static_cast<std::size_t>(ranking[0])]<<'\n';
        }
        if(episodes!=408) throw std::runtime_error("episode budget mismatch");
        std::cerr<<"complete episodes="<<episodes<<'\n';
    } catch(const std::exception& e) {std::cerr<<"training error: "<<e.what()<<'\n';return 2;}
}
