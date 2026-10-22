CXX = clang++
INTERACTOR_CXXFLAGS = -O2 -std=c++17 -pipe
SOLVER_CXXFLAGS = -O2 -std=c++20 -pipe

.PHONY: all interactor test test-holdout compare-policies

all: interactor results/pipes/binaries/pipes-final

interactor: tools/interactor

tools/interactor: vendor/pipes_official/interactor.cpp vendor/pipes_official/testlib.h
	$(CXX) $(INTERACTOR_CXXFLAGS) $< -o $@

results/pipes/binaries/pipes-final: src/pipes.cpp
	mkdir -p results/pipes/binaries
	$(CXX) $(SOLVER_CXXFLAGS) $< -o $@

test: interactor results/pipes/binaries/pipes-final
	python3 tools/pipes_harness.py --solver results/pipes/binaries/pipes-final --name final-source --tests data/pipes/open --out results/pipes/final-open

test-holdout: interactor results/pipes/binaries/pipes-final
	python3 tools/pipes_harness.py --solver results/pipes/binaries/pipes-final --name final-source --tests data/pipes/synthetic/final-holdout-v2 --out results/pipes/final-holdout-v2/final-source

compare-policies: interactor results/pipes/policy-comparison/source.cpp
	python3 tools/compare_pipes.py --source results/pipes/policy-comparison/source.cpp --tests data/pipes/open --out results/pipes/policy-comparison
