#include "cppyy.h"
#include "reflexcwrapper.h"
#include <vector>

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
    Reflex::Object r = Reflex::Object(t, t.Allocate());
    t.FunctionMemberAt(1).Invoke(r, 0, arguments);
    return r.Address();
}

