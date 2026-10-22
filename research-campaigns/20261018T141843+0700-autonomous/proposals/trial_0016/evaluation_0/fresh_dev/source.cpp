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
    constexpr int MaxLength=40;
    constexpr int ValueLimit=2*MaxLength;
    std::array<int,ValueLimit+2> gapCount{};
    std::array<int,MaxLength+1> recent{};
    std::array<int,2048> history{};
    std::array<double,ValueLimit+1> value{};
    std::size_t historyPos=0;
    int recentDeletes=0;
    I liveCount=0;
    std::uint64_t step=0,modelStep=0;
    bool modelDirty=true;
    I retiredStart=0,retiredLength=0;
    int deletionRun=0,previousLength=0;
    std::array<int,512> renewalHistory{};
    std::size_t renewalPos=0;
    int renewalBalance=0,renewalDiscordant=0;
    auto observe=[&](int event){
        int old=history[historyPos];
        if(old>0){
            if(--recent[old]==0)modelDirty=true;
        }else if(old<0){
            if(--recentDeletes==0)modelDirty=true;
        }
        history[historyPos]=event;
        historyPos=(historyPos+1)%history.size();
        if(event>0){
            if(recent[event]++==0)modelDirty=true;
        }else{
            if(recentDeletes++==0)modelDirty=true;
        }
        ++step;
    };
    auto rebuildValue=[&](){
        std::array<double,MaxLength+1> rate{};
        I fitting=gapCount[ValueLimit+1];
        for(int g=ValueLimit;g>=1;--g){
            fitting+=gapCount[g];
            if(g<=MaxLength)
                rate[g]=double(recent[g])/double(std::max<I>(1,fitting));
        }
        double expiry=2.0*recentDeletes/double(std::max<I>(1,liveCount));
        value.fill(0.0);
        for(int g=1;g<=ValueLimit;++g){
            int top=std::min(g,MaxLength);
            if(expiry==0.0){
                for(int s=1;s<=top;++s)
                    if(rate[s]>0.0)
                        value[g]=std::max(value[g],double(s)+value[g-s]);
                continue;
            }
            std::array<double,MaxLength+1> reward{};
            std::uint64_t active=0;
            double numerator=0.0,denominator=expiry;
            for(int s=1;s<=top;++s){
                if(rate[s]==0.0)continue;
                reward[s]=double(s)+value[g-s];
                numerator+=rate[s]*reward[s];
                denominator+=rate[s];
                active|=std::uint64_t(1)<<s;
            }
            double estimate=numerator/denominator;
            for(;;){
                bool removed=false;
                for(int s=1;s<=top;++s){
                    std::uint64_t bit=std::uint64_t(1)<<s;
                    if((active&bit)&&reward[s]<estimate){
                        numerator-=rate[s]*reward[s];
                        denominator-=rate[s];
                        active&=~bit;
                        removed=true;
                    }
                }
                if(!removed)break;
                estimate=numerator/denominator;
            }
            value[g]=std::clamp(estimate,0.0,double(g));
        }
        modelStep=step;
        modelDirty=false;
    };
    auto erase=[&](std::map<I,I>::iterator p){
        I length=p->second-p->first;
        --gapCount[static_cast<std::size_t>(std::min<I>(ValueLimit+1,length))];
        sizes.erase({length,p->first});gaps.erase(p);
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
        ++gapCount[static_cast<std::size_t>(std::min<I>(ValueLimit+1,end-start))];
    };
    while(std::cin>>command&&command){
        observe(command>0?static_cast<int>(command):-1);
        if(command<0){
            auto p=pipes.at(static_cast<std::size_t>(-command));
            retiredStart=p.first;
            retiredLength=p.second;
            ++deletionRun;
            std::cout<<p.first<<'\n'<<std::flush;
            add(p.first,p.first+p.second);
            --liveCount;
            continue;
        }
        I length=command,digs=0,start=0;
        bool restoreCandidate=false;
        if(deletionRun==1&&previousLength!=0){
            bool hit=retiredLength==length;
            bool control=previousLength==length;
            restoreCandidate=hit&&renewalBalance>0&&
                renewalBalance*renewalBalance>16*renewalDiscordant;
            int vote=int(hit)-int(control);
            int old=renewalHistory[renewalPos];
            renewalBalance+=vote-old;
            renewalDiscordant+=int(vote!=0)-int(old!=0);
            renewalHistory[renewalPos]=vote;
            renewalPos=(renewalPos+1)%renewalHistory.size();
        }
        deletionRun=0;
        previousLength=static_cast<int>(length);
        auto best=sizes.lower_bound({length,-1});
        if(best==sizes.end()){
            I tail=trench;
            if(!gaps.empty()&&std::prev(gaps.end())->second==trench)tail=std::prev(gaps.end())->first;
            digs=(length-(trench-tail)+19)/20;
            I old=trench;trench+=digs*20;add(old,trench);best=sizes.lower_bound({length,-1});
        }
        if(best->first>length&&best->first<=ValueLimit){
            if(modelDirty||step-modelStep>=64)rebuildValue();
            int chosen=static_cast<int>(best->first);
            int request=static_cast<int>(length);
            double loss=value[chosen]-value[chosen-request];
            for(int g=chosen+1;g<=ValueLimit;++g){
                if(gapCount[g]==0)continue;
                double candidate=value[g]-value[g-request];
                if(candidate+1e-9<loss){
                    loss=candidate;
                    chosen=g;
                }
            }
            if(chosen!=best->first)best=sizes.lower_bound({chosen,-1});
        }
        auto gap=gaps.find(best->second);
        start=gap->first;
        I end=gap->second;
        if(restoreCandidate){
            auto home=gaps.upper_bound(retiredStart);
            if(home!=gaps.begin()){
                --home;
                I homeLength=home->second-home->first;
                if(home->first<=retiredStart&&
                   retiredStart+length<=home->second&&
                   (best->first!=length||homeLength==length)){
                    if(modelDirty||step-modelStep>=64)rebuildValue();
                    auto potential=[&](I amount)->double{
                        if(amount<=ValueLimit)
                            return value[static_cast<std::size_t>(amount)];
                        return double(amount-ValueLimit)+value[ValueLimit];
                    };
                    double parentLoss=potential(end-start)-
                        potential(end-start-length);
                    double restoreLoss=potential(homeLength)-
                        potential(retiredStart-home->first)-
                        potential(home->second-retiredStart-length);
                    if(restoreLoss<=parentLoss+1e-9){
                        gap=home;
                        start=retiredStart;
                        end=gap->second;
                    }
                }
            }
        }
        I gapStart=gap->first;
        erase(gap);
        add(gapStart,start);
        add(start+length,end);
        ++liveCount;
        pipes.push_back({start,length});std::cout<<digs<<' '<<start<<'\n'<<std::flush;
    }
}
