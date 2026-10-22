#include <algorithm>
#include <array>
#include <cstdint>
#include <cstdlib>
#include <deque>
#include <fstream>
#include <iomanip>
#include <iostream>
#include <limits>
#include <map>
#include <set>
#include <string>
#include <tuple>
#include <vector>

struct Gap {
    int len;
    int stamp;
};
struct Pipe { int start=-1, len=0; bool alive=false; };

// Offline exact simulator for allocation policies. It sees only the current
// command when it chooses a placement; future commands are used only by the
// outer measurement code to compute lower bounds.
struct Allocator {
    std::string policy, tie, side;
    bool preserveTail=false;
    int switchH=0;
    int H=0, nextStamp=0, cursor=0;
    int historyWindow=128, unfitScale=50;
    int rightMaxLength=40;
    std::deque<int> recentLengths;
    std::array<int,41> recentFrequency{};
    std::map<int,Gap> gaps;
    std::map<int,std::pair<int,int>> liveByStart; // start -> (PID,length)
    std::array<std::set<std::pair<int,int>>,42> bySize;
    std::array<std::set<std::pair<int,int>>,42> byAge;
    std::set<std::pair<int,int>> largeByLen; // (length, start), only len>40
    std::map<int,std::set<int>> startsByLen;
    std::map<int,std::set<std::pair<int,int>>> agesByLen;

    Allocator(std::string p, std::string t, std::string s, bool pt, int sh,
              int hw, int us, int rml):policy(p),tie(t),side(s),preserveTail(pt),switchH(sh),
              historyWindow(hw),unfitScale(us),rightMaxLength(rml) {}
    void eraseGap(std::map<int,Gap>::iterator it) {
        int start=it->first, len=it->second.len, stamp=it->second.stamp;
        int bucket=std::min(len,41);
        bySize[bucket].erase({start,stamp});
        byAge[bucket].erase({stamp,start});
        if (len>40) largeByLen.erase({len,start});
        startsByLen[len].erase(start);
        agesByLen[len].erase({stamp,start});
        if(startsByLen[len].empty()) startsByLen.erase(len);
        if(agesByLen[len].empty()) agesByLen.erase(len);
        gaps.erase(it);
    }
    void eraseGap(int start) { auto it=gaps.find(start); if(it!=gaps.end()) eraseGap(it); }
    void addGap(int start,int len) {
        if(len<=0) return;
        int stamp=nextStamp++, bucket=std::min(len,41);
        gaps[start]={len,stamp};
        bySize[bucket].insert({start,stamp});
        byAge[bucket].insert({stamp,start});
        if(len>40) largeByLen.insert({len,start});
        startsByLen[len].insert(start);
        agesByLen[len].insert({stamp,start});
    }
    bool allowed(int start) const {
        if(!preserveTail) return true;
        auto it=gaps.find(start);
        return it==gaps.end() || start+it->second.len!=H;
    }
    int inClass(int bucket, bool high) const {
        const auto &v=bySize[bucket];
        if(!high) {
            for(auto it=v.begin();it!=v.end();++it)
                if(allowed(it->first)) return it->first;
        } else {
            for(auto it=v.rbegin();it!=v.rend();++it)
                if(allowed(it->first)) return it->first;
        }
        return -1;
    }
    void freeInterval(int start,int len) {
        int end=start+len;
        auto it=gaps.lower_bound(start);
        if(it!=gaps.begin()) {
            auto p=std::prev(it);
            if(p->first+p->second.len==start) {
                start=p->first;
                len+=p->second.len;
                eraseGap(p);
            }
        }
        it=gaps.lower_bound(end);
        if(it!=gaps.end() && it->first==end) {
            len+=it->second.len;
            eraseGap(it);
        }
        addGap(start,len);
    }
    int choose(int need) const {
        if(policy=="hist") {
            int best=-1;
            int bestGapLength=0;
            long long bestScore=std::numeric_limits<long long>::max();
            const long long n=static_cast<long long>(recentLengths.size());
            if(recentLengths.empty()) {
                for(auto it=startsByLen.lower_bound(need);it!=startsByLen.end();++it) {
                    for(int start:it->second) if(allowed(start)) return start;
                }
                return -1;
            }
            for(auto it=startsByLen.lower_bound(need);it!=startsByLen.end();++it) {
                const int slack=it->first-need;
                long long score=static_cast<long long>(slack)*n;
                if(slack>0 && slack<=40) {
                    int misses=0;
                    for(int request=slack+1;request<=40;request++) misses+=recentFrequency[request];
                    score+=static_cast<long long>(unfitScale)*misses;
                }
                for(int start:it->second) {
                    if(!allowed(start)) continue;
                    if(score<bestScore || (score==bestScore &&
                       (best<0 || it->first<bestGapLength ||
                        (it->first==bestGapLength && start<best)))) {
                        bestScore=score;
                        bestGapLength=it->first;
                        best=start;
                    }
                }
                if(slack>40) break;
            }
            return best;
        }
        // policies: ff, bf, wf, next; only the current request is used.
        std::string mode=policy;
        if(mode=="hybrid") mode=(H<switchH?"ff":"bf");
        if(mode=="bf" || mode=="bfhi" || mode=="bf-old" || mode=="bf-new") {
            auto it=startsByLen.lower_bound(need);
            for(;it!=startsByLen.end();++it) {
                const int len=it->first;
                if(mode=="bf-old" || mode=="bf-new") {
                    const auto &ages=agesByLen.at(len);
                    if(mode=="bf-old") {
                        for(auto a=ages.begin();a!=ages.end();++a) if(allowed(a->second)) return a->second;
                    } else {
                        for(auto a=ages.rbegin();a!=ages.rend();++a) if(allowed(a->second)) return a->second;
                    }
                } else if(tie!="high") {
                    for(int start:it->second) if(allowed(start)) return start;
                } else {
                    for(auto s=it->second.rbegin();s!=it->second.rend();++s) if(allowed(*s)) return *s;
                }
            }
            return -1;
        }
        if(mode=="wf" || mode=="wfhi") {
            for(auto it=startsByLen.rbegin();it!=startsByLen.rend();++it) {
                if(it->first<need) break;
                if(tie!="high") {
                    for(int start:it->second) if(allowed(start)) return start;
                } else {
                    for(auto s=it->second.rbegin();s!=it->second.rend();++s) if(allowed(*s)) return *s;
                }
            }
            return -1;
        }
        if(mode=="next") {
            int afterBest=-1, wrapBest=-1;
            for(int sz=need;sz<=41;sz++) {
                const auto &v=bySize[sz];
                auto it=v.lower_bound({cursor,-1});
                while(it!=v.end() && !allowed(it->first)) ++it;
                if(it!=v.end() && (afterBest<0 || it->first<afterBest)) afterBest=it->first;
                for(auto jt=v.begin();jt!=v.end() && jt->first<cursor;++jt)
                    if(allowed(jt->first)) { if(wrapBest<0 || jt->first<wrapBest) wrapBest=jt->first; break; }
            }
            return afterBest>=0 ? afterBest : wrapBest;
        }
        // First fit (low or high address). Scan just 41 size indexes.
        int best=-1;
        for(int sz=need;sz<=41;sz++) {
            const auto &v=bySize[sz];
            if(v.empty()) continue;
            int candidate=inClass(sz,tie=="high");
            if(candidate<0) continue;
            if(best<0 || (tie=="high" ? candidate>best : candidate<best)) best=candidate;
        }
        return best;
    }
    int endpoint(int start, int gapLen, int len, int pid) const {
        if(side=="small-right") return len<=rightMaxLength ? start+gapLen-len : start;
        if(side=="right") return start+gapLen-len;
        if(side=="center") return start+(gapLen-len)/2;
        if(side!="near-size" && side!="near-age") return start;
        bool hasLeft=false, hasRight=false;
        int leftLen=0,rightLen=0,leftPid=0,rightPid=0;
        auto it=liveByStart.lower_bound(start);
        if(it!=liveByStart.begin()) {
            auto p=std::prev(it);
            if(p->first+p->second.second==start) {
                hasLeft=true; leftPid=p->second.first; leftLen=p->second.second;
            }
        }
        it=liveByStart.lower_bound(start+gapLen);
        if(it!=liveByStart.end() && it->first==start+gapLen) {
            hasRight=true; rightPid=it->second.first; rightLen=it->second.second;
        }
        if(!hasLeft && hasRight) return start+gapLen-len;
        if(hasLeft && !hasRight) return start;
        if(!hasLeft && !hasRight) return start;
        int leftScore, rightScore;
        if(side=="near-size") {
            leftScore=std::abs(len-leftLen); rightScore=std::abs(len-rightLen);
        } else {
            leftScore=pid-leftPid; rightScore=pid-rightPid;
        }
        return rightScore<leftScore ? start+gapLen-len : start;
    }
    int place(int len, int pid) {
        int start=choose(len);
        if(start>=0) {
            auto it=gaps.find(start);
            int glen=it->second.len;
            eraseGap(it);
            int d=endpoint(start,glen,len,pid);
            if(d>start) addGap(start,d-start);
            if(d+len<start+glen) addGap(d+len,start+glen-(d+len));
            liveByStart[d]={pid,len};
            cursor=d+len;
            return d;
        }
        // When no non-tail gap is chosen, extend the current expandable tail
        // regardless of the gap-selection policy, matching the actual task's
        // natural tail reuse and the reference solver's macro policies.
        int old=H, tailStart=H;
        if(!gaps.empty()) {
            auto it=std::prev(gaps.end());
            if(it->first+it->second.len==H) {
                tailStart=it->first;
                eraseGap(it);
            }
        }
        int tailLen=old-tailStart;
        int digs=std::max(0,(len-tailLen+19)/20);
        H+=digs*20;
        addGap(tailStart+len,H-tailStart-len);
        cursor=tailStart+len;
        liveByStart[tailStart]={pid,len};
        return tailStart;
    }
    void recordLength(int len) {
        recentLengths.push_back(len);
        ++recentFrequency[len];
        if(static_cast<int>(recentLengths.size())>historyWindow) {
            --recentFrequency[recentLengths.front()];
            recentLengths.pop_front();
        }
    }
    void release(int start,int len) {
        liveByStart.erase(start);
        freeInterval(start,len);
    }
};

struct Result {
    double weight=1, kpi=0;
    int n=0, finalH=0, finalLive=0, maxLive=0, lowerH=0;
};

Result simulate(const std::string &path, const std::string &policy,
                const std::string &tie, const std::string &side, bool preserveTail, int switchH,
                int historyWindow, int unfitScale, int rightMaxLength) {
    std::ifstream in(path);
    Result r;
    in>>r.weight>>r.n;
    std::vector<int> ops(r.n);
    for(int &x:ops) in>>x;
    Allocator a(policy,tie,side,preserveTail,switchH,historyWindow,unfitScale,rightMaxLength);
    std::vector<Pipe> pipes(1);
    int live=0, maxLive=0;
    for(int op:ops) {
        if(op>0) {
            int d=a.place(op,static_cast<int>(pipes.size()));
            pipes.push_back({d,op,true});
            a.recordLength(op);
            live+=op;
            maxLive=std::max(maxLive,live);
        } else if(op<0) {
            int id=-op;
            if(id<=0 || id>=int(pipes.size()) || !pipes[id].alive) {
                std::cerr<<"invalid delete id "<<id<<" in "<<path<<"\n"; std::exit(2);
            }
            a.release(pipes[id].start,pipes[id].len);
            pipes[id].alive=false;
            live-=pipes[id].len;
        }
    }
    r.finalH=a.H; r.finalLive=live; r.maxLive=maxLive;
    r.lowerH=((maxLive+19)/20)*20;
    r.kpi=(double)live/a.H;
    return r;
}

int main(int argc,char **argv) {
    if(argc<3) {
        std::cerr<<"usage: pipes_sim policy input... [--tie=low|high|old|new] [--side=left|right|small-right|center|near-size|near-age] [--tail=preserve|consume] [--threshold=H] [--history-window=N] [--unfit-scale=N] [--right-max=N]\n";
        return 2;
    }
    std::string policy=argv[1],tie="low",side="left";
    bool preserveTail=false;
    int switchH=0;
    int historyWindow=128, unfitScale=50;
    int rightMaxLength=40;
    std::vector<std::string> files;
    for(int i=2;i<argc;i++) {
        std::string arg=argv[i];
        if(arg.rfind("--tie=",0)==0) tie=arg.substr(6);
        else if(arg.rfind("--side=",0)==0) side=arg.substr(7);
        else if(arg=="--tail=preserve") preserveTail=true;
        else if(arg.rfind("--threshold=",0)==0) switchH=std::stoi(arg.substr(12));
        else if(arg.rfind("--history-window=",0)==0) historyWindow=std::stoi(arg.substr(17));
        else if(arg.rfind("--unfit-scale=",0)==0) unfitScale=std::stoi(arg.substr(14));
        else if(arg.rfind("--right-max=",0)==0) rightMaxLength=std::stoi(arg.substr(12));
        else files.push_back(arg);
    }
    double total=0, weighted=0;
    for(auto &f:files) {
        auto r=simulate(f,policy,tie,side,preserveTail,switchH,historyWindow,unfitScale,rightMaxLength);
        total+=r.kpi*r.weight; weighted+=r.weight;
        std::cout<<f<<" weight="<<r.weight<<" alive="<<r.finalLive<<" H="<<r.finalH
                 <<" lb="<<r.lowerH<<" gap="<<(r.finalH-r.lowerH)
                 <<" KPI="<<std::setprecision(9)<<r.kpi<<"\n";
    }
    std::cout<<"weighted_score="<<std::setprecision(12)<<total<<" total_weight="<<weighted<<"\n";
}
