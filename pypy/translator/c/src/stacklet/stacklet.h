/********** A really minimal coroutine package for C **********/
#ifndef _STACKLET_H_
#define _STACKLET_H_

#include <stdlib.h>


/* A "stacklet handle" is an opaque pointer to a suspended stack.
 * Whenever we suspend the current stack in order to switch elsewhere,
 * stacklet.c passes to the target a 'stacklet_handle' argument that points
 * to the original stack now suspended.  The handle must later be passed
 * back to this API once, in order to resume the stack.  It is only
 * valid once.
 */
typedef struct stacklet_s *stacklet_handle;

#define EMPTY_STACKLET_HANDLE  ((stacklet_handle) -1)


/* Multithread support.
 */
typedef struct stacklet_thread_s *stacklet_thread_handle;

stacklet_thread_handle stacklet_newthread(void);
void stacklet_deletethread(stacklet_thread_handle thrd);


/* The "run" function of a stacklet.  The first argument is the handle
 * of the stack from where we come.  When such a function returns, it
 * must return a (non-empty) stacklet_handle that tells where to go next.
 */
typedef stacklet_handle (*stacklet_run_fn)(stacklet_handle, void *);

/* Call 'run(source, run_arg)' in a new stack.  See stacklet_switch()
 * for the return value.
 */
stacklet_handle stacklet_new(stacklet_thread_handle thrd,
                             stacklet_run_fn run, void *run_arg);

/* Switch to the target handle, resuming its stack.  This returns:
 *  - if we come back from another call to stacklet_switch(), the source handle
 *  - if we come back from a run() that finishes, EMPTY_STACKLET_HANDLE
 *  - if we run out of memory, NULL
 * Don't call this with an already-used target, with EMPTY_STACKLET_HANDLE,
 * or with a stack handle from another thread (in multithreaded apps).
 */
stacklet_handle stacklet_switch(stacklet_thread_handle thrd,
                                stacklet_handle target);

/* Delete a stack handle without resuming it at all.
 * (This works even if the stack handle is of a different thread)
 */
void stacklet_destroy(stacklet_thread_handle thrd, stacklet_handle target);

/* stacklet_handle _stacklet_switch_to_copy(stacklet_handle) --- later */

/* Hack: translate a pointer into the stack of a stacklet into a pointer
 * to where it is really stored so far.  Only to access word-sized data.
 */
char **_stacklet_translate_pointer(stacklet_handle context, char **ptr);

/* To use with the previous function: turn a 'char**' that points into
 * the currently running stack into an opaque 'long'.  The 'long'
 * remains valid as long as the original stack location is valid.  At
 * any point in time we can ask '_stacklet_get_...()' to convert it back
 * into a 'stacklet_handle, char**' pair.  The 'char**' will always be
 * the same, but the 'stacklet_handle' might change over time.
 * Together, they are valid arguments for _stacklet_translate_pointer().
 *
 * The returned 'long' is an odd value if currently running in a non-
 * main stacklet, or directly '(long)stackptr' if currently running in
 * the main stacklet.  This guarantees that it is possible to use
 * '_stacklet_get_...()' on a regular address taken before starting
 * to use stacklets.
 *
 * XXX assumes a single stacklet_thread_handle per thread
 *
 * XXX _stacklet_capture_stack_pointer() invalidates all 'long' values
 * previously returned for the same stacklet that were for addresses
 * later in the stack (i.e. lower).
 */
long _stacklet_capture_stack_pointer(stacklet_thread_handle, char **stackptr);
char **_stacklet_get_captured_pointer(long captured);
stacklet_handle _stacklet_get_captured_context(long captured);

#endif /* _STACKLET_H_ */
