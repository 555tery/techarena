#include <algorithm>
#include <array>
#include <cstdint>
#include <cmath>
#include <iostream>
#include <map>
#include <set>
#include <utility>
#include <vector>
using I=std::int64_t;
struct DeletionBondEvidence{
    std::array<unsigned char,512> samples{};
    int used=0,head=0,hits=0,referenceHits=0,discordant=0;
    void observe(bool hit,bool reference){
        auto adjust=[&](unsigned char state,int delta){
            if(state&1)hits+=delta;
            if(state&2)referenceHits+=delta;
            if(state==1||state==2)discordant+=delta;
        };
        if(used==static_cast<int>(samples.size()))adjust(samples[head],-1);
        else ++used;
        unsigned char state=static_cast<unsigned char>((hit?1:0)|(reference?2:0));
        samples[head]=state;adjust(state,1);
        if(++head==static_cast<int>(samples.size()))head=0;
    }
    double strength()const{
        if(used<64||hits<=referenceHits||2*hits<=used)return 0;
        // Evidence margins, not an IID significance claim.
        double excess=hits-referenceHits-4.0*std::sqrt(discordant+1.0);
        if(excess<=0||2.0*hits-used<=4.0*std::sqrt(static_cast<double>(used)))return 0;
        return excess/used;
    }
};
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
    constexpr int BondLag=64,DeathWindow=16,ActiveBonds=4;
    std::array<DeletionBondEvidence,BondLag+1> bonds{};
    std::map<I,int> liveAt;
    std::vector<I> deathAt(1,0);
    I deletionClock=0;
    struct PendingDeath{int pid=0,lastPid=0;I when=0;};
    std::array<PendingDeath,DeathWindow> pending{};
    auto observeDeletion=[&](int pid){
        ++deletionClock;deathAt[pid]=deletionClock;
        std::size_t slot=static_cast<std::size_t>(deletionClock%DeathWindow);
        PendingDeath old=pending[slot];
        if(old.pid){
            for(int d=1;d<=BondLag;++d){
                for(int direction=-1;direction<=1;direction+=2){
                    int target=old.pid+direction*d;
                    int control=old.pid+direction*(d+BondLag);
                    if(target<=0||control<=0||target>old.lastPid||control>old.lastPid)continue;
                    I targetDeath=deathAt[target],controlDeath=deathAt[control];
                    if((targetDeath&&targetDeath<=old.when)||
                       (controlDeath&&controlDeath<=old.when))continue;
                    bool hit=targetDeath>old.when&&targetDeath<=deletionClock;
                    bool reference=controlDeath>old.when&&controlDeath<=deletionClock;
                    bonds[d].observe(hit,reference);
                }
            }
        }
        pending[slot]={pid,static_cast<int>(pipes.size()-1),deletionClock};
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
            observeDeletion(pid);liveAt.erase(p.first);
            std::cout<<p.first<<'\n'<<std::flush;
            add(p.first,p.first+p.second);continue;
        }
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
        auto gap=gaps.find(best->second);
        const I selectedWidth=best->first;
        const int newPid=static_cast<int>(pipes.size());
        bool placeAtRight=false;
        std::array<double,BondLag+1> weight{};
        std::array<int,ActiveBonds> active{};
        for(int d=1;d<=BondLag&&d<newPid;++d){
            if(deathAt[newPid-d])continue;
            weight[d]=bonds[d].strength();
            if(weight[d]<=0)continue;
            int position=0;
            while(position<ActiveBonds&&active[position]&&
                  weight[active[position]]>=weight[d])++position;
            if(position<ActiveBonds){
                for(int j=ActiveBonds-1;j>position;--j)active[j]=active[j-1];
                active[position]=d;
            }
        }
        if(active[0]){
            double selectedScore=0;
            auto bondAt=[&](int owner){
                int d=newPid-owner;
                return d>0&&d<=BondLag?weight[d]:0.0;
            };
            auto consider=[&](std::map<I,I>::iterator candidate){
                if(candidate==gaps.end()||candidate->second-candidate->first!=selectedWidth)return;
                auto right=liveAt.lower_bound(candidate->first);
                double leftBond=0,rightBond=0;
                if(right!=liveAt.begin()){
                    auto left=std::prev(right);
                    const auto& p=pipes[left->second];
                    if(p.first+p.second==candidate->first)leftBond=bondAt(left->second);
                }
                if(right!=liveAt.end()&&right->first==candidate->second)
                    rightBond=bondAt(right->second);
                double score=leftBond;
                bool atRight=false;
                if(selectedWidth==length)score+=rightBond;
                else if(rightBond>score+1e-12){score=rightBond;atRight=true;}
                if(score>selectedScore+1e-12){
                    selectedScore=score;gap=candidate;placeAtRight=atRight;
                }
            };
            consider(gap);
            for(int d:active){
                if(!d)break;
                const auto& peer=pipes[newPid-d];
                consider(gaps.find(peer.first+peer.second));
                auto before=gaps.lower_bound(peer.first);
                if(before!=gaps.begin()){
                    --before;
                    if(before->second==peer.first)consider(before);
                }
            }
        }
        I begin=gap->first,end=gap->second;
        start=placeAtRight?end-length:begin;
        erase(gap);add(begin,start);add(start+length,end);
        pipes.push_back({start,length});deathAt.push_back(0);
        liveAt.emplace(start,newPid);
        std::cout<<digs<<' '<<start<<'\n'<<std::flush;
    }
}
