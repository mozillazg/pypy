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
}

void destruct(const char* class_name, void* self) {
    Reflex::Type t = Reflex::Type::ByName(class_name);
    t.Destruct(self, true);
}
