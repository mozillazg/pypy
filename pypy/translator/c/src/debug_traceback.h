/**************************************************************/
 /***  C header subsection: RPython tracebacks for debugging ***/


#define PYPY_DEBUG_TRACEBACK_DEPTH      8

#define OP_DEBUG_START_TRACEBACK()                              \
  pypy_debug_traceback_count = PYPY_DEBUG_TRACEBACK_DEPTH

#define PYPY_DEBUG_RECORD_TRACEBACK(funcname)                           \
  if ((--pypy_debug_traceback_count) >= 0) {                            \
    static struct pydtentry_s entry = { PYPY_FILE_NAME, funcname, __LINE__ }; \
    pypy_debug_tracebacks[pypy_debug_traceback_count] = &entry;         \
  }

/* Format of the data: to represent a location in the source code, we
   use for now just a pointer to a 'pypy_debug_traceback_entry_s'.
*/
struct pydtentry_s {
  const char *filename;
  const char *funcname;
  int lineno;
};

extern int pypy_debug_traceback_count;
extern struct pydtentry_s *pypy_debug_tracebacks[PYPY_DEBUG_TRACEBACK_DEPTH];

void pypy_debug_catch_exception(void);


/************************************************************/


#ifndef PYPY_NOT_MAIN_FILE

int pypy_debug_traceback_count = PYPY_DEBUG_TRACEBACK_DEPTH;
struct pydtentry_s *pypy_debug_tracebacks[PYPY_DEBUG_TRACEBACK_DEPTH];

void pypy_debug_traceback_print(void)
{
  int i, lineno;
  const char *filename;
  const char *funcname;

  fprintf(stderr, "RPython traceback:\n");
  for (i=PYPY_DEBUG_TRACEBACK_DEPTH-1; i>=0; i--)
    {
      if (i < pypy_debug_traceback_count)
        break;
      filename = pypy_debug_tracebacks[i]->filename;
      funcname = pypy_debug_tracebacks[i]->funcname;
      lineno   = pypy_debug_tracebacks[i]->lineno;
      fprintf(stderr, "  File \"%s\", line %d, in %s\n",
              filename, lineno, funcname);
    }
}

void pypy_debug_catch_exception(void)
{
  pypy_debug_traceback_print();
  fprintf(stderr, "Fatal RPython error: %s\n",
          RPyFetchExceptionType()->ov_name->items);
  abort();
}

#endif /* PYPY_NOT_MAIN_FILE */
