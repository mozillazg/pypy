#include <iostream>

#include "myClass.h"

using namespace std;

MyClass::MyClass()
{}

void MyClass::testOne()
{
    cout <<"test one\n";
}

void MyClass::testTwo(int i)
{
    cout <<"test two:"<<i;
}
