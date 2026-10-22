// Process CPU = user + kernel/system; excludes time waiting for the interactor.
// The solver has one worker thread. Do not divide this value by core count.
#include <cstdint>
#include <limits>
#if defined(_WIN32)
#ifndef NOMINMAX
#define NOMINMAX
#endif
#ifndef WIN32_LEAN_AND_MEAN
#define WIN32_LEAN_AND_MEAN
#endif
#include <windows.h>
#else
#include <sys/resource.h>
#endif

namespace pipes_cpu {
inline double seconds() noexcept {
#if defined(_WIN32)
    FILETIME created{},exited{},kernel{},user{};
    if(!GetProcessTimes(GetCurrentProcess(),&created,&exited,&kernel,&user))
        return std::numeric_limits<double>::infinity();
    const auto ticks=[](const FILETIME& t){return (std::uint64_t(t.dwHighDateTime)<<32)|std::uint64_t(t.dwLowDateTime);};
    return (double(ticks(kernel))+double(ticks(user)))*1e-7;
#else
    rusage usage{};
    if(getrusage(RUSAGE_SELF,&usage)!=0)return std::numeric_limits<double>::infinity();
    return double(usage.ru_utime.tv_sec)+double(usage.ru_stime.tv_sec)
        +(double(usage.ru_utime.tv_usec)+double(usage.ru_stime.tv_usec))*1e-6;
#endif
}
}

// Conservative provisional profile. These are not measurements on the G5420.
#ifndef PIPES_MEMO_BUCKET_LOG2
#define PIPES_MEMO_BUCKET_LOG2 19
#endif
static_assert(PIPES_MEMO_BUCKET_LOG2>=16&&PIPES_MEMO_BUCKET_LOG2<=21);
constexpr double kHardwarePlannerCpu=2.5;
constexpr double kHardwareSearchStopCpu=3.8;
constexpr double kHardwareProcessEnvelope=4.0;
constexpr double kHardwareReserveSafety=1.25;
