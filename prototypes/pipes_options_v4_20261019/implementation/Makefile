CXX ?= c++
CXXFLAGS ?= -O2 -std=c++17 -Wall -Wextra -Wpedantic
MODEL_HEADER ?= model.hpp
MODEL_DEFINE = -DMODEL_HEADER='"$(abspath $(MODEL_HEADER))"'
all: teacher solver solver-bf solver-hold1
teacher: teacher.cpp policy.hpp allocator.hpp $(MODEL_HEADER)
	$(CXX) $(CXXFLAGS) $(MODEL_DEFINE) teacher.cpp -o $@
solver: solver.cpp policy.hpp allocator.hpp $(MODEL_HEADER)
	$(CXX) $(CXXFLAGS) $(MODEL_DEFINE) solver.cpp -o $@
solver-bf: solver.cpp policy.hpp allocator.hpp $(MODEL_HEADER)
	$(CXX) $(CXXFLAGS) $(MODEL_DEFINE) -DOPTIONS_ENABLED=0 solver.cpp -o $@
solver-hold1: solver.cpp policy.hpp allocator.hpp $(MODEL_HEADER)
	$(CXX) $(CXXFLAGS) $(MODEL_DEFINE) -DOPTION_HOLD=1 solver.cpp -o $@
.PHONY: all
