#pragma once
#include <csetjmp>
#include <cstdint>
extern std::jmp_buf benchmarkFinish;
void loadBenchmarkFixtures(const char*path,bool crlf);
void startBenchmarkCase(unsigned i,bool verify);
unsigned benchmarkCases();
uint64_t benchmarkCommands();
uint64_t benchmarkCompletedCommands();
