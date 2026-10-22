#include <algorithm>
#include <array>
#include <cmath>
#include <cstdint>
#include <iostream>
#include <map>
#include <set>
#include <tuple>
#include <utility>
#include <vector>
using I=std::int64_t;

struct Pipe {
    I start=0;
    int length=0;
    bool alive=false;
};

struct Gap {
    I end=0;
    double history=-1.0;
};

struct LifetimeModel {
    static constexpr std::array<I,3> horizons{32,256,2048};
    struct Counts {
        I n=0,survived=0;
        void observe(bool alive){++n;survived+=alive;}
        std::pair<double,double> interval() const {
            if(!n)return {0.0,1.0};
            double count=static_cast<double>(n);
            double p=static_cast<double>(survived)/count;
            double denominator=1.0+9.0/count;
            double center=(p+4.5/count)/denominator;
            double radius=3.0*std::sqrt(p*(1.0-p)/count+2.25/(count*count))/denominator;
            return {std::max(0.0,center-radius),std::min(1.0,center+radius)};
        }
    };
    struct Forecast {
        bool usable=false;
        double mean=0.0,low=0.0,high=0.0;
    };
    std::array<std::array<Counts,3>,41> by_length{};
    std::array<Counts,3> pooled{};

    void advance(I current_pid,const std::vector<Pipe>& pipes){
        for(std::size_t k=0;k<horizons.size();++k){
            I old_pid=current_pid-horizons[k];
            if(old_pid<=0)continue;
            const Pipe& p=pipes[static_cast<std::size_t>(old_pid)];
            by_length[p.length][k].observe(p.alive);
            pooled[k].observe(p.alive);
        }
    }

    double completed_score(I age) const {
        double score=0.0;
        for(I horizon:horizons)score+=age>=horizon;
        return score;
    }

    Forecast predict(int length) const {
        Forecast forecast;
        double global_low=0.0,global_high=0.0;
        for(std::size_t k=0;k<horizons.size();++k){
            const Counts& local=by_length[length][k];
            if(!local.n)return {};
            forecast.mean+=static_cast<double>(local.survived)/static_cast<double>(local.n);
            auto bounds=local.interval();
            forecast.low+=bounds.first;
            forecast.high+=bounds.second;
            auto global_bounds=pooled[k].interval();
            global_low+=global_bounds.first;
            global_high+=global_bounds.second;
        }
        forecast.usable=forecast.low>global_high||forecast.high<global_low;
        return forecast;
    }
};
int main(){
    std::ios::sync_with_stdio(false);std::cin.tie(nullptr);
    std::map<I,Gap> gaps;
    std::set<std::pair<I,I>> sizes;
    std::set<std::tuple<I,double,I>> history_index;
    std::vector<Pipe> pipes(1);
    LifetimeModel lifetime;
    I trench=0,command;
    auto erase=[&](std::map<I,Gap>::iterator p){
        I span=p->second.end-p->first;
        sizes.erase({span,p->first});
        if(p->second.history>=0.0)
            history_index.erase({span,p->second.history,p->first});
        gaps.erase(p);
    };
    auto mix=[](double a,I a_length,double b,I b_length){
        if(a<0.0||b<0.0)return -1.0;
        return (a*static_cast<double>(a_length)+b*static_cast<double>(b_length))
            /static_cast<double>(a_length+b_length);
    };
    auto add=[&](I start,I end,double history){
        if(start>=end)return;
        auto it=gaps.lower_bound(start);
        if(it!=gaps.begin()){
            auto prev=std::prev(it);
            if(prev->second.end==start){
                history=mix(history,end-start,prev->second.history,start-prev->first);
                start=prev->first;
                erase(prev);
            }
        }
        it=gaps.lower_bound(start);
        if(it!=gaps.end()&&it->first==end){
            history=mix(history,end-start,it->second.history,it->second.end-it->first);
            end=it->second.end;
            erase(it);
        }
        gaps[start]=Gap{end,history};
        sizes.insert({end-start,start});
        if(history>=0.0)history_index.insert({end-start,history,start});
    };
    while(std::cin>>command&&command){
        if(command<0){
            I pid=-command;
            Pipe& p=pipes.at(static_cast<std::size_t>(pid));
            std::cout<<p.start<<'\n'<<std::flush;
            I age=static_cast<I>(pipes.size())-1-pid;
            p.alive=false;
            add(p.start,p.start+p.length,lifetime.completed_score(age));
            continue;
        }
        I length=command,digs=0,start=0;
        lifetime.advance(static_cast<I>(pipes.size()),pipes);
        auto best=sizes.lower_bound({length,-1});
        if(best==sizes.end()){
            I tail=trench;
            if(!gaps.empty()&&std::prev(gaps.end())->second.end==trench)tail=std::prev(gaps.end())->first;
            digs=(length-(trench-tail)+19)/20;
            I old=trench;trench+=digs*20;add(old,trench,-1.0);best=sizes.lower_bound({length,-1});
        }
        I selected=best->second;
        auto forecast=lifetime.predict(static_cast<int>(length));
        auto original=gaps.find(selected);
        if(forecast.usable&&original->second.history>=0.0){
            I span=best->first;
            double original_history=original->second.history;
            double difference=original_history-forecast.mean;
            double best_cost=difference*difference;
            auto consider=[&](auto candidate){
                if(candidate==history_index.end()||std::get<0>(*candidate)!=span)return;
                double history=std::get<1>(*candidate);
                I address=std::get<2>(*candidate);
                double low_gain=(original_history-history)
                    *(original_history+history-2.0*forecast.low);
                double high_gain=(original_history-history)
                    *(original_history+history-2.0*forecast.high);
                if(std::min(low_gain,high_gain)<=1e-10)return;
                double delta=history-forecast.mean;
                double cost=delta*delta;
                if(cost<best_cost-1e-12||
                   (std::abs(cost-best_cost)<=1e-12&&address<selected)){
                    selected=address;
                    best_cost=cost;
                }
            };
            auto upper=history_index.lower_bound({span,forecast.mean,-1});
            consider(upper);
            if(upper!=history_index.begin()){
                auto lower=std::prev(upper);
                if(std::get<0>(*lower)==span){
                    auto first=history_index.lower_bound({span,std::get<1>(*lower),-1});
                    consider(first);
                }
            }
        }
        auto gap=gaps.find(selected);
        start=gap->first;
        I end=gap->second.end;
        double history=gap->second.history;
        erase(gap);
        add(start+length,end,history);
        pipes.push_back(Pipe{start,static_cast<int>(length),true});
        std::cout<<digs<<' '<<start<<'\n'<<std::flush;
    }
}
