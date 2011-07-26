/********** A minimal coroutine package for C **********
 * By Armin Rigo
 * Documentation: see the source code of the greenlet package from
 *
 *     http://codespeak.net/svn/greenlet/trunk/c/_greenlet.c
 */

#include "src/tealet/tealet.h"

#include <stddef.h>
#include <assert.h>
#include <string.h>

/************************************************************
 * platform specific code
 */

/* The default stack direction is downwards, 0, but platforms
 * can redefine it to upwards growing, 1.
 */
#define STACK_DIRECTION 0   

#include "src/tealet/slp_platformselect.h"

#if STACK_DIRECTION == 0
#define STACK_STOP_MAIN     ((char*) -1)    /* for stack_stop */
#define STACK_LE(a, b)      ((a) <= (b))    /* to compare stack position */
#define STACK_SUB(a, b)     ((a) - (b))     /* to subtract stack pointers */
#else
#define STACK_STOP_MAIN     ((char*) 1)     /* for stack_stop */
#define STACK_LE(a, b)      ((b) <= (a))    /* to compare stack position */
#define STACK_SUB(a, b)     ((b) - (a))     /* to subtract stack pointers */
#endif

/************************************************************/

/* #define DEBUG_DUMP */

#ifdef DEBUG_DUMP
#include <stdio.h>
static int counter = 0;
#endif


/* the actual tealet structure as used internally */
typedef struct tealet_sub_s {
  tealet_t base;

  /* The stack claimed by this tealet.  Since we allow for architectures
   * where stack can be allocated downwards in memory (most common) or
   * upwards (less common), we use the terms near or far to discern this.
   * The main tealet will have stack_stop set to the end of memory.
   * stack_start is zero for a running tealet, otherwise it contains
   * the address where the stack_copy should go.
   * In addition, stack_stop is set to NULL value to indicate
   * that a tealet is exiting.
   */
  char *stack_start;                /* the "near" end of the stack */
  char *stack_stop;                 /* the "far" end of the stack. */
  
  /* if the tealet is inactive, the following contain its saved
   * stack, otherwise, both are zero.
   * stack_saved can also be -1, meaning that saving the stack
   * failed and the tealet is invalid.
   */
  char *stack_copy;                 /* saved data */
  size_t stack_saved;               /* the amount saved */

  /* A linked list of partially or completely unsaved tealets linked
   * from the currently executing tealet.  Each one is has it's
   * stack_stop higher to the previous one.  This is used
   * to enable just-in-time saving of stacks.
   */
  struct tealet_sub_s *stack_prev;
#ifdef DEBUG_DUMP
  int counter;
#endif
} tealet_sub_t;

/* The main tealet has additional fields for housekeeping */
typedef struct {
  tealet_sub_t base;
  tealet_sub_t *g_current;
  tealet_sub_t *g_target;   /* Temporary store when switching */
  tealet_run_t  g_run;      /* run function and arguments */
  void         *g_run_arg;
  tealet_alloc_t g_alloc;   /* the allocation context used */
} tealet_main_t;

#define TEALET_IS_MAIN(t)  (((tealet_sub_t *)(t))->stack_stop == STACK_STOP_MAIN)
#define TEALET_MAIN(t)     ((tealet_main_t *)((t)->base.main))

/************************************************************/

int (*_tealet_switchstack)(tealet_main_t*);
int (*_tealet_initialstub)(tealet_main_t*, long*);

/************************************************************
 * helpers to call the malloc functions provided by the user
 */
static void *g_malloc(tealet_main_t *g_main, size_t size)
{
    return g_main->g_alloc.malloc_p(size, g_main->g_alloc.context);
}
static void *g_realloc(tealet_main_t *g_main, void *ptr, size_t size)
{
    return g_main->g_alloc.realloc_p(ptr, size, g_main->g_alloc.context);
}
static void g_free(tealet_main_t *g_main, void *ptr)
{
    g_main->g_alloc.free_p(ptr, g_main->g_alloc.context);
}

/*************************************************************
 * Helpers to allocate, grow and duplicate stacks, using reference
 * counts. This allows us to duplicate tealets (stubs primarily)
 * cheaply and without all sorts of special casing.
 */
static void* stack_grow(tealet_main_t *main, void *old, size_t oldsize, size_t newsize)
{
#ifndef TEALET_NO_SHARING
    char *result;
    newsize += sizeof(size_t);
    assert(oldsize < newsize);
    if (old == NULL) {
        result = (char*)g_malloc(main, newsize);
    } else {
        char *realp = (char*)old - sizeof(size_t);
        size_t cnt = *(size_t*)realp;
        if (cnt == 1) {
            result = (char*)g_realloc(main, (void*)realp, newsize);
        } else {
            /* we can't grow a shared stack, un-share it */
            result = (char*)g_malloc(main, newsize);
            if (result != NULL) {
                --(*(size_t*)realp);
                memcpy((void*)result, (void*)realp, oldsize + sizeof(size_t));
            }
        }
    }
    if (result == NULL)
        return NULL;
    *(size_t*)result = 1;
    return (void*)(result + sizeof(size_t));
#else
    return g_realloc(main, old, newsize);
#endif
}

static void stack_free(tealet_main_t *main, void *ptr)
{
#ifndef TEALET_NO_SHARING
    if (ptr != NULL) {
        char *realp = (char*)ptr - sizeof(size_t);
        if (--(*(size_t*)realp) == 0)
            g_free(main, (void*)realp);
    }
#else
    g_free(main, ptr);
#endif
}

#ifndef TEALET_NO_SHARING
static void* stack_dup(void *ptr)
{
    if (ptr != NULL) {
        /* just increment the reference count */
        char *realp = (char*)ptr - sizeof(size_t);
        ++(*(size_t*)realp);
    }
    return ptr;
}
#endif

/***************************************************************/

static int g_save(tealet_sub_t* g, char* stop, int fail_ok)
{
    /* Save more of g's stack into the heap -- at least up to 'stop'

       In the picture below, the C stack is on the left, growing down,
       and the C heap on the right.  The area marked with xxx is the logical
       stack of the tealet 'g'.  It can be half in the C stack (its older
       part), and half in the heap (its newer part).

       g->stack_stop |________|
                     |xxxxxxxx|
                     |xxx __ stop       .........
                     |xxxxxxxx|    ==>  :       :
                     |________|         :_______:
                     |        |         |xxxxxxx|
                     |        |         |xxxxxxx|
      g->stack_start |        |         |_______| g->stack_copy

     */
    ptrdiff_t sz1 = g->stack_saved;
    ptrdiff_t sz2 = STACK_SUB(stop, g->stack_start);
    assert(g->stack_stop != NULL); /* it is not exiting */
    assert(STACK_LE(stop, g->stack_stop));

    if (sz2 > sz1) {
        tealet_main_t *g_main = (tealet_main_t *)g->base.main;
        char* c = stack_grow(g_main, g->stack_copy, sz1, sz2);
        if (c == NULL) {
            if (fail_ok)
                return -1;
            /* we cannot signal a failure, either because this is an exit
             * switch, or the user is doing an emergency switch, ignoring
             * failures.
             * We must therefore mark this tealet's saved state as
             * invalid, so that we can't switch to it again.
             */
            g->stack_saved = (size_t)-1; /* invalid saved stack */
            return 0;
        }
#if STACK_DIRECTION == 0
        memcpy(c+sz1, g->stack_start+sz1, sz2-sz1);
#else
        memmove(c+sz2-sz1, c, sz1);
        memcpy(c, stop, sz2-sz1);
#endif
        g->stack_copy = c;
        g->stack_saved = sz2;
    }
    return 0;
}

/* main->g_target contains the tealet we are switching to:
 * target->stack_stop is the limit to which we must save the old stack
 * target->stack_start can be NULL, indicating that the target stack
 * needs not be restored.
 */
static void *g_save_state(void *old_stack_pointer, void *main)
{
    /* must free all the C stack up to target->stack_stop */
    tealet_main_t *g_main = (tealet_main_t *)main;
    tealet_sub_t *g_target = g_main->g_target;
    tealet_sub_t *g_current = g_main->g_current;
    char* target_stop = g_target->stack_stop;
    int exiting;
    assert(target_stop != NULL);
    assert(g_current != g_target);
    assert(g_current->stack_saved == 0);
    assert(g_current->stack_start == NULL);

    exiting = g_current->stack_stop == NULL;
    if (exiting) {
        /* tealet is exiting. We don't save its stack, and delete it, but
         * may need to save other stacks on demand
         */
        tealet_sub_t *g;
        assert(!TEALET_IS_MAIN(g_current));
        g = g_current;
        g_current = g_current->stack_prev;
        g_free(g_main, g);
    } else
        g_current->stack_start = old_stack_pointer;

    /* save and unlink tealets that are completely within
     * the area to clear. 
     */
    while (g_current != NULL && STACK_LE(g_current->stack_stop, target_stop)) {
        tealet_sub_t *prev = g_current->stack_prev;
        if (g_current != g_target) {            /* but don't save the target */
            assert(!TEALET_IS_MAIN(g_current)); /* never completely save main */
            if (g_save(g_current, g_current->stack_stop, exiting) == -1) {
                /* make sure that stack chain is intact if we have error */
                if (g_current != g_main->g_current)
                    g_main->g_current->stack_prev = g_current;
                return (void *)-1; /* error */
            }
        }
        g_current->stack_prev = NULL;
        g_current = prev;
    }

    /* save a partial stack */
    if (g_current != NULL && g_save(g_current, target_stop, exiting) == -1)
        return (void *) -1; /* error */

    assert(g_target->stack_prev == NULL);
    g_target->stack_prev = g_current;
      
    if (g_target->stack_start == NULL)
        return (void *)1; /* don't restore */

    return g_target->stack_start;
}

static void *g_restore_state(void *new_stack_pointer, void *main)
{
    tealet_main_t *g_main = (tealet_main_t *)main;
    tealet_sub_t *g = g_main->g_target;

    /* Restore the heap copy back into the C stack */
    assert(g->stack_start != NULL);
    if (g->stack_saved != 0) {
        size_t stack_saved = g->stack_saved;
#if STACK_DIRECTION == 0
        memcpy(g->stack_start, g->stack_copy, stack_saved);
#else
        memcpy(g->stack_start - stack_saved, g->stack_copy, stack_saved);
#endif
        stack_free(g_main, g->stack_copy);
        g->stack_copy = NULL;
        g->stack_saved = 0;
    }
    g->stack_start = NULL; /* mark as running */
    return NULL;
}

static int g_switchstack(tealet_main_t *g_main)
{
    /* note: we can't pass g_target simply as an argument here, because
     of the mix between different call stacks: after slp_switch() it
     might end up with a different value.  But g_main is safe, because
     it should have always the same value before and after the switch. */
    void *res;
    assert(g_main->g_target);
    assert(g_main->g_target != g_main->g_current);
    /* if the target saved stack is invalid (due to a failure to save it
    * during the exit of another tealet), we detect this here and
    * report an error
    * return value is:
    *  0 = successful switch
    *  1 = successful save only
    * -1 = error, couldn't save state
    * -2 = error, target tealet corrupt
    */
    if (g_main->g_target->stack_saved == (size_t)-1)
        return -2;
    res = slp_switch(g_save_state, g_restore_state, g_main);
    if ((ptrdiff_t)res >= 0)
        g_main->g_current = g_main->g_target;
    g_main->g_target = NULL;
    return (ptrdiff_t)res;
}

/* This function gets called for two cases:  In the first,
 * case, we are initializing and switching to a new stub,
 * in order to immediately start a new tealet's execution.
 * In this case, g_main->run will be non-zero.
 * The other case is when we are just saving the current
 * execution state in the stub, in order to reawaken it
 * later.  In this case, g_main->run is zero.
 */
static int g_initialstub(tealet_main_t *g_main, long *dummymarker)
{
    int result;
    tealet_sub_t *g_current = g_main->g_current;
    tealet_sub_t *g_target = g_main->g_target;
    assert(g_target->stack_start == NULL);
    g_target->stack_stop = (char *)dummymarker;
    
    if (g_main->g_run == NULL) {
        /* if are saving the execution state in the stub, we set
         * things up so that the stub is running, and then switch back
         * from it to our caller.
         */
        g_target->stack_prev = g_main->g_current;
        g_main->g_target = g_current;
        g_main->g_current = g_target;
    }
    /* The following call can return multiple times.  The first
     * time it returns with 1, when the stub is saved.
     * Then it can return with 0 when there is a switch into the
     * stub.
     */
    result = _tealet_switchstack(g_main);
    if (result < 0) {
        /* couldn't allocate stack */
        g_main->g_current = g_current;
        return result;
    }

    if (g_main->g_run) {
        /* this is the invocation of a new tealet */
        tealet_sub_t *g, *g_target;
        tealet_run_t run = g_main->g_run;
        void *run_arg = g_main->g_run_arg;
        g_main->g_run = NULL;
        g_main->g_run_arg = NULL;
        g = g_main->g_current;
        assert(g->stack_start == NULL);     /* running */      
#ifdef DEBUG_DUMP
          printf("starting %p\n", g);
#endif

        g_target = (tealet_sub_t *)(run((tealet_t *)g, run_arg));
        if (!g_target)
            g_target = &g_main->base;
        assert(g_target != g);
        assert(TEALET_MAIN(g_target) == g_main);
        assert(g_main->g_current == g);
#ifdef DEBUG_DUMP
        printf("ending %p -> %p\n", g, g_target);
#endif
        assert(g->stack_copy == NULL);
        g->stack_stop = NULL;              /* dying */
        g_main->g_target = g_target;
        _tealet_switchstack(g_main);
        assert(!"This point should not be reached");
    }
    return 0;
}

static tealet_sub_t *tealet_alloc(tealet_main_t *g_main, tealet_alloc_t *alloc)
{
    size_t size;
    tealet_sub_t *g;
    size = g_main == NULL ? sizeof(tealet_main_t) : sizeof(tealet_sub_t);
    g = alloc->malloc_p(size, alloc->context);
    if (g == NULL)
        return NULL;
    if (g_main == NULL)
        g_main = (tealet_main_t *)g;
    g->base.main = (tealet_t *)g_main;
    g->base.data = NULL;
    g->stack_start = NULL;
    g->stack_stop = NULL;
    g->stack_copy = NULL;
    g->stack_saved = 0;
    g->stack_prev = NULL;
#ifdef DEBUG_DUMP
    g->counter = counter++;
#endif
    return g;
}

static int tealet_new_int(tealet_t *main, tealet_run_t run, void *run_arg, tealet_sub_t **res)
{
    long dummymarker;
    int result;
    tealet_main_t *g_main = (tealet_main_t *)main->main;
    assert(TEALET_IS_MAIN(g_main));
    assert(!g_main->g_target);
    assert(!g_main->g_run);
    assert(!g_main->g_run_arg);
    g_main->g_target = tealet_alloc(g_main, &g_main->g_alloc);
    if (g_main->g_target == NULL)
        return -1; /* Could not allocate */
    if (res != NULL)
        *res = g_main->g_target;
    g_main->g_run = run;
    g_main->g_run_arg = run_arg;
    result = _tealet_initialstub(g_main, &dummymarker);
    if (result < 0) {
        /* could not save stack */
        g_free(g_main, g_main->g_target);
        g_main->g_target = NULL;
        g_main->g_run = NULL;
        g_main->g_run_arg = NULL;
        return result;
    }
    return 0;
}

/************************************************************/

static tealet_alloc_t stdalloc = TEALET_MALLOC;

tealet_t *tealet_initialize(tealet_alloc_t *alloc)
{
    /* NB. there are a lot of local variables with names starting with 'g_'.
       In the original stackless and greenlet code these were typically
       globals.  There are no global variables left in tealets. */
    tealet_sub_t *g;
    tealet_main_t *g_main;
    if (alloc == NULL)
      alloc = &stdalloc;
    g = tealet_alloc(NULL, alloc);
    if (g == NULL)
        return NULL;
    g_main = (tealet_main_t *)g;
    g->stack_start = NULL;
    g->stack_stop = STACK_STOP_MAIN;
    g_main->g_current = g;
    g_main->g_target = NULL;
    g_main->g_run = NULL;
    g_main->g_run_arg = NULL;
    g_main->g_alloc = *alloc;
    assert(TEALET_IS_MAIN(g_main));
    /* set up the following field with an indirection, which is needed
     to prevent any inlining */
    _tealet_initialstub = g_initialstub;
    _tealet_switchstack = g_switchstack;
    return (tealet_t *)g_main;
}

void tealet_finalize(tealet_t *main)
{
    tealet_main_t *g_main = (tealet_main_t *)main;
    assert(TEALET_IS_MAIN(g_main));
    assert(g_main->g_current == (tealet_sub_t *)g_main);
    g_free(g_main, g_main);
}

int tealet_new(tealet_t *main, tealet_run_t run, void *run_arg)
{
    return tealet_new_int(main, run, run_arg, NULL);
}
 
tealet_t *tealet_current(tealet_t *main)
{
    tealet_main_t *g_main = (tealet_main_t *)main;
    assert(TEALET_IS_MAIN(g_main));
    return (tealet_t *)g_main->g_current;
}

int tealet_switch(tealet_t *target)
{
    tealet_sub_t *g_target = (tealet_sub_t *)target;
    tealet_main_t *g_main = TEALET_MAIN(g_target);
    int result = 0;
    if (g_target != g_main->g_current) {
    #ifdef DEBUG_DUMP
        printf("switch %p -> %p\n", g_main->g_current, g_target);
    #endif
        g_main->g_target = g_target;
        result = _tealet_switchstack(g_main);
    #ifdef DEBUG_DUMP
        printf("done switching, res=%d, now in %p\n", result, g_main->g_current);
    #endif
    }
    return result;
}

int tealet_exit(tealet_t *target)
{
    tealet_sub_t *g_target = (tealet_sub_t *)target;
    tealet_main_t *g_main = TEALET_MAIN(g_target);
    char *stack_stop = g_target->stack_stop;
    int result;
    if (TEALET_IS_MAIN(g_target) || g_target == g_main->g_current)
        return -2; /* invalid tealet */

    g_target->stack_stop = NULL; /* signal exit */
    g_main->g_target = g_target;
    result = _tealet_switchstack(g_main);
    assert(result < 0); /* only return here if there was failure */
    g_target->stack_stop = stack_stop;
    return result;
}

tealet_t *tealet_stub_new(tealet_t *main)
{
    tealet_sub_t *g_result;
    if (tealet_new_int(main, NULL, NULL, &g_result) < 0)
        return NULL;
    assert(g_result->stack_copy);
    assert(STACK_SUB(g_result->stack_stop, g_result->stack_start) == g_result->stack_saved);
    return (tealet_t*)g_result;
}

int tealet_stub_run(tealet_t *stub, tealet_run_t run, void *run_arg)
{
    tealet_sub_t *g_target = (tealet_sub_t *)stub;
    tealet_main_t *g_main = TEALET_MAIN(g_target);
    int result = 0;
    assert(g_target != g_main->g_current && g_target != (tealet_sub_t*)g_main);
    assert(g_main->g_run == 0);
    assert(g_main->g_run_arg == 0);
    g_main->g_run = run;
    g_main->g_run_arg = run_arg;
#ifdef DEBUG_DUMP
    printf("stub run %p -> %p\n", g_main->g_current, g_target);
#endif
    g_main->g_target = g_target;
    result = _tealet_switchstack(g_main);
#ifdef DEBUG_DUMP
    printf("done stub_run, res=%d, now in %p\n", result, g_main->g_current);
#endif
    return result;
}

#ifndef TEALET_NO_SHARING
tealet_t *tealet_duplicate(tealet_t *tealet)
{
    tealet_sub_t *g_tealet = (tealet_sub_t *)tealet;
    tealet_main_t *g_main = TEALET_MAIN(g_tealet);
    tealet_sub_t *g_copy;
    assert(g_tealet != g_main->g_current && g_tealet != (tealet_sub_t*)g_main);
    g_copy = tealet_alloc(g_main, &g_main->g_alloc);
    if (g_copy == NULL)
        return NULL;
    *g_copy = *g_tealet;
    g_copy->stack_copy = stack_dup(g_copy->stack_copy);
    return (tealet_t*)g_copy;
}
#endif

void tealet_delete(tealet_t *target)
{
    tealet_sub_t *g_target = (tealet_sub_t *)target;
    tealet_main_t *g_main = TEALET_MAIN(g_target);
    /* XXX this is wrong.  Deleting a random tealet is delicate,
       because it can be part of the stack_prev chained list */
    stack_free(g_main, g_target->stack_copy);
    g_free(g_main, g_target);
}

#if STACK_DIRECTION != 0
#  error "fix _tealet_translate_pointer below"
#endif
char **_tealet_translate_pointer(tealet_t *context, char **ptr)
{
  tealet_sub_t *g_tealet = (tealet_sub_t *)context;
  /* if g_tealet is not suspended, then stack_start is probably NULL,
     giving nonsense in the following computation.  But then stack_saved
     is 0, so the following test can never be true. */
  char *p = (char *)ptr;
  long delta = p - g_tealet->stack_start;
  if (((unsigned long)delta) < ((unsigned long)g_tealet->stack_saved)) {
    /* a pointer to a saved away word */
    return (char **)(g_tealet->stack_copy + delta);
  }
  return ptr;
}
