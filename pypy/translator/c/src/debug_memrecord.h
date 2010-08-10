#include <stdio.h>


extern FILE* debug_memrecord_f;

void debug_memrecord_startup(void);

struct debug_memrecord_s {
  void *a, *b, *c, *d, *e;
};

#define DEBUG_MEMREC(a1, b1, c1, d1, e1)  do {                  \
  struct debug_memrecord_s _dmr_s;                              \
  _dmr_s.a = (void*)(a1);                                       \
  _dmr_s.b = (void*)(b1);                                       \
  _dmr_s.c = c1;                                                \
  _dmr_s.d = d1;                                                \
  _dmr_s.e = e1;                                                \
  fwrite_unlocked(&_dmr_s, sizeof(struct debug_memrecord_s), 1, \
                  debug_memrecord_f);                           \
} while(0)

#define RPyWrite(posid, container, targetexpr, newvalue)        \
  DEBUG_MEMREC(posid,                                           \
               ((struct pypy_header0 *)(container))->h_tid,     \
               &(targetexpr),                                   \
               targetexpr, newvalue);                           \
  targetexpr = newvalue

#undef OP_RAW_MEMCLEAR
#define OP_RAW_MEMCLEAR(p, size, r)                             \
  memset((void*)p, 0, size);                                    \
  DEBUG_MEMREC(-1, (void*)p, (void*)size, ((char*)p)+size, (void*)0)

/************************************************************/

#ifndef PYPY_NOT_MAIN_FILE

FILE* debug_memrecord_f;

void debug_memrecord_startup(void)
{
  debug_memrecord_f = fopen("debug_memrecord", "wb");
  assert(debug_memrecord_f);
}

#endif
