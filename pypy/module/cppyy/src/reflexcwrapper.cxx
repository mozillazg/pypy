#include "cppyy.h"
#include "reflexcwrapper.h"
#include <vector>
#include <iostream>

long callstatic_l(const char* class_name, int method_index, int numargs, void* args[]) {
    long result;
    std::vector<void*> arguments(args, args+numargs);
    Reflex::Type t = Reflex::Type::ByName(class_name);
    Reflex::Member m = t.FunctionMemberAt(method_index);
    m.Invoke(result, arguments);
    return result;
}
double callstatic_d(const char* class_name, int method_index, int numargs, void* args[]) {
    double result;
    std::vector<void*> arguments(args, args+numargs);
    Reflex::Type t = Reflex::Type::ByName(class_name);
    Reflex::Member m = t.FunctionMemberAt(method_index);
    m.Invoke(result, arguments);
    return result;
}

long callmethod_l(const char* class_name, int method_index,
	          void* self, int numargs, void* args[]) {
    long result;
    std::vector<void*> arguments(args, args+numargs);
    Reflex::Type t = Reflex::Type::ByName(class_name);
    Reflex::Object o(t, self);
    Reflex::Member m = t.FunctionMemberAt(method_index);
    m.Invoke(o, result, arguments);
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


int num_methods(const char* class_name) {
    Reflex::Type t = Reflex::Type::ByName(class_name);
    for (int i = 0; i < t.FunctionMemberSize(); i++) {
        Reflex::Member m = t.FunctionMemberAt(i);
        std::cout << i << " " << m.Name() << std::endl;
        for (int j = 0; j < m.FunctionParameterSize(); j++) {
            Reflex::Type at = m.TypeOf().FunctionParameterAt(j);
            std::cout << "    " << j << " " << at.Name() << std::endl;
        }
    }
    return t.FunctionMemberSize();
}

char* method_name(const char* class_name, int method_index) {
    Reflex::Type t = Reflex::Type::ByName(class_name);
    Reflex::Member m = t.FunctionMemberAt(method_index);
    std::string name = m.Name();
    char* name_char = (char*)malloc(name.size() + 1);
    strcpy(name_char, name.c_str());
    return name_char;
}

char* result_type_method(const char* class_name, int method_index) {
    Reflex::Type t = Reflex::Type::ByName(class_name);
    Reflex::Member m = t.FunctionMemberAt(method_index);
    Reflex::Type rt = m.TypeOf().ReturnType();
    std::string name = rt.Name(Reflex::FINAL);
    char* name_char = (char*)malloc(name.size() + 1);
    strcpy(name_char, name.c_str());
    return name_char;
}

int num_args_method(const char* class_name, int method_index) {
    Reflex::Type t = Reflex::Type::ByName(class_name);
    Reflex::Member m = t.FunctionMemberAt(method_index);
    return m.FunctionParameterSize();
}

char* arg_type_method(const char* class_name, int method_index, int arg_index) {

    Reflex::Type t = Reflex::Type::ByName(class_name);
    Reflex::Member m = t.FunctionMemberAt(method_index);
    Reflex::Type at = m.TypeOf().FunctionParameterAt(arg_index);
    std::string name = at.Name(Reflex::FINAL);
    char* name_char = (char*)malloc(name.size() + 1);
    strcpy(name_char, name.c_str());
    return name_char;
}

int is_constructor(const char* class_name, int method_index) {
    Reflex::Type t = Reflex::Type::ByName(class_name);
    Reflex::Member m = t.FunctionMemberAt(method_index);
    return m.IsConstructor();
}

int is_static(const char* class_name, int method_index) {
    Reflex::Type t = Reflex::Type::ByName(class_name);
    Reflex::Member m = t.FunctionMemberAt(method_index);
    return m.IsStatic();
}

void myfree(void* ptr) {
    free(ptr);
}
