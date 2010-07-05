
#ifndef CPPYY_REFLEXCWRAPPER
#define CPPYY_REFLEXCWRAPPER

extern "C" {
    long callstatic_l(const char* class_name, const char* method_name, int numargs, void* args[]);
    long callmethod_l(const char* class_name, const char* method_name, void* self, int numargs, void* args[]);
    void* construct(const char* class_name, int numargs, void* args[]);
    void destruct(const char* class_name, void* self);
}

#endif // ifndef CPPYY_REFLEXCWRAPPER
