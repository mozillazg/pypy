//for using the LLVM C++ API

#ifdef  __cplusplus
extern "C" {
#endif

void    restart();
int     transform(const char* passnames);
int     parse(const char* llsource);

//Function code
int     freeMachineCodeForFunction(const void* function);
int     recompile(const void* function);
int     execute(const void* function, int param);

//Module code
void*   getNamedFunction(const char* name);
void*   getNamedGlobal(const char* name);
void    addGlobalMapping(const void* p, void* address); 

//test code
int     get_global_data();
void    set_global_data(int n);
int*    get_pointer_to_global_data();
void*   get_pointer_to_global_function();

#ifdef  __cplusplus    
}
#endif
