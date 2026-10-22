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

    constexpr int MaxLag=32;
    struct CorrelationModel{
        std::array<double,64> samples{};
        int count=0,cursor=0,lastEpisode=0;
        double sum=0,squares=0;
        void observe(double value,int episode){
            if(count==static_cast<int>(samples.size())){
                double old=samples[cursor];
                sum-=old;squares-=old*old;
            }else ++count;
            samples[cursor]=value;
            sum+=value;squares+=value*value;
            cursor=(cursor+1)%static_cast<int>(samples.size());
            lastEpisode=episode;
        }
        double lower(int episode)const{
            if(count<8||episode-lastEpisode>static_cast<int>(samples.size()))return 0;
            double mean=sum/count;
            double variance=std::max(0.0,squares/count-mean*mean);
            return std::max(0.0,mean-3.0*std::sqrt((variance+1.0/count)/count));
        }
    };
    std::array<std::array<CorrelationModel,2>,MaxLag+1> correlations{};
    std::array<std::array<int,2>,MaxLag+1> episodeTrials{},episodeHits{};
    std::array<std::array<double,2>,MaxLag+1> linkStrength{};
    std::vector<int> birthRun(1,0),deathEpisode(1,0);
    int insertionRun=1,deletionEpisode=0;
    bool deleting=false;
    I liveCount=0,episodePopulation=0,episodeDeaths=0;
    struct CohortStats{
        I supported=0,candidates=0,dpVetoes=0,changed=0,right=0;
    }cohortStats;

    auto observeDeletion=[&](int pid){
        if(!deleting){
            deleting=true;++deletionEpisode;
            episodePopulation=liveCount;episodeDeaths=0;
            episodeTrials={};episodeHits={};
        }
        deathEpisode[pid]=deletionEpisode;
        ++episodeDeaths;
        int allocated=static_cast<int>(pipes.size())-1;
        for(int lag=1;lag<=MaxLag;++lag){
            for(int side=-1;side<=1;side+=2){
                int other=pid+side*lag;
                if(other<=0||other>allocated)continue;
                int context=birthRun[pid]==birthRun[other];
                if(deathEpisode[other]==0)
                    ++episodeTrials[lag][context];
                else if(deathEpisode[other]==deletionEpisode)
                    ++episodeHits[lag][context];
            }
        }
        --liveCount;
    };
    auto finishDeletionEpisode=[&](){
        if(!deleting)return;
        double background=episodePopulation>1
            ?static_cast<double>(episodeDeaths-1)/(2*episodePopulation-episodeDeaths-1)
            :0.0;
        for(int lag=1;lag<=MaxLag;++lag){
            for(int context=0;context<2;++context){
                int trials=episodeTrials[lag][context];
                if(trials){
                    double excess=static_cast<double>(episodeHits[lag][context])/trials-background;
                    correlations[lag][context].observe(excess,deletionEpisode);
                }
                linkStrength[lag][context]=correlations[lag][context].lower(deletionEpisode);
            }
        }
        deleting=false;++insertionRun;
    };
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
        if(command<0){
            previousLength=0;
            int pid=static_cast<int>(-command);
            auto p=pipes.at(static_cast<std::size_t>(pid));
            std::cout<<p.first<<'\n'<<std::flush;
            observeDeletion(pid);
            add(p.first,p.first+p.second);
            continue;
        }
        finishDeletionEpisode();
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
        auto parentGap=gaps.find(best->second);
        auto chosenGap=parentGap;
        I parentWidth=parentGap->second-parentGap->first;
        I chosenStart=parentGap->first;

        struct Link{int pid=0;double credit=0;};
        std::array<Link,MaxLag> links{};
        std::array<Link,4> probes{};
        int linkCount=0;
        int newPid=static_cast<int>(pipes.size());
        for(int lag=1;lag<=MaxLag;++lag){
            int other=newPid-lag;
            if(other<=0)break;
            if(deathEpisode[other]!=0)continue;
            int context=birthRun[other]==insertionRun;
            double strength=linkStrength[lag][context];
            if(strength<=0)continue;
            Link link{other,std::min(length,pipes[other].second)*strength};
            links[linkCount++]=link;
            for(auto& probe:probes)
                if(link.credit>probe.credit)std::swap(link,probe);
        }
        if(linkCount)++cohortStats.supported;
        auto edgeCredit=[&](I position){
            double credit=0;
            for(int i=0;i<linkCount;++i){
                const auto& p=pipes[links[i].pid];
                if(position==p.first+p.second||position+length==p.first)
                    credit+=links[i].credit;
            }
            return credit;
        };
        double highestCredit=edgeCredit(chosenStart);
        auto consider=[&](std::map<I,I>::iterator candidate,bool fromRight){
            if(candidate==gaps.end()||candidate==parentGap)return;
            I width=candidate->second-candidate->first;
            if(width<length)return;
            ++cohortStats.candidates;
            if(width!=parentWidth){
                if(width>K||parentWidth>K){
                    ++cohortStats.dpVetoes;return;
                }
                int a=static_cast<int>(parentWidth);
                int b=static_cast<int>(width);
                int current=static_cast<int>(length);
                double gain=pairValue[pairIndex(a,b-current)][current]
                           -pairValue[pairIndex(a-current,b)][current];
                if(gain< -1e-10){
                    ++cohortStats.dpVetoes;return;
                }
            }
            I position=fromRight?candidate->second-length:candidate->first;
            double credit=edgeCredit(position);
            if(credit>highestCredit+1e-10){
                highestCredit=credit;
                chosenGap=candidate;chosenStart=position;
            }
        };
        for(const auto& probe:probes){
            if(!probe.pid)continue;
            const auto& p=pipes[probe.pid];
            auto after=gaps.find(p.first+p.second);
            if(after!=gaps.end())consider(after,false);
            auto before=gaps.lower_bound(p.first);
            if(before!=gaps.begin()){
                --before;
                if(before->second==p.first)consider(before,true);
            }
        }
        if(chosenGap!=parentGap){
            ++cohortStats.changed;
            if(chosenStart>chosenGap->first)++cohortStats.right;
        }
        start=chosenStart;
        I gapStart=chosenGap->first,end=chosenGap->second;
        erase(chosenGap);
        add(gapStart,start);add(start+length,end);
        pipes.push_back({start,length});
        birthRun.push_back(insertionRun);deathEpisode.push_back(0);++liveCount;
        std::cout<<digs<<' '<<start<<'\n'<<std::flush;
    }
#ifdef COHORT_DIAGNOSTICS
    std::cerr<<"cohort supported="<<cohortStats.supported
             <<" candidates="<<cohortStats.candidates
             <<" dp_vetoes="<<cohortStats.dpVetoes
             <<" changed_gap="<<cohortStats.changed
             <<" right="<<cohortStats.right<<'\n';
#endif
}
