#include "cppyy.h"
#include "reflexcwrapper.h"
#include <vector>

long callstatic_l(const char* classname, const char* methodname, int numargs, void* args[]) {
    long result;
    std::vector<void*> arguments(args, args+numargs);
    Reflex::Type t = Reflex::Type::ByName(classname);
    Reflex::Member m = t.FunctionMemberByName(methodname);
    m.Invoke(result, arguments);
    return result;
}
