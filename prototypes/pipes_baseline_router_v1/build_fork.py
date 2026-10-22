#!/usr/bin/env python3
"""Mechanically instrument exact baseline; fail on unexpected source drift."""
from pathlib import Path
import difflib
import hashlib
import json

ROOT=Path(__file__).resolve().parent


def main():
    original=(ROOT/'baseline/solution.cpp').read_text()
    assert hashlib.sha256(original.encode()).hexdigest()=='c19945111834e5969e2f58f0b6503851b35e7642a9bd77f9f70c118ee3bb736c'
    prefix,body=original.split('class Allocator {',1)
    body=body[:body.rindex('\nint main() {')]
    counts={}

    def replace(old,new,count=1):
        nonlocal body
        assert body.count(old)==count,(old,body.count(old))
        body=body.replace(old,new);counts[old[:90]]=count

    replace('    void place(int length) {','    void place(int length) {\n        ++routerClock;lastRouterActions.clear();lastRouterChosen=0;lastRouterProtected=false;')
    replace('        if (cohortSlabActive && cohortSlabUsed < cohortSlabExpectedCount) {',
        '        if (cohortSlabActive && cohortSlabUsed < cohortSlabExpectedCount) {\n            lastRouterProtected=true;++routerProtected;')
    replace('            start = consumeAtSide(gap, length, highSide);',
        '''            const bool protectedBranch=cohortSlabActive || parityCohortMode ||
                alternatingDeleteMode || geometricLaneActive || rearmReverse ||
                additiveNextAlignment || counterfactualCapacityChoice || lifoStackLane;
            const auto routed=routerDecision(length,gap->first,highSide,protectedBranch);
            gap=freeByStart.find(routed.first);highSide=routed.second;
            start = consumeAtSide(gap, length, highSide);''')
    replace('pipes.push_back(Pipe{start, length, true, sizeCohort});',
        'pipes.push_back(Pipe{start, length, true, sizeCohort});\n        routerBirth.push_back(routerClock);routerOccupied+=length;',2)
    replace('    void remove(std::int64_t pid) {','    void remove(std::int64_t pid) {\n        ++routerClock;')
    replace("        std::cout << pipe.start << '\\n' << std::flush;",
        "        if(!routerQuiet)std::cout << pipe.start << '\\n' << std::flush;\n"
        "        routerOccupied-=pipe.length;routerDeletionAges.push_back(routerClock-routerBirth[index]);\n"
        "        routerDeletionLengths.push_back(pipe.length);\n"
        "        if(routerDeletionAges.size()>128){routerDeletionAges.pop_front();routerDeletionLengths.pop_front();}")
    replace('        const std::int64_t gapLength = end - start;\n        const int cohort = gapCohort.at(start);',
        '        const std::int64_t gapLength = end - start;\n        --routerGapHistogram[routerGapBucket(gapLength)];\n        const int cohort = gapCohort.at(start);')
    replace('        freeByStart.emplace(start, end);','        freeByStart.emplace(start, end);\n        ++routerGapHistogram[routerGapBucket(end-start)];')
    replace('    static void printPlacement(std::int64_t digs, std::int64_t start) {\n        std::cout',
        '    void printPlacement(std::int64_t digs, std::int64_t start) {\n        lastPlacementDigs=digs;lastPlacementStart=start;\n        if(!routerQuiet)std::cout')
    marker='    bool hasLongAdditiveSizeTrend(int currentLength) const {'
    replace(marker,(ROOT/'src/router_members.inc').read_text()+'\n'+marker)
    extra='''#include <cmath>
#include <stdexcept>
#if defined(USE_ROUTER)
#include "trained_router.hpp"
#endif
'''
    result=extra+prefix+'class Allocator {'+body
    (ROOT/'src/baseline_fork.hpp').write_text(result)
    diff=''.join(difflib.unified_diff(original.splitlines(True),result.splitlines(True),fromfile='exact-baseline',tofile='instrumented-baseline'))
    (ROOT/'reports/instrumentation.diff').write_text(diff)
    (ROOT/'reports/instrumentation.json').write_text(json.dumps({'baseline_sha256':hashlib.sha256(original.encode()).hexdigest(),'fork_sha256':hashlib.sha256(result.encode()).hexdigest(),'replacements':counts},indent=2)+'\n')
    print('instrumented fork written; baseline untouched')


if __name__=='__main__':main()
