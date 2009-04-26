#include <Reflex/Reflex.h>

#include <iostream>
#include <dlfcn.h>

#include "poc.h"

using namespace ROOT::Reflex;

void invokeMethod(const char *method)
{
    void * s_libInstance = s_libInstance = dlopen("libMyClass.so", RTLD_NOW);
    Type t = Type::ByName("MyClass");

    if ( t ) {
        if ( t.IsClass() ) {
            Object o = t.Construct();
            Member m = t.MemberByName(method);
            if ( m ) {
                m.Invoke(o);
            }
        }
    }
}
