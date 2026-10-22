#include <cstdint>
#include <limits>
#include <cmath>
#include <cassert>
#include <cstdio>
#define _WIN32 1
#include "process_cpu.hpp"
int main(){
    fake_kernel={10000000,0};fake_user={7500000,0};assert(std::abs(pipes_cpu::seconds()-1.75)<1e-9);
    fake_kernel={2,1};fake_user={0,0};assert(std::abs(pipes_cpu::seconds()-429.4967298)<1e-9);
    fake_ok=false;assert(std::isinf(pipes_cpu::seconds()));
    std::puts("Windows CPU tick conversion and API failure handling: stub unit OK; not a native Windows run");
}
