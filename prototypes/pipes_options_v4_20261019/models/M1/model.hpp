#pragma once
#include <array>
namespace options_v4 {
inline constexpr bool ModelTrained=true;
inline constexpr const char* ModelProvenance="sha256:20a7b3e726ba02a8aa329653899f5bac0d6a1bf3a941fa3465a4398690e488c5";
inline constexpr int Tree_feature[] = {108,10,92,86,7,-2,-2,-2,-2,86,-2,-2,-2};
inline constexpr double Tree_threshold[] = {0.46249999105930328,0.2321428582072258,0.16938965767621994,0.09375,0.2321428582072258,-2,-2,-2,-2,0.060000000521540642,-2,-2,-2};
inline constexpr int Tree_left[] = {1,2,3,4,5,-1,-1,-1,-1,10,-1,-1,-1};
inline constexpr int Tree_right[] = {12,9,8,7,6,-1,-1,-1,-1,11,-1,-1,-1};
inline constexpr double Tree_value[][4] = {{0,-0.024271844660194174,0,-0.014563106796116505},
{0,0.0053191489361702126,0,-0.015957446808510637},
{0,0.03048780487804878,0,0.0060975609756097563},
{0,0.0066666666666666671,0,-0.0066666666666666671},
{0,-0.0070422535211267607,0,-0.0070422535211267607},
{0,-0.010869565217391304,-0.0036231884057971015,-0.010869565217391304},
{0,0.125,0.125,0.125},
{0,0.25,0,0},
{0,0.2857142857142857,0,0.14285714285714285},
{0,-0.16666666666666666,0,-0.16666666666666666},
{0,-0.33333333333333331,0,-0.33333333333333331},
{0,0,0,0},
{0,-0.33333333333333331,0,0}};
inline std::array<double,4> predict(const std::array<float,128>& x) {
  int node=0; while(Tree_left[node]>=0) node=(static_cast<double>(x[Tree_feature[node]])<=Tree_threshold[node])?Tree_left[node]:Tree_right[node];
  return {{Tree_value[node][0],Tree_value[node][1],Tree_value[node][2],Tree_value[node][3]}};
}
}
