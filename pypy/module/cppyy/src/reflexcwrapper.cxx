#include "cppyy.h"
#include "reflexcwrapper.h"
#include <vector>
#include <iostream>


cppyy_typehandle_t cppyy_get_typehandle(const char* class_name) {
   return Reflex::Type::ByName(class_name).Id();
}


cppyy_object_t cppyy_construct(cppyy_typehandle_t handle, int numargs, void* args[]) {
    std::vector<void*> arguments(args, args+numargs);
    Reflex::Type t((Reflex::TypeName*)handle);
    std::vector<Reflex::Type> argtypes;
    argtypes.reserve(numargs);
    for (int i = 0; i < numargs; i++) {
        argtypes.push_back(Reflex::Type::ByName("int"));
    }
    Reflex::Type constructor_type = Reflex::FunctionTypeBuilder(
            Reflex::Type::ByName("void"), argtypes);
    return t.Construct(constructor_type, arguments).Address();
}

long cppyy_call_l(cppyy_typehandle_t handle, int method_index,
                  cppyy_object_t self, int numargs, void* args[]) {
    long result;
    std::vector<void*> arguments(args, args+numargs);
    Reflex::Type t((Reflex::TypeName*)handle);
    Reflex::Member m = t.FunctionMemberAt(method_index);
    if (self) {
        Reflex::Object o(t, self);
        m.Invoke(o, result, arguments);
    } else {
        m.Invoke(result, arguments);
    }
    return result;
}

double cppyy_call_d(cppyy_typehandle_t handle, int method_index,
                    cppyy_object_t self, int numargs, void* args[]) {
    double result;
    std::vector<void*> arguments(args, args+numargs);
    Reflex::Type t((Reflex::TypeName*)handle);
    Reflex::Member m = t.FunctionMemberAt(method_index);
    if (self) {
        Reflex::Object o(t, self);
        m.Invoke(o, result, arguments);
    } else {
        m.Invoke(result, arguments);
    }
    return result;
}   

void cppyy_destruct(cppyy_typehandle_t handle, cppyy_object_t self) {
    Reflex::Type t((Reflex::TypeName*)handle);
    t.Destruct(self, true);
}

static cppyy_methptrgetter_t get_methptr_getter(Reflex::Member m)
{
  Reflex::PropertyList plist = m.Properties();
  if (plist.HasProperty("MethPtrGetter")) {
    Reflex::Any& value = plist.PropertyValue("MethPtrGetter");
    return (cppyy_methptrgetter_t)Reflex::any_cast<void*>(value);
  }
  else
    return 0;
}

cppyy_methptrgetter_t cppyy_get_methptr_getter(cppyy_typehandle_t handle, int method_index)
{
    Reflex::Type t((Reflex::TypeName*)handle);
    Reflex::Member m = t.FunctionMemberAt(method_index);
    return get_methptr_getter(m);
}


int num_methods(cppyy_typehandle_t handle) {
    Reflex::Type t((Reflex::TypeName*)handle);
    for (int i = 0; i < (int)t.FunctionMemberSize(); i++) {
        Reflex::Member m = t.FunctionMemberAt(i);
        std::cout << i << " " << m.Name() << std::endl;
        std::cout << "    " << "Stubfunction:  " << (void*)m.Stubfunction() << std::endl;
        std::cout << "    " << "MethPtrGetter: " << (void*)get_methptr_getter(m) << std::endl;
        for (int j = 0; j < (int)m.FunctionParameterSize(); j++) {
            Reflex::Type at = m.TypeOf().FunctionParameterAt(j);
            std::cout << "    " << j << " " << at.Name() << std::endl;
        }
    }
    return t.FunctionMemberSize();
}

char* method_name(cppyy_typehandle_t handle, int method_index) {
    Reflex::Type t((Reflex::TypeName*)handle);
    Reflex::Member m = t.FunctionMemberAt(method_index);
    std::string name = m.Name();
    char* name_char = (char*)malloc(name.size() + 1);
    strcpy(name_char, name.c_str());
    return name_char;
}

char* result_type_method(cppyy_typehandle_t handle, int method_index) {
    Reflex::Type t((Reflex::TypeName*)handle);
    Reflex::Member m = t.FunctionMemberAt(method_index);
    Reflex::Type rt = m.TypeOf().ReturnType();
    std::string name = rt.Name(Reflex::FINAL|Reflex::SCOPED|Reflex::QUALIFIED);
    char* name_char = (char*)malloc(name.size() + 1);
    strcpy(name_char, name.c_str());
    return name_char;
}

int num_args_method(cppyy_typehandle_t handle, int method_index) {
    Reflex::Type t((Reflex::TypeName*)handle);
    Reflex::Member m = t.FunctionMemberAt(method_index);
    return m.FunctionParameterSize();
}

char* arg_type_method(cppyy_typehandle_t handle, int method_index, int arg_index) {

    Reflex::Type t((Reflex::TypeName*)handle);
    Reflex::Member m = t.FunctionMemberAt(method_index);
    Reflex::Type at = m.TypeOf().FunctionParameterAt(arg_index);
    std::string name = at.Name(Reflex::FINAL|Reflex::SCOPED|Reflex::QUALIFIED);
    char* name_char = (char*)malloc(name.size() + 1);
    strcpy(name_char, name.c_str());
    return name_char;
}

int is_constructor(cppyy_typehandle_t handle, int method_index) {
    Reflex::Type t((Reflex::TypeName*)handle);
    Reflex::Member m = t.FunctionMemberAt(method_index);
    return m.IsConstructor();
}

int is_static(cppyy_typehandle_t handle, int method_index) {
    Reflex::Type t((Reflex::TypeName*)handle);
    Reflex::Member m = t.FunctionMemberAt(method_index);
    return m.IsStatic();
}

void myfree(void* ptr) {
    free(ptr);
}
