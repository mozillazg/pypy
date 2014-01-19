#include "common_header.h"
#include <src/support.h>
#include <src/commondefs.h>
#include <src/mem.h>
#include <src/instrument.h>

/************************************************************/
/***  C header subsection: support functions              ***/

#include <stdio.h>
#include <stdlib.h>

/*** misc ***/

void RPyAssertFailed(const char* filename, long lineno,
                     const char* function, const char *msg) {
  fprintf(stderr,
          "PyPy assertion failed at %s:%ld:\n"
          "in %s: %s\n",
          filename, lineno, function, msg);
  abort();
}

void RPyAbort(void) {
  fprintf(stderr, "Invalid RPython operation (NULL ptr or bad array index)\n");
  abort();
}


void rpython_special_startup()
{
#ifdef PYPY_X86_CHECK_SSE2_DEFINED
    pypy_x86_check_sse2();
#endif
    instrument_setup();

#ifndef MS_WINDOWS
    /* this message does no longer apply to win64 :-) */
    if (sizeof(void*) != SIZEOF_LONG) {
        fprintf(stderr, "Only support platforms where sizeof(void*) == "
                        "sizeof(long), for now\n");
        abort();
    }
#endif
}

void rpython_special_shutdown()
{
    pypy_debug_alloc_results();
    pypy_malloc_counters_results();
}
