#include <algorithm>
#include <array>
#include <cmath>
#include <cstdint>
#include <iostream>
#include <iterator>
#include <map>
#include <set>
#include <utility>
#include <vector>
using I=std::int64_t;

struct Coalescence {
    using G=std::map<I,I>;
    using S=std::set<std::pair<I,I>>;
    struct Plan {
        int cell=-1;
        bool high=false,youngLeft=false;
    };
    struct Stat {
        double sum=0,square=0;
        std::uint64_t stamp=0;
    };
    struct Record {
        I start=0,length=0,rest=0,left=-1,right=-1;
        int cell=-1,low=0,high=0,bucket=0,prev=0,next=0;
        bool placedHigh=false,youngLeft=false;
    };
    std::array<Stat,72> stats{};
    std::array<int,41> heads{};
    std::vector<Record> records=std::vector<Record>(1);
    std::map<I,int> live;
    std::uint64_t tick=0;

    void advance(){++tick;}
    void discount(Stat& s){
        if(s.stamp==tick)return;
        double f=std::exp2(-double(tick-s.stamp)/8192.0);
        s.sum*=f;s.square*=f*f;s.stamp=tick;
    }
    void detach(int id){
        auto& r=records[id];
        if(!r.bucket)return;
        if(r.prev)records[r.prev].next=r.next;
        else heads[r.bucket]=r.next;
        if(r.next)records[r.next].prev=r.prev;
        r.prev=r.next=r.bucket=0;
    }
    void cancel(int id){
        detach(id);records[id].cell=-1;
    }
    void complete(int id,int highMinusLow){
        auto& r=records[id];
        if(r.cell<0)return;
        detach(id);
        auto& s=stats[r.cell];discount(s);
        double value=r.youngLeft?highMinusLow:-highMinusLow;
        s.sum+=value;s.square+=value*value;
        r.cell=-1;
    }
    void refresh(int id,const G& gaps,I trench){
        auto& r=records[id];
        if(r.cell<0)return;
        I left=0,right=0;
        auto it=gaps.lower_bound(r.start);
        if(it!=gaps.begin()){
            auto p=std::prev(it);
            if(p->second==r.start)left=p->second-p->first;
        }
        it=gaps.find(r.start+r.length);
        if(it!=gaps.end())right=it->second-it->first;
        // The growable tail is a different decision context.
        if(r.start+r.length+right==trench){cancel(id);return;}
        if((r.placedHigh?left:right)<r.rest){cancel(id);return;}
        r.left=left?r.start-left:-1;
        r.right=right?r.start+r.length:-1;
        I baseLeft=left-(r.placedHigh?r.rest:0);
        I baseRight=right-(r.placedHigh?0:r.rest);
        r.low=static_cast<int>(std::min<I>(40,std::max(baseLeft,baseRight+r.rest)));
        r.high=static_cast<int>(std::min<I>(40,std::max(baseLeft+r.rest,baseRight)));
        detach(id);
        r.bucket=std::max(r.low,r.high);
        r.next=heads[r.bucket];
        if(r.next)records[r.next].prev=id;
        heads[r.bucket]=id;
    }
    void changed(I start,I end,const G& gaps,I trench){
        auto right=live.find(end);
        if(right!=live.end())refresh(right->second,gaps,trench);
        auto left=live.lower_bound(start);
        if(left!=live.begin()){
            --left;
            const auto& p=records[left->second];
            if(p.start+p.length==start)refresh(left->second,gaps,trench);
        }
    }
    Plan choose(I begin,I end,I length,I trench){
        Plan p;
        I rest=end-begin-length;
        if(rest<=0||rest>=40||end==trench)return p;
        auto right=live.find(end);
        auto left=live.lower_bound(begin);
        if(right==live.end()||left==live.begin())return p;
        --left;
        int lid=left->second,rid=right->second;
        if(records[lid].start+records[lid].length!=begin)return p;
        int young=std::max(lid,rid),old=std::min(lid,rid);
        I youngAge=static_cast<I>(records.size())-young;
        I oldAge=static_cast<I>(records.size())-old;
        int ratio=0;
        while(ratio<3&&oldAge>=2*youngAge){oldAge/=2;++ratio;}
        I yl=records[young].length,ol=records[old].length;
        int order=yl<ol?0:(yl==ol?1:2);
        int restBin=0;
        for(I v=rest;v>1;v/=2)++restBin;
        p.cell=(ratio*3+order)*6+restBin;
        p.youngLeft=lid>rid;
        auto& s=stats[p.cell];discount(s);
        double advantage=p.youngLeft?s.sum:-s.sum;
        // A conservative empirical gate, not a confidence guarantee.
        p.high=advantage>2.0*std::sqrt(s.square+400.0);
        return p;
    }
    void birth(I start,I length,I rest,const Plan& p,const G& gaps,I trench){
        int id=static_cast<int>(records.size());
        Record r;
        r.start=start;r.length=length;r.rest=rest;
        r.cell=p.cell;r.placedHigh=p.high;r.youngLeft=p.youngLeft;
        records.push_back(r);live.emplace(start,id);
        refresh(id,gaps,trench);
    }
    void death(int id){
        // Once the inserted pipe disappears, both local layouts coincide.
        complete(id,0);live.erase(records[id].start);
    }
    void ready(int length,const G& gaps,const S& sizes,I trench){
        I tail=0;
        if(!gaps.empty()){
            auto last=std::prev(gaps.end());
            if(last->second==trench)tail=last->second-last->first;
        }
        for(int b=length;b<=40;++b){
            while(heads[b]){
                int id=heads[b];
                const auto& r=records[id];
                int difference=int(length<=r.high)-int(length<=r.low);
                int value=0;
                if(difference){
                    // All other gaps are identical in the paired layouts.
                    auto it=sizes.lower_bound({length,-1});
                    while(it!=sizes.end()&&(it->second==r.left||it->second==r.right))++it;
                    if(it==sizes.end()){
                        I deficit=I(length)-tail;
                        I growth=deficit>0?((deficit+19)/20)*20:0;
                        value=difference*static_cast<int>(growth);
                    }
                }
                complete(id,value);
            }
        }
    }
};
int main(){
    std::ios::sync_with_stdio(false);std::cin.tie(nullptr);
    std::map<I,I> gaps;
    std::set<std::pair<I,I>> sizes;
    std::vector<std::pair<I,I>> pipes(1);
    I trench=0,command;
    Coalescence coalescence;
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
        coalescence.changed(start,end,gaps,trench);
    };
    while(std::cin>>command&&command){
        coalescence.advance();
        if(command<0){
            auto pid=static_cast<std::size_t>(-command);
            auto p=pipes.at(pid);
            std::cout<<p.first<<'\n'<<std::flush;
            coalescence.death(static_cast<int>(pid));
            add(p.first,p.first+p.second);continue;
        }
        I length=command,digs=0,start=0;
        coalescence.ready(static_cast<int>(length),gaps,sizes,trench);
        auto best=sizes.lower_bound({length,-1});
        if(best==sizes.end()){
            I tail=trench;
            if(!gaps.empty()&&std::prev(gaps.end())->second==trench)tail=std::prev(gaps.end())->first;
            digs=(length-(trench-tail)+19)/20;
            I old=trench;trench+=digs*20;add(old,trench);best=sizes.lower_bound({length,-1});
        }
        auto gap=gaps.find(best->second);
        I begin=gap->first,end=gap->second,rest=end-begin-length;
        auto plan=coalescence.choose(begin,end,length,trench);
        start=plan.high?end-length:begin;
        erase(gap);add(begin,start);add(start+length,end);
        pipes.push_back({start,length});
        coalescence.birth(start,length,rest,plan,gaps,trench);
        std::cout<<digs<<' '<<start<<'\n'<<std::flush;
    }
}
