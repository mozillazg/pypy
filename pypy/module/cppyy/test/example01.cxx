#include <iostream>

class example01 {
public:
    int somedata;
    example01(int a) : somedata(a) {
        std::cout << "constructor called" << std::endl;
    }

    static int add1(int a) {
        return a + 1;
    }
    int add(int a) {
        return somedata + a;
    }
};
