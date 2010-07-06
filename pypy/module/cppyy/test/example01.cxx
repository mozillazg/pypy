#include <iostream>
#include <stdlib.h>

class example01 {
public:
    static int count;
    int somedata;

    example01() : somedata(-99) {
        count++;
    }
    example01(int a) : somedata(a) {
        count++;
        std::cout << "constructor called" << std::endl;
    }
    example01(const example01& e) : somedata(e.somedata) {
        count++;
        std::cout << "copy constructor called" << std::endl;
    }
    example01& operator=(const example01& e) {
        if (this != &e) {
            somedata = e.somedata;
        }
        return *this;
    }
    ~example01() {
        count--;
    }

    static int add1(int a) {
        return a + 1;
    }
    static int add1(int a, int b) {
        return a + b + 1;
    }
    static double adddouble(double a) {
        return a + 0.01;
    }
    static int atoi(const char* str) {
        return ::atoi(str);
    }
    static int getcount() {
        std::cout << "getcount called" << std::endl;
        return count;
    }
    int add(int a) {
        return somedata + a;
    }
};

int example01::count = 0;
