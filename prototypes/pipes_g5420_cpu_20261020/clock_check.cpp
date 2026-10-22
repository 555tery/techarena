#include <chrono>
#include <thread>
#include <cassert>
#include <cmath>
#include <cstdio>
#include "process_cpu.hpp"
int main(){
    double before=pipes_cpu::seconds();assert(std::isfinite(before));
    std::this_thread::sleep_for(std::chrono::milliseconds(300));
    double idle=pipes_cpu::seconds()-before;assert(idle<0.05);
    volatile unsigned value=1;double begin=pipes_cpu::seconds();
    while(pipes_cpu::seconds()-begin<0.1)value=value*1664525u+1013904223u;
    double work=pipes_cpu::seconds()-begin;assert(work>=0.1&&work<0.5);
    std::printf("sleep_CPU=%.6f work_CPU=%.6f\n",idle,work);
}
