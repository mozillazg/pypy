#include <iostream>
#include <sstream>
#include <string>
#include <stdlib.h>
#include <string.h>

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

// class methods
    static int staticAddOneToInt(int a) {
        return a + 1;
    }
    static int staticAddOneToInt(int a, int b) {
        return a + b + 1;
    }
    static double staticAddToDouble(double a) {
        return a + 0.01;
    }
    static int staticAtoi(const char* str) {
        return ::atoi(str);
    }
    static char* staticStrcpy(const char* strin) {
        char* strout = (char*)malloc(::strlen(strin + 1));
        ::strcpy(strout, strin);
        return strout;
    }

    static int getCount() {
        std::cout << "getcount called" << std::endl;
        return count;
    }

// instance methods
    int addDataToInt(int a) {
        return somedata + a;
    }

    double addDataToDouble(double a) {
        return somedata + a;
    }

    int addDataToAtoi(const char* str) {
        return ::atoi(str) + somedata;
    }   

    char* addToStringValue(const char* str) {
        int out = ::atoi(str) + somedata;
        std::ostringstream ss;
        ss << out << std::ends;
        std::string result = ss.str();
        char* cresult = (char*)malloc(result.size()+1);
        ::strcpy(cresult, result.c_str());
        return cresult;
    }

};

int example01::count = 0;
