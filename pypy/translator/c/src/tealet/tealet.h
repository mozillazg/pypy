/********** A minimal coroutine package for C **********/
#ifndef _TEALET_H_
#define _TEALET_H_

#include <stdlib.h>


#ifdef WIN32
#if defined TEALET_EXPORTS
#define TEALET_API __declspec(dllexport)
#elif defined TEALET_IMPORTS
#define TEALET_API __declspec(dllimport)
#else
#define TEALET_API
#endif
#else /* win32 */
#define TEALET_API
#endif


/* A structure to define the memory allocation api used.
 * the functions have C89 semantics and take an additional "context"
 * pointer that they can use as they please
 */
typedef struct tealet_alloc_s {
  void *(*malloc_p)(size_t size, void *context);
  void *(*realloc_p)(void *ptr, size_t size, void *context);
  void  (*free_p)(void *ptr, void *context);
  void *context;
} tealet_alloc_t;

/* use the following macro to initialize a tealet_alloc_t
 * structure with stdlib malloc functions, for convenience, e.g.:
 * tealet_alloc_t stdalloc = TEALET_MALLOC;
 */
#define TEALET_MALLOC {\
    (void *(*)(size_t, void*))malloc, \
    (void *(*)(void*, size_t, void*))realloc, \
    (void (*)(void*, void*))free, \
    0 \
}


/* The user-visible tealet structure */
typedef struct tealet_s {
  struct tealet_s *main;   /* pointer to the main tealet */
  void *data;              /* general-purpose, store whatever you want here */
  /* private fields follow */
} tealet_t;

/* The "run" function of a tealet.  It is called with the
 * current tealet and the argument provided to its start function 
 */
typedef tealet_t *(*tealet_run_t)(tealet_t *current, void *arg);


/* error codes.  API functions that return int return a negative value
 * to signal an error.
 * Those that return tealet_t pointers return NULL to signal a memory
 * error.
 */
#define TEALET_ERR_MEM -1       /* memory allocation failed */
#define TEALET_ERR_INVALID -2   /* the target tealet is corrupt */


/* Initialize and return the main tealet.  The main tealet contains the whole
 * "normal" execution of the program; it starts when the program starts and
 * ends when the program ends.  This function and tealet_finalize() should
 * be called together from the same (main) function which calls the rest of
 * the program.  It is fine to nest several uses of initialize/finalize,
 * or to call them in multiple threads in case of multithreaded programs,
 * as long as you don't try to switch to tealets created with a
 * different main tealet.
 */
TEALET_API
tealet_t *tealet_initialize(tealet_alloc_t *alloc);

/* Tear down the main tealet.  Call e.g. after a thread finishes (including
 * all its tealets).
 */
TEALET_API
void tealet_finalize(tealet_t *main);

/* Allocate a new tealet 'g', and call 'run(g, arg)' in it.
 * The return value of run() must be the next tealet in which to continue
 * execution, which must be a different one, like for example the main tealet.
 * When 'run(g)' returns, the tealet 'g' is freed.
 */
TEALET_API
int tealet_new(tealet_t *main, tealet_run_t run, void *arg);

/* Return the current tealet, i.e. the one in which the caller of this
 * function currently is.  "main" can be any tealet derived from the
 * main tealet.
 */
TEALET_API
tealet_t *tealet_current(tealet_t *main);

/* Switch to another tealet.  Execution continues there.  The tealet
 * passed in must not have been freed yet and must descend from
 * the same main tealet as the current one.  In multithreaded applications,
 * it must also belong to the current thread (otherwise, segfaults).
 */
TEALET_API
int tealet_switch(tealet_t *target);

/* Exit the current tealet.  Same as tealet_switch except that
 * it the current tealet is deleted.  Use this only in emergency,
 * if tealet_switch() fails due to inability to save the stack.
 * This call fails only if the target has invalid state, otherwise
 * it never returns.
 */
TEALET_API
int tealet_exit(tealet_t *target);

/* Duplicate a tealet. This is intended for the duplication of stubs so
 * that new stubs can be recretaed with a predetermined stack.
 */
#ifndef TEALET_NO_SHARING
TEALET_API
tealet_t *tealet_duplicate(tealet_t *tealet);
#endif

/* Deallocate a tealet.  Use this to delete a stub that
 * is no longer being used for tealet_stub_dup(), or to deallocate
 * a tealet that has become invalid due to memory errors.
 * It can also delete a suspended tealet, which effectively kills it.
 *
 * XXX probably buggy
 */
TEALET_API
void tealet_delete(tealet_t *target);

/* Allocate a new tealet stub at this position.  This can later
 * be run with tealet_stub_new(), duplicated with tealet_duplicate()
 * and deleted with tealet_stub_del().
 */
TEALET_API
tealet_t *tealet_stub_new(tealet_t *main);

/* Run a stub.  The combination of tealet_stub_new() and tealet_stub_run()
 * is exactly the same as tealet_new()
 */
TEALET_API
int tealet_stub_run(tealet_t *stub, tealet_run_t run, void *run_arg);

/* Hack: translate a pointer into the stack of a tealet into a pointer
 * to where it is really stored so far.  Only to access word-sized data.
 */
TEALET_API
char **_tealet_translate_pointer(tealet_t *context, char **ptr);

#endif /* _TEALET_H_ */
