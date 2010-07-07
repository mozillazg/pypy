
#ifndef CPPYY_REFLEXCWRAPPER
#define CPPYY_REFLEXCWRAPPER

#ifdef __cplusplus
extern "C" {
#endif // ifdef __cplusplus
    long callstatic_l(const char* class_name, int method_index, int numargs, void* args[]);
    double callstatic_d(const char* class_name, int method_index, int numargs, void* args[]);
    long callmethod_l(const char* class_name, int method_index, void* self, int numargs, void* args[]);
    void* construct(const char* class_name, int numargs, void* args[]);
    void destruct(const char* class_name, void* self);

    int num_methods(const char* class_name);
    char* method_name(const char* class_name, int method_index);
    char* result_type_method(const char* class_name, int method_index);
    int num_args_method(const char* class_name, int method_index);
    char* arg_type_method(const char* class_name, int method_index, int index);
    int is_constructor(const char* class_name, int method_index);
    int is_static(const char* class_name, int method_index);

    void myfree(void* ptr);
#ifdef __cplusplus
}
#endif // ifdef __cplusplus

#endif // ifndef CPPYY_REFLEXCWRAPPER
