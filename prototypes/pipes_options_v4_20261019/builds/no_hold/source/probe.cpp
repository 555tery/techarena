#include "policy.hpp"
#ifndef MODEL_HEADER
#define MODEL_HEADER "model.hpp"
#endif
#include MODEL_HEADER
#include <iostream>
int main(){std::array<float,128> x;std::cout<<std::setprecision(17);
    while(std::cin>>x[0]){for(int i=1;i<128;++i)if(!(std::cin>>x[i]))return 2;
        const auto values=options_v4::predict(x);for(double v:values)std::cout<<v<<' ';std::cout<<options_v4::selectOption(values)<<'\n';}
}
