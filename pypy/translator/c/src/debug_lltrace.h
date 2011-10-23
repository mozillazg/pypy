
void _RPyTraceSet(void *addr, long newvalue, long mark);


#ifndef RPY_LL_TRACE /****************************************/


#  define RPY_IS_TRACING           0
#  define RPyTraceSet(ptr, mark)   /* nothing */
#  ifndef PYPY_NOT_MAIN_FILE
void _RPyTraceSet(void *addr, long newvalue, long mark) { }
#  endif


/* enable this for sending it out to stderr
#undef RPyTraceSet
#define RPyTraceSet(field, n)  {fprintf(stderr,"s %p->%p\n",\
                                &(field),(void*)(long)field);}
*/


#else /*******************************************************/

#  include "src/atomic_ops.h"


#  define RPY_IS_TRACING           1
#  define RPyTraceSet(ptr, mark)   _RPyTraceSet(&(ptr), (long)(ptr), mark)

#  ifndef PYPY_NOT_MAIN_FILE

struct _RPyTrace_s {
  long mark;
  void *addr;
  long newvalue;
};

static struct _RPyTrace_s *_RPyTrace_start   = NULL;
static struct _RPyTrace_s *_RPyTrace_stop    = NULL;
static struct _RPyTrace_s * volatile _RPyTrace_current = NULL;
static const long _RPyTrace_default_size = 0x4000000;

void _RPyTrace_Setup(void)
{
    /* not thread-safe, but assume that it's called very early anyway,
       when there is only one thread */
    char *csize = getenv("PYPYTRACEBUF");
    long size = csize ? atol(csize) : 0;
    if (size <= 1)
        size = _RPyTrace_default_size;
    _RPyTrace_start = calloc(size, sizeof(struct _RPyTrace_s));
    RPyAssert(_RPyTrace_start, "not enough memory to allocate the trace");
    _RPyTrace_stop = _RPyTrace_start + size;

    _RPyTrace_current = _RPyTrace_start;
    fprintf(stderr, "lltrace: buffer from %p to %p, size %ld entries\n",
            _RPyTrace_start, _RPyTrace_stop,
            (long)(_RPyTrace_stop - _RPyTrace_start));
}

void _RPyTraceSet(void *addr, long newvalue, long mark)
{
    struct _RPyTrace_s *current, *next;
    do {
        current = _RPyTrace_current;
        if (current == NULL) {
            _RPyTrace_Setup();
            current = _RPyTrace_current;
        }
        next = current + 1;
        if (next == _RPyTrace_stop) next = _RPyTrace_start;
    } while (!bool_cas((volatile unsigned long*)&_RPyTrace_current,
                       (unsigned long)current,
                       (unsigned long)next));
    current->mark = mark;
    current->addr = addr;
    current->newvalue = newvalue;
}

void _RPyTraceDump(void)
{
    char *start   = _RPyTrace_start;
    char *stop    = _RPyTrace_stop;
    char *current = (char *)_RPyTrace_current;
    FILE *f       = fopen("trace.dump", "wb");
    fwrite(current, 1, stop - current, f);
    fwrite(start,   1, current - start, f);
    fclose(f);
}

#  endif


#endif /******************************************************/
