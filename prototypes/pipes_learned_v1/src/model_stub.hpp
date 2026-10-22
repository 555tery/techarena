#pragma once

#include <array>

namespace learned_model {

// Safe placeholder until a locally calibrated model is available.
inline constexpr float kMargin = 1.0e30f;
inline float score(const std::array<float, 128>&) { return 0.0f; }

}  // namespace learned_model
