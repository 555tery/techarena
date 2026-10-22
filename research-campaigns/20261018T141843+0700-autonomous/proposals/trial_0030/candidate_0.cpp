#include <algorithm>
#include <array>
#include <cmath>
#include <cstdint>
#include <iostream>
#include <map>
#include <set>
#include <utility>
#include <vector>
using I=std::int64_t;

struct ConditionalPrices {
    static constexpr int K=40,Window=4096,Cap=2*K;
    static constexpr double discount=31.0/32.0;
    using Index=std::set<std::pair<I,I>>;
    std::array<int,K+1> histogram{},outgoing{};
    std::array<std::array<int,K+1>,K+1> transitions{};
    std::array<int,Window> history{};
    std::array<double,K+1> probability{};
    std::array<double,Cap+1> value{};
    int used=0,head=0,previous=0;
    std::uint64_t seen=0,pricedAt=0;
    bool priced=false;
    double conditionalWeight=0.5;
    std::uint64_t comparisons=0,overrides=0,conditionalFlips=0;
    double logLossGain=0.0;

    void observe(int length){
        // Evaluate the arrived symbol before updating either predictor.
        const double pooled=(histogram[length]+0.5)/(used+0.5*K);
        if(previous){
            const double conditional=(transitions[previous][length]+K*pooled)
                                     /(outgoing[previous]+K);
            const double mixture=(1.0-conditionalWeight)*pooled
                                 +conditionalWeight*conditional;
            logLossGain+=std::log(mixture/pooled);
            const double posterior=conditionalWeight*conditional/mixture;
            constexpr double share=1.0/Window;
            conditionalWeight=(1.0-share)*posterior+0.5*share;
        }
        if(used==Window){
            const int oldest=history[head];
            const int successor=history[(head+1)%Window];
            --histogram[oldest];
            --transitions[oldest][successor];
            --outgoing[oldest];
        }else{
            ++used;
        }
        if(previous){
            ++transitions[previous][length];
            ++outgoing[previous];
        }
        history[head]=length;
        head=(head+1)%Window;
        ++histogram[length];
        previous=length;
        ++seen;
    }

    void refresh(){
        for(int length=1;length<=K;++length)
            probability[length]=(histogram[length]+0.5)/(used+0.5*K);
        value.fill(0.0);
        double fittingProbability=0.0;
        for(int capacity=1;capacity<=Cap;++capacity){
            if(capacity<=K)fittingProbability+=probability[capacity];
            double reward=0.0;
            for(int length=1;length<=std::min(capacity,K);++length)
                reward+=probability[length]
                       *(length+discount*value[capacity-length]);
            value[capacity]=reward/(1.0-discount*(1.0-fittingProbability));
        }
        pricedAt=seen;
        priced=true;
    }

    Index::iterator choose(Index& sizes,Index::iterator best,int length){
        if(best==sizes.end()||best->first==length||best->first>Cap)return best;
        auto alternative=sizes.lower_bound({best->first+1,-1});
        if(alternative==sizes.end()||alternative->first>Cap)return best;
        if(!priced||seen-pricedAt>=64)refresh();

        std::array<double,K+1> forecast{};
        for(int next=1;next<=K;++next){
            const double conditional=(transitions[previous][next]
                                      +K*probability[next])
                                     /(outgoing[previous]+K);
            forecast[next]=(1.0-conditionalWeight)*probability[next]
                          +conditionalWeight*conditional;
        }
        // Only the first future arrival uses the conditional forecast.
        auto conditionalValue=[&](int capacity){
            double result=discount*value[capacity];
            for(int next=1;next<=std::min(capacity,K);++next)
                result+=forecast[next]
                       *(next+discount*(value[capacity-next]-value[capacity]));
            return result;
        };
        const int first=static_cast<int>(best->first);
        const int second=static_cast<int>(alternative->first);
        const double pooledFirst=value[first]-value[first-length];
        const double pooledSecond=value[second]-value[second-length];
        const bool pooledChange=pooledSecond+1e-9<pooledFirst;
        const double conditionalFirst=conditionalValue(first)
                                     -conditionalValue(first-length);
        const double conditionalSecond=conditionalValue(second)
                                      -conditionalValue(second-length);
        const bool change=conditionalSecond+1e-9<conditionalFirst;
        ++comparisons;
        conditionalFlips+=change!=pooledChange;
        if(change){++overrides;return alternative;}
        return best;
    }
};

int main(){
    std::ios::sync_with_stdio(false);std::cin.tie(nullptr);
    std::map<I,I> gaps;
    std::set<std::pair<I,I>> sizes;
    std::vector<std::pair<I,I>> pipes(1);
    I trench=0,command;
    ConditionalPrices pricing;
    auto erase=[&](std::map<I,I>::iterator p){sizes.erase({p->second-p->first,p->first});gaps.erase(p);};
    auto add=[&](I start,I end){
        if(start>=end)return;
        auto it=gaps.lower_bound(start);
        if(it!=gaps.begin()){
            auto prev=std::prev(it);
            if(prev->second==start){start=prev->first;erase(prev);}
        }
        it=gaps.lower_bound(start);
        if(it!=gaps.end()&&it->first==end){end=it->second;erase(it);}
        gaps[start]=end;sizes.insert({end-start,start});
    };
    while(std::cin>>command&&command){
        if(command<0){auto p=pipes.at(static_cast<std::size_t>(-command));std::cout<<p.first<<'\n'<<std::flush;add(p.first,p.first+p.second);continue;}
        I length=command,digs=0,start=0;
        pricing.observe(static_cast<int>(length));
        auto best=sizes.lower_bound({length,-1});
        if(best==sizes.end()){
            I tail=trench;
            if(!gaps.empty()&&std::prev(gaps.end())->second==trench)tail=std::prev(gaps.end())->first;
            digs=(length-(trench-tail)+19)/20;
            I old=trench;trench+=digs*20;add(old,trench);best=sizes.lower_bound({length,-1});
        }
        best=pricing.choose(sizes,best,static_cast<int>(length));
        auto gap=gaps.find(best->second);start=gap->first;I end=gap->second;erase(gap);add(start+length,end);
        pipes.push_back({start,length});std::cout<<digs<<' '<<start<<'\n'<<std::flush;
    }
}
