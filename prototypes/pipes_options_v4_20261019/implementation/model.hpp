#pragma once
#include <array>
namespace options_v4 {
inline constexpr bool ModelTrained=false;
inline constexpr const char* ModelProvenance="untrained-BF";
inline std::array<double,4> predict(const std::array<float,128>&) {return {{0,0,0,0}};}
}
