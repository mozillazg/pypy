
#ifndef CPPYY_REFLEXCWRAPPER
#define CPPYY_REFLEXCWRAPPER

#ifdef __cplusplus
extern "C" {
#endif // ifdef __cplusplus
    void* cppyy_get_typehandle(const char* class_name);

    double callstatic_d(void* handle, int method_index, int numargs, void* args[]);
    long cppyy_call_l(void* handle, int method_index, void* self, int numargs, void* args[]);
    void* construct(void* handle, int numargs, void* args[]);
    void destruct(void* handle, void* self);

    int num_methods(void* handle);
    char* method_name(void* handle, int method_index);
    char* result_type_method(void* handle, int method_index);
    int num_args_method(void* handle, int method_index);
    char* arg_type_method(void* handle, int method_index, int index);
    int is_constructor(void* handle, int method_index);
    int is_static(void* handle, int method_index);

    void myfree(void* ptr);
#ifdef __cplusplus
}
#endif // ifdef __cplusplus

#endif // ifndef CPPYY_REFLEXCWRAPPER
