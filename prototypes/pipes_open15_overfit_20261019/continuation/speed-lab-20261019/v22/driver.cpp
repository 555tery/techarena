#include "winapi_test_shim.hpp"
#include "bench_api.hpp"
#include <cstdint>
#include <cstring>
#include <climits>
#include <cstdio>
#include <cstdlib>
#include <cerrno>
#include <chrono>
#include <ctime>
#define PIPES_WINAPI_TEST
#define main candidateMain
#include "solution.cpp"
#undef main
int main(int argc,char**argv){
 if(argc<3)return 2;loadBenchmarkFixtures(argv[1],argc>3&&std::atoi(argv[3]));
 const unsigned repeats=std::atoi(argv[2]);
 for(unsigned i=0;i<benchmarkCases();++i){startBenchmarkCase(i,true);if(!setjmp(benchmarkFinish))candidateMain();}
 const auto cpuStart=std::clock();const auto start=std::chrono::steady_clock::now();
 for(unsigned r=0;r<repeats;++r)for(unsigned i=0;i<benchmarkCases();++i){startBenchmarkCase(i,false);if(!setjmp(benchmarkFinish))candidateMain();}
 double cpu=double(std::clock()-cpuStart)/CLOCKS_PER_SEC;
 double wall=std::chrono::duration<double>(std::chrono::steady_clock::now()-start).count();
 std::printf("{\"cpu_s\":%.9f,\"wall_s\":%.9f,\"repeats\":%u,\"commands\":%llu,\"completed\":%llu}\n",cpu,wall,repeats,(unsigned long long)benchmarkCommands(),(unsigned long long)benchmarkCompletedCommands());
}
