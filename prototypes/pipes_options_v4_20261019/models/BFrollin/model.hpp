#pragma once
#include <array>
namespace options_v4 {
inline constexpr bool ModelTrained=true;
inline constexpr const char* ModelProvenance="sha256:888b524394026dd316401aedf2ad6522c483d9343b5c09222e33313002d15298";
inline constexpr int Tree_feature[] = {13,36,116,116,82,-2,-2,-2,-2,-2,-2};
inline constexpr double Tree_threshold[] = {0.01785714365541935,0.04583333432674408,0.79999998211860657,0.625,0.88166666030883789,-2,-2,-2,-2,-2,-2};
inline constexpr int Tree_left[] = {1,2,3,4,5,-1,-1,-1,-1,-1,-1};
inline constexpr int Tree_right[] = {10,9,8,7,6,-1,-1,-1,-1,-1,-1};
inline constexpr double Tree_value[][4] = {{0,-0.04637320044296786,-0.0016611295681063117,-0.033776301218161678},
{0,-0.027442528735632184,-0.0017241379310344827,-0.017816091954022988},
{0,-0.010490543735224588,-0.0017730496453900713,-0.018321513002364072},
{0,-0.014290012033694345,-0.001805054151624549,-0.025872442839951871},
{0,-0.0071997549019607848,-0.001838235294117647,-0.015318627450980393},
{0,-0.019598155467720691,-0.0019762845849802375,-0.02042160737812912},
{0,0.15789473684210525,0,0.052631578947368418},
{0,-0.40000000000000002,0,-0.59999999999999998},
{0,0.20000000000000001,0,0.40000000000000002},
{0,-0.625,0,0},
{0,-0.54545454545454541,0,-0.45454545454545453}};
inline std::array<double,4> predict(const std::array<float,128>& x) {
  int node=0; while(Tree_left[node]>=0) node=(static_cast<double>(x[Tree_feature[node]])<=Tree_threshold[node])?Tree_left[node]:Tree_right[node];
  return {{Tree_value[node][0],Tree_value[node][1],Tree_value[node][2],Tree_value[node][3]}};
}
}
