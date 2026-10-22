#include "trained_router.hpp"
#include <array>
#include <iomanip>
#include <iostream>
int main() {
    std::array<float,128> x{};std::cout<<std::setprecision(9);
    while(std::cin>>x[0]) {
        for(std::size_t i=1;i<x.size();++i)if(!(std::cin>>x[i]))return 2;
        std::cout<<learned_model::score(x)<<'\n';
    }
}
