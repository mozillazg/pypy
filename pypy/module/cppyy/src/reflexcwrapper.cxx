#include "cppyy.h"
#include "reflexcwrapper.h"
#include <vector>
#include <iostream>

long callstatic_l(const char* class_name, const char* method_name, int numargs, void* args[]) {
    long result;
    std::vector<void*> arguments(args, args+numargs);
    Reflex::Type t = Reflex::Type::ByName(class_name);
    Reflex::Member m = t.FunctionMemberByName(method_name);
    m.Invoke(result, arguments);
    return result;
}

long callmethod_l(const char* class_name, const char* method_name,
	          void* self, int numargs, void* args[]) {
    long result;
    std::vector<void*> arguments(args, args+numargs);
    Reflex::Type t = Reflex::Type::ByName(class_name);
    Reflex::Object o(t, self);
    o.Invoke(method_name, result, arguments);
    return result;
}

void* construct(const char* class_name, int numargs, void* args[]) {
    std::vector<void*> arguments(args, args+numargs);
    Reflex::Type t = Reflex::Type::ByName(class_name);
    std::vector<Reflex::Type> argtypes;
    argtypes.reserve(numargs);
    for (int i = 0; i < numargs; i++) {
    	argtypes.push_back(Reflex::Type::ByName("int"));
    }
    Reflex::Type constructor_type = Reflex::FunctionTypeBuilder(
	    Reflex::Type::ByName("void"), argtypes);
    return t.Construct(constructor_type, arguments).Address();
    void* mem = t.Allocate();
    memset(mem, 41, t.SizeOf());
    Reflex::Object r = Reflex::Object(t, mem);
    int i = 1;
    std::cout << t.FunctionMemberAt(i).Name() << std::endl;
    t.FunctionMemberAt(i).Invoke(r, 0, arguments);
    return r.Address();
}

