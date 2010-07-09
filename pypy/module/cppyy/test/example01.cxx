#include <iostream>
#include <sstream>
#include <string>
#include <stdlib.h>
#include <string.h>

#include "example01.h"

//===========================================================================
payload::payload(double d) : m_data(d) {}
payload::payload(const payload& p) : m_data(p.m_data) {}

double payload::getData() { return m_data; }
void payload::setData(double d) { m_data = d; }


//===========================================================================
example01::example01() : somedata(-99) {
    count++;
}
example01::example01(int a) : somedata(a) {
    count++;
    std::cout << "constructor called" << std::endl;
}
example01::example01(const example01& e) : somedata(e.somedata) {
    count++;
    std::cout << "copy constructor called" << std::endl;
}
example01& example01::operator=(const example01& e) {
    if (this != &e) {
        somedata = e.somedata;
    }
    return *this;
}
example01::~example01() {
    count--;
}

// class methods
int example01::staticAddOneToInt(int a) {
    return a + 1;
}
int example01::staticAddOneToInt(int a, int b) {
    return a + b + 1;
}
double example01::staticAddToDouble(double a) {
    return a + 0.01;
}
int example01::staticAtoi(const char* str) {
    return ::atoi(str);
}
char* example01::staticStrcpy(const char* strin) {
    char* strout = (char*)malloc(::strlen(strin + 1));
    ::strcpy(strout, strin);
    return strout;
}
void example01::setPayload( payload* p, double d ) {
    p->setData(d);
}

int example01::getCount() {
    std::cout << "getcount called" << std::endl;
    return count;
}

// instance methods
int example01::addDataToInt(int a) {
    return somedata + a;
}

double example01::addDataToDouble(double a) {
    return somedata + a;
}

int example01::addDataToAtoi(const char* str) {
    return ::atoi(str) + somedata;
}   

char* example01::addToStringValue(const char* str) {
    int out = ::atoi(str) + somedata;
    std::ostringstream ss;
    ss << out << std::ends;
    std::string result = ss.str();
    char* cresult = (char*)malloc(result.size()+1);
    ::strcpy(cresult, result.c_str());
    return cresult;
}

int example01::count = 0;
