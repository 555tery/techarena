#include <algorithm>
#include <array>
#include <cstdint>
#include <iostream>
#include <map>
#include <set>
#include <utility>
#include <vector>
using I=std::int64_t;
int main(){
    std::ios::sync_with_stdio(false);std::cin.tie(nullptr);
    std::map<I,I> gaps;
    std::set<std::pair<I,I>> sizes;
    std::vector<std::pair<I,I>> pipes(1);
    I trench=0,command;
    constexpr int K=40;
    constexpr int PairStates=(K+1)*(K+2)/2;
    std::array<std::set<I>,K+1> small;
    std::array<I,K+1> frequency{},outgoing{};
    std::array<std::array<I,K+1>,K+1> transitions{};
    std::array<std::array<double,K+1>,PairStates> pairValue{};
    I insertions=0,nextRebuild=1;
    int previousLength=0;
    auto pairIndex=[](int a,int b){
        if(a>b)std::swap(a,b);
        return b*(b+1)/2+a;
    };
    auto rebuild=[&](){
        std::array<double,K+1> marginal{};
        std::array<std::array<double,K+1>,K+1> probability{};
        for(int length=1;length<=K;++length)
            marginal[length]=(frequency[length]+0.5)/(insertions+0.5*K);
        for(int last=1;last<=K;++last)
            for(int length=1;length<=K;++length)
                probability[last][length]=
                    (transitions[last][length]+K*marginal[length])/
                    (outgoing[last]+static_cast<double>(K));

        // Expected accepted volume until the first request fitting neither hole.
        // Both legal placements are evaluated after observing the request size.
        for(int b=1;b<=K;++b){
            for(int a=0;a<=b;++a){
                std::array<double,K+1> offer{};
                for(int length=1;length<=b;++length){
                    double continuation=pairValue[pairIndex(a,b-length)][length];
                    if(length<=a)
                        continuation=std::max(continuation,
                            pairValue[pairIndex(a-length,b)][length]);
                    offer[length]=length+continuation;
                }
                int state=pairIndex(a,b);
                for(int last=1;last<=K;++last){
                    double value=0;
                    for(int length=1;length<=b;++length)
                        value+=probability[last][length]*offer[length];
                    pairValue[state][last]=value;
                }
            }
        }
    };
    auto observeInsertion=[&](int length){
        ++insertions;++frequency[length];
        if(previousLength){
            ++transitions[previousLength][length];
            ++outgoing[previousLength];
        }
        previousLength=length;
        if(insertions==nextRebuild){
            rebuild();
            // Refresh cadence controls computation only.
            nextRebuild+=std::min<I>(nextRebuild,1024);
        }
    };
    auto erase=[&](std::map<I,I>::iterator p){
        I width=p->second-p->first;
        if(width<=K)small[static_cast<int>(width)].erase(p->first);
        sizes.erase({width,p->first});gaps.erase(p);
    };
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
        if(end-start<=K)small[static_cast<int>(end-start)].insert(start);
    };
    while(std::cin>>command&&command){
        if(command<0){previousLength=0;auto p=pipes.at(static_cast<std::size_t>(-command));std::cout<<p.first<<'\n'<<std::flush;add(p.first,p.first+p.second);continue;}
        I length=command,digs=0,start=0;
        observeInsertion(static_cast<int>(length));
        auto best=sizes.lower_bound({length,-1});
        if(best==sizes.end()){
            I tail=trench;
            if(!gaps.empty()&&std::prev(gaps.end())->second==trench)tail=std::prev(gaps.end())->first;
            digs=(length-(trench-tail)+19)/20;
            I old=trench;trench+=digs*20;add(old,trench);best=sizes.lower_bound({length,-1});
        }
        if(best->first>length&&best->first<K){
            int base=static_cast<int>(best->first);
            int current=static_cast<int>(length);
            int selected=base;
            double bestGain=0;
            for(int width=base+1;width<=K;++width){
                if(small[width].empty())continue;
                double parentValue=pairValue[pairIndex(base-current,width)][current];
                double alternativeValue=pairValue[pairIndex(base,width-current)][current];
                double gain=alternativeValue-parentValue;
                if(gain>bestGain+1e-10){
                    bestGain=gain;selected=width;
                }
            }
            if(selected!=base)
                best=sizes.find({selected,*small[selected].begin()});
        }
        auto gap=gaps.find(best->second);start=gap->first;I end=gap->second;erase(gap);add(start+length,end);
        pipes.push_back({start,length});std::cout<<digs<<' '<<start<<'\n'<<std::flush;
    }
}
