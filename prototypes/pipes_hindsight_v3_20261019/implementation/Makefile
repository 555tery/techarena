CXX ?= c++
CXXFLAGS ?= -O2 -std=c++17 -Wall -Wextra -Wpedantic

all: teacher solver solver-bf

teacher: teacher.cpp policy.hpp allocator.hpp
	$(CXX) $(CXXFLAGS) teacher.cpp -o $@

solver: solver.cpp policy.hpp allocator.hpp model.hpp
	$(CXX) $(CXXFLAGS) solver.cpp -o $@

solver-bf: solver.cpp policy.hpp allocator.hpp model.hpp
	$(CXX) $(CXXFLAGS) -DHINDSIGHT_ENABLED=0 solver.cpp -o $@

.PHONY: all
