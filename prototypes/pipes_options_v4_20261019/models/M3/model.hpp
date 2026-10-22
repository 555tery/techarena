#pragma once
#include <array>
namespace options_v4 {
inline constexpr bool ModelTrained=true;
inline constexpr const char* ModelProvenance="sha256:7312e7536188b76d16e9fc42ffaa348e53bebc1af860b28261db9a743fc76216";
inline constexpr int Tree_feature[] = {36,13,114,115,-2,93,-2,-2,-2,-2,-2};
inline constexpr double Tree_threshold[] = {0.01785714365541935,0.038690477609634399,0.14265625178813934,-0.28750000894069672,-2,0.40416666865348816,-2,-2,-2,-2,-2};
inline constexpr int Tree_left[] = {1,2,3,4,-1,6,-1,-1,-1,-1,-1};
inline constexpr int Tree_right[] = {10,9,8,5,-1,7,-1,-1,-1,-1,-1};
inline constexpr double Tree_value[][4] = {{0,-0.053194444444444426,-0.0016666666666666661,-0.037222222222222212},
{0,-0.027442528735632184,-0.0017241379310344827,-0.028160919540229885},
{0,-0.014136904761904767,-0.0017857142857142861,-0.014880952380952385},
{0,-0.0035493827160493823,-0.0018518518518518521,-0.011728395061728399},
{0,-0.2857142857142857,0,-0.14285714285714285},
{0,0.0039607097591888452,-0.0019011406844106464,-0.0082382762991128015},
{0,-0.0037581699346405234,-0.0019607843137254906,-0.012418300653594774},
{0,0.25,0,0.125},
{0,-0.29999999999999999,0,-0.10000000000000001},
{0,-0.40000000000000002,0,-0.40000000000000002},
{0,-0.80000000000000004,0,-0.29999999999999999}};
inline std::array<double,4> predict(const std::array<float,128>& x) {
  int node=0; while(Tree_left[node]>=0) node=(static_cast<double>(x[Tree_feature[node]])<=Tree_threshold[node])?Tree_left[node]:Tree_right[node];
  return {{Tree_value[node][0],Tree_value[node][1],Tree_value[node][2],Tree_value[node][3]}};
}
}
