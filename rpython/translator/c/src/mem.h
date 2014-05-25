
/************************************************************/
/***  C header subsection: operations on LowLevelTypes    ***/

#include <string.h>

/* used by rpython.rlib.rstack, but also by asmgcc */
#define OP_STACK_CURRENT(r)  r = (Signed)&r


#define OP_RAW_MALLOC(size, r, restype)  {				\
	r = (restype) PyObject_Malloc(size);				\
	if (r != NULL) {						\
	    COUNT_MALLOC;						\
	}								\
    }

#define OP_RAW_FREE(p, r) PyObject_Free(p); COUNT_FREE;

#define OP_RAW_MEMCLEAR(p, size, r) memset((void*)p, 0, size)

#define OP_RAW_MALLOC_USAGE(size, r) r = size

#if defined(MS_WINDOWS) && !defined(__MINGW32__)
#define alloca  _alloca
#endif

#define OP_STACK_MALLOC(size,r,restype)                                 \
    r = (restype) alloca(size);                                         \
    if (r != NULL) memset((void*) r, 0, size);
    
#define OP_RAW_MEMCOPY(x,y,size,r) memcpy(y,x,size);
#define OP_RAW_MEMMOVE(x,y,size,r) memmove(y,x,size);

/************************************************************/

#define OP_FREE(p)	OP_RAW_FREE(p, do_not_use)

#ifndef COUNT_OP_MALLOCS

#define COUNT_MALLOC	/* nothing */
#define COUNT_FREE	/* nothing */
#define pypy_malloc_counters_results()  /* nothing */

#else /* COUNT_OP_MALLOCS */

static int count_mallocs=0, count_frees=0;

#define COUNT_MALLOC	count_mallocs++
#define COUNT_FREE	count_frees++

#define pypy_malloc_counters_results()  \
    printf("MALLOC COUNTERS: %d %d\n", count_mallocs, count_frees)

#endif /* COUNT_OP_MALLOCS */


/*** tracking raw mallocs and frees for debugging ***/

#ifndef RPY_ASSERT

#  define OP_TRACK_ALLOC_START(addr, r)   /* nothing */
#  define OP_TRACK_ALLOC_STOP(addr, r)    /* nothing */
#  define pypy_debug_alloc_results() /* nothing */

#else /* RPY_ASSERT */

#  define OP_TRACK_ALLOC_START(addr, r)  pypy_debug_alloc_start(addr, \
                                                                __FUNCTION__)
#  define OP_TRACK_ALLOC_STOP(addr, r)   pypy_debug_alloc_stop(addr)

void pypy_debug_alloc_start(void*, const char*);
void pypy_debug_alloc_stop(void*);
void pypy_debug_alloc_results(void);

#endif /* RPY_ASSERT */

/* for Boehm GC */

#ifdef PYPY_USING_BOEHM_GC

#define BOEHM_MALLOC_0_0   GC_MALLOC
#define BOEHM_MALLOC_1_0   GC_MALLOC_ATOMIC
#define BOEHM_MALLOC_0_1   GC_MALLOC
#define BOEHM_MALLOC_1_1   GC_MALLOC_ATOMIC
/* #define BOEHM_MALLOC_0_1   GC_MALLOC_IGNORE_OFF_PAGE */
/* #define BOEHM_MALLOC_1_1   GC_MALLOC_ATOMIC_IGNORE_OFF_PAGE */

#define OP_BOEHM_ZERO_MALLOC(size, r, restype, is_atomic, is_varsize) { \
	r = (restype) BOEHM_MALLOC_ ## is_atomic ## _ ## is_varsize (size); \
	if (r && is_atomic)  /* the non-atomic versions return cleared memory */ \
	    memset((void*) r, 0, size);					\
    }

#define OP_BOEHM_DISAPPEARING_LINK(link, obj, r)			\
    if (GC_base(obj) == NULL)						\
	; /* 'obj' is probably a prebuilt object - it makes no */	\
    /* sense to register it then, and it crashes Boehm in */		\
    /* quite obscure ways */						\
    else								\
	GC_GENERAL_REGISTER_DISAPPEARING_LINK(link, obj)

extern int boehm_gc_finalizer_lock;
void boehm_gc_startup_code(void);
void boehm_gc_finalizer_notifier(void);

#define OP_GC__DISABLE_FINALIZERS(r)  boehm_gc_finalizer_lock++
#define OP_GC__ENABLE_FINALIZERS(r)  (boehm_gc_finalizer_lock--,	\
				      boehm_gc_finalizer_notifier())

#endif /* PYPY_USING_BOEHM_GC */


#ifdef PYPY_USING_NO_GC_AT_ALL
#define OP_BOEHM_ZERO_MALLOC(size, r, restype, is_atomic, is_varsize)	\
    r = (restype) calloc(1, size);
#define OP_BOEHM_DISAPPEARING_LINK(link, obj, r)  /* nothing */
#define OP_GC__DISABLE_FINALIZERS(r)  /* nothing */
#define OP_GC__ENABLE_FINALIZERS(r)  /* nothing */
#endif

/************************************************************/
/* weakref support */

#define OP_CAST_PTR_TO_WEAKREFPTR(x, r)  r = x
#define OP_CAST_WEAKREFPTR_TO_PTR(x, r)  r = x

/************************************************************/
/* dummy version of these operations, e.g. with Boehm */

#define OP_GC_GET_RPY_ROOTS(r)           r = 0
#define OP_GC_GET_RPY_REFERENTS(x, r)    r = 0
#define OP_GC_GET_RPY_MEMORY_USAGE(x, r) r = -1
#define OP_GC_GET_RPY_TYPE_INDEX(x, r)   r = -1
#define OP_GC_IS_RPY_INSTANCE(x, r)      r = 0
#define OP_GC_DUMP_RPY_HEAP(fd, r)       r = 0
#define OP_GC_SET_EXTRA_THRESHOLD(x, r)  /* nothing */


#ifdef PYPY_USE_ASMGCC
/****************************/
/* The "asmgcc" root finder */
/****************************/

/* Implementation of asmgcc, for Linux only */
extern char __gcmapstart;
extern char __gcmapend;
extern char __gccallshapes;
extern long pypy_asm_stackwalk(void*, void*);
#define __gcnoreorderhack __gcmapend

/* The following pseudo-instruction is used by --gcrootfinder=asmgcc
   just after a call to tell gcc to put a GCROOT mark on each gc-pointer
   local variable.  All such local variables need to go through a "v =
   pypy_asm_gcroot(v)".  The old value should not be used any more by
   the C code; this prevents the following case from occurring: gcc
   could make two copies of the local variable (e.g. one in the stack
   and one in a register), pass one to GCROOT, and later use the other
   one.  In practice the pypy_asm_gcroot() is often a no-op in the final
   machine code and doesn't prevent most optimizations. */

/* With gcc, getting the asm() right was tricky, though.  The asm() is
   not volatile so that gcc is free to delete it if the output variable
   is not used at all.  We need to prevent gcc from moving the asm()
   *before* the call that could cause a collection; this is the purpose
   of the (unused) __gcnoreorderhack input argument.  Any memory input
   argument would have this effect: as far as gcc knows the call
   instruction can modify arbitrary memory, thus creating the order
   dependency that we want. */

#define pypy_asm_gcroot(p) ({void*_r; \
	    asm ("/* GCROOT %0 */" : "=g" (_r) :       \
		 "0" (p), "m" (__gcnoreorderhack));    \
	    _r; })

#define pypy_asm_gc_nocollect(f) asm volatile ("/* GC_NOCOLLECT " #f " */" \
                                               : : )

#define pypy_asm_keepalive(v)  asm volatile ("/* keepalive %0 */" : : \
                                             "g" (v))

/* marker for trackgcroot.py, and inhibits tail calls */
#define pypy_asm_stack_bottom() { asm volatile ("/* GC_STACK_BOTTOM */" : : : \
                                  "memory"); pypy_check_stack_count(); }
#ifdef RPY_ASSERT
void pypy_check_stack_count(void);
#else
static void pypy_check_stack_count(void) { }
#endif


#define OP_GC_ASMGCROOT_STATIC(i, r)   r =	       \
	i == 0 ? (void*)&__gcmapstart :		       \
	i == 1 ? (void*)&__gcmapend :		       \
	i == 2 ? (void*)&__gccallshapes :	       \
	NULL


#else
/*********************************/
/* The "shadowstack" root finder */
/*********************************/

#if defined(__GNUC__) && defined(__amd64__)
//#  define RPY_SHADOWSTACK_REG  "r15"
#endif

struct rpy_shadowstack_s { void *s; };
#ifdef RPY_SHADOWSTACK_REG
register void *rpy_shadowstack asm(RPY_SHADOWSTACK_REG);
#else
extern void *rpy_shadowstack;
#endif

#define RPY_SS_GRAPH_MARKER(marker, count)              \
    ;                                                   \
    struct rpy_shadowstack_s a##marker[count + 1];      \
    a##marker[0].s = rpy_shadowstack;                   \
    marker = a##marker

#define RPY_SS_STORED(marker, count)                            \
    rpy_shadowstack = count > 0 ? (char *)(marker + count) - 2  \
                                : marker[0].s

static inline void pypy_asm_stack_bottom(void)
{
    void *s = pypy_g_rpython_memory_gctypelayout_GCData.gcd_inst_root_stack_top;
    rpy_shadowstack = s;
}

static inline void pypy_asm_stack_top(void)
{
    void *s = rpy_shadowstack;
    pypy_g_rpython_memory_gctypelayout_GCData.gcd_inst_root_stack_top = s;
}

#define OP_GETFIELD_EXC_TYPE(r)                                            \
    if (__builtin_expect(((Signed)rpy_shadowstack) & 1, 0)) {              \
        r = (struct pypy_object_vtable0 *)(((char *)rpy_shadowstack) - 1); \
        if (!r) __builtin_unreachable();                                   \
    }                                                                      \
    else {                                                                 \
        r = NULL;                                                          \
    }
#define OP_SETFIELD_EXC_TYPE(x, r)                      \
    rpy_shadowstack = (x) ? ((char *)(x)) + 1 : NULL


#endif
