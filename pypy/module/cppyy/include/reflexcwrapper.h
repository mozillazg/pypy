
#ifndef CPPYY_REFLEXCWRAPPER
#define CPPYY_REFLEXCWRAPPER

extern "C" {
    long callstatic_l(const char* class_name, const char* method_name, int numargs, void* args[]);
}

#endif // ifndef CPPYY_REFLEXCWRAPPER
