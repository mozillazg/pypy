#include <stdio.h>


extern FILE* debug_memrecord_f;

void debug_memrecord_startup(void);

struct debug_memrecord_s {
  long a;
  void *b, *c, *d;
};

#define DEBUG_MEMREC(a1, b1, c1, d1)  do {                      \
  struct debug_memrecord_s _dmr_s;                              \
  _dmr_s.a = a1;                                                \
  _dmr_s.b = b1;                                                \
  _dmr_s.c = c1;                                                \
  _dmr_s.d = d1;                                                \
  fwrite_unlocked(&_dmr_s, sizeof(struct debug_memrecord_s), 1, \
                  debug_memrecord_f);                           \
} while(0)

#define RPyWrite(posid, targetexpr, newvalue)                   \
  DEBUG_MEMREC(posid, &(targetexpr), targetexpr, newvalue);     \
  targetexpr = newvalue

/************************************************************/

#ifndef PYPY_NOT_MAIN_FILE

FILE* debug_memrecord_f;

void debug_memrecord_startup(void)
{
  debug_memrecord_f = fopen("debug_memrecord", "wb");
  assert(debug_memrecord_f);
}

#endif
