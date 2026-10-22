#include <algorithm>
#include <array>
#include <cmath>
#include <cstddef>
#include <cstdint>
#include <iostream>
#include <map>
#include <set>
#include <utility>
#include <vector>
using I=std::int64_t;

struct GapFirstFit {
    std::size_t base=1;
    std::vector<I> tree=std::vector<I>(2,0);

    void ensure(std::size_t bucket){
        if(bucket<base)return;
        std::size_t next=base;
        while(next<=bucket)next*=2;
        std::vector<I> expanded(2*next,0);
        for(std::size_t j=0;j<base;++j)expanded[next+j]=tree[base+j];
        for(std::size_t j=next-1;j>0;--j)
            expanded[j]=std::max(expanded[2*j],expanded[2*j+1]);
        base=next;
        tree.swap(expanded);
    }

    void refresh(I address,const std::map<I,I>& gaps){
        const std::size_t bucket=static_cast<std::size_t>(address/20);
        ensure(bucket);
        const I low=static_cast<I>(bucket)*20;
        I maximum=0;
        for(auto it=gaps.lower_bound(low);it!=gaps.end()&&it->first<low+20;++it)
            maximum=std::max(maximum,it->second-it->first);
        std::size_t node=base+bucket;
        if(tree[node]==maximum)return;
        tree[node]=maximum;
        while(node>1){
            node/=2;
            const I value=std::max(tree[2*node],tree[2*node+1]);
            if(tree[node]==value)break;
            tree[node]=value;
        }
    }

    I first(I length,const std::map<I,I>& gaps)const{
        if(tree[1]<length)return -1;
        std::size_t node=1;
        while(node<base){
            if(tree[2*node]>=length)node*=2;
            else node=2*node+1;
        }
        const I low=static_cast<I>(node-base)*20;
        for(auto it=gaps.lower_bound(low);it!=gaps.end()&&it->first<low+20;++it)
            if(it->second-it->first>=length)return it->first;
        return -1;
    }
};

struct SurvivalClasses {
    static constexpr int K=3;
    static constexpr int Classes=160;
    static constexpr int Window=8192;
    static constexpr double Prior=32.0;
    inline static constexpr std::array<I,K> horizons{64,512,4096};

    struct Label {
        int cls=0;
        bool survived=false;
        double logRatio=0;
    };

    struct Model {
        std::array<int,Classes> count{},survived{};
        std::array<int,40> lengthCount{},lengthSurvived{};
        std::array<Label,Window> history{};
        int used=0,write=0,totalSurvived=0;
        double advantage=0;

        double baseline()const{
            return (totalSurvived+1.0)/(used+2.0);
        }

        double predict(int cls)const{
            const int length=cls/4;
            const double pooled=baseline();
            const double byLength=(lengthSurvived[length]+Prior*pooled)
                                 /(lengthCount[length]+Prior);
            return (survived[cls]+Prior*byLength)/(count[cls]+Prior);
        }

        void observe(int cls,bool outcome,double logRatio){
            if(used==Window){
                const Label old=history[write];
                --count[old.cls];
                --lengthCount[old.cls/4];
                survived[old.cls]-=static_cast<int>(old.survived);
                lengthSurvived[old.cls/4]-=static_cast<int>(old.survived);
                totalSurvived-=static_cast<int>(old.survived);
                advantage-=old.logRatio;
            }else ++used;
            history[write]={cls,outcome,logRatio};
            write=(write+1)%Window;
            ++count[cls];
            ++lengthCount[cls/4];
            survived[cls]+=static_cast<int>(outcome);
            lengthSurvived[cls/4]+=static_cast<int>(outcome);
            totalSurvived+=static_cast<int>(outcome);
            advantage+=logRatio;
        }

        bool supported(int cls)const{
            return used>=256&&count[cls]>=32&&totalSurvived>=16
                &&used-totalSurvived>=16&&advantage>=std::log(100.0);
        }

        bool relativelyDurable(int cls)const{
            const int length=cls/4;
            const double pooled=baseline();
            const double byLength=(lengthSurvived[length]+Prior*pooled)
                                 /(lengthCount[length]+Prior);
            const double prediction=predict(cls);
            const double pooledVariance=pooled*(1-pooled)/(used+3.0);
            const double lengthWeight=Prior/(lengthCount[length]+Prior);
            const double lengthVariance=byLength*(1-byLength)
                                       /(lengthCount[length]+Prior+1.0)
                                       +lengthWeight*lengthWeight*pooledVariance;
            const double classWeight=Prior/(count[cls]+Prior);
            const double predictionVariance=prediction*(1-prediction)
                                           /(count[cls]+Prior+1.0)
                                           +classWeight*classWeight*lengthVariance;
            return prediction-pooled>2.5*std::sqrt(predictionVariance+pooledVariance);
        }
    };

    struct Entry {
        I born=0;
        int cls=0;
        bool live=false;
        std::array<double,K> forecast{},baseline{};
    };

    std::array<Model,K> models{};
    std::array<std::size_t,K> cursor{};
    std::vector<Entry> entries;

    SurvivalClasses():entries(1){cursor.fill(1);}

    static int classId(int length,int insertionRun){
        int phase=0;
        for(int value=insertionRun+1;value>1&&phase<3;value/=2)++phase;
        return 4*(length-1)+phase;
    }

    static double bounded(double probability){
        return std::clamp(probability,1e-6,1.0-1e-6);
    }

    void advance(I now){
        for(int k=0;k<K;++k){
            while(cursor[k]<entries.size()){
                const Entry& entry=entries[cursor[k]];
                if(now-entry.born<horizons[k])break;
                const bool outcome=entry.live;
                const double prediction=entry.forecast[k];
                const double pooled=entry.baseline[k];
                const double logRatio=outcome
                    ?std::log(prediction/pooled)
                    :std::log((1-prediction)/(1-pooled));
                models[k].observe(entry.cls,outcome,logRatio);
                ++cursor[k];
            }
        }
    }

    bool durable(int cls)const{
        for(int k=K-1;k>=0;--k)
            if(models[k].supported(cls))return models[k].relativelyDurable(cls);
        return false;
    }

    void insert(I now,int cls){
        Entry entry;
        entry.born=now;
        entry.cls=cls;
        entry.live=true;
        for(int k=0;k<K;++k){
            entry.forecast[k]=bounded(models[k].predict(cls));
            entry.baseline[k]=bounded(models[k].baseline());
        }
        entries.push_back(entry);
    }

    void remove(std::size_t pid){entries.at(pid).live=false;}
};

int main(){
    std::ios::sync_with_stdio(false);std::cin.tie(nullptr);
    std::map<I,I> gaps;
    std::set<std::pair<I,I>> sizes;
    std::vector<std::pair<I,I>> pipes(1);
    I trench=0,command,tick=0;
    int insertionRun=0;
    SurvivalClasses lifetimes;
    GapFirstFit firstFit;
    auto erase=[&](std::map<I,I>::iterator p){
        const I address=p->first;
        sizes.erase({p->second-p->first,p->first});
        gaps.erase(p);
        firstFit.refresh(address,gaps);
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
        firstFit.refresh(start,gaps);
    };
    while(std::cin>>command&&command){
        ++tick;
        lifetimes.advance(tick);
        if(command<0){
            const auto pid=static_cast<std::size_t>(-command);
            auto p=pipes.at(pid);
            lifetimes.remove(pid);
            insertionRun=0;
            std::cout<<p.first<<'\n'<<std::flush;
            add(p.first,p.first+p.second);
            continue;
        }
        I length=command,digs=0,start=0;
        const int cls=SurvivalClasses::classId(static_cast<int>(length),insertionRun);
        ++insertionRun;
        const bool durable=lifetimes.durable(cls);
        auto best=sizes.lower_bound({length,-1});
        if(best==sizes.end()){
            I tail=trench;
            if(!gaps.empty()&&std::prev(gaps.end())->second==trench)tail=std::prev(gaps.end())->first;
            digs=(length-(trench-tail)+19)/20;
            I old=trench;trench+=digs*20;add(old,trench);best=sizes.lower_bound({length,-1});
        }
        I chosen=best->second;
        if(durable&&best->first>length){
            const I candidate=firstFit.first(length,gaps);
            if(candidate>=0&&candidate<chosen)chosen=candidate;
        }
        auto gap=gaps.find(chosen);start=gap->first;I end=gap->second;erase(gap);add(start+length,end);
        pipes.push_back({start,length});
        lifetimes.insert(tick,cls);
        std::cout<<digs<<' '<<start<<'\n'<<std::flush;
    }
}
