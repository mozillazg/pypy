/************************************************************/
 /***  C header subsection: debug_print & related tools    ***/


/* macros used by the generated code */
#define PYPY_DEBUG_ENABLED     (pypy_debug_enabled && pypy_debug_is_ready())
#define PYPY_DEBUG_FILE        pypy_debug_file
#define PYPY_DEBUG_START(cat)  if (pypy_debug_enabled) pypy_debug_start(cat)
#define PYPY_DEBUG_STOP(cat)   if (pypy_debug_enabled) pypy_debug_stop(cat)


/************************************************************/

/* prototypes (internal use only) */
bool_t pypy_debug_is_ready(void);
void pypy_debug_start(const char *category);
void pypy_debug_stop(const char *category);

extern bool_t pypy_debug_enabled;
extern FILE *pypy_debug_file;


/* implementations */

#ifndef PYPY_NOT_MAIN_FILE
#include <sys/time.h>

static bool_t pypy_debug_initialized = 0;
bool_t pypy_debug_enabled = 1;   /* set to 0 if PYPYLOG is not defined */
FILE *pypy_debug_file;

static void pypy_debug_open(void)
{
  char *filename = getenv("PYPYLOG");
  if (filename && filename[0])
    {
      if (filename[0] == '-' && filename[1] == 0)
        pypy_debug_file = stderr;
      else
        pypy_debug_file = fopen(filename, "w");
    }
  else
    {
      pypy_debug_file = NULL;
    }
  pypy_debug_enabled = (pypy_debug_file != NULL);
  pypy_debug_initialized = 1;
}

bool_t pypy_debug_is_ready(void)
{
  if (!pypy_debug_initialized)
    pypy_debug_open();
  return pypy_debug_enabled;
}


/* XXXXXXXXXX   x86 Pentium only! */
#define READ_TIMESTAMP(val) \
     __asm__ __volatile__("rdtsc" : "=A" (val))


static void pypy_debug_category(const char *start, const char *category)
{
  long long timestamp;
  if (!pypy_debug_is_ready())
    return;
  READ_TIMESTAMP(timestamp);
  fprintf(pypy_debug_file, "{%llx} -%s- %s\n", timestamp, start, category);
}

void pypy_debug_start(const char *category)
{
  pypy_debug_category("start", category);
}

void pypy_debug_stop(const char *category)
{
  pypy_debug_category("stop", category);
}

#endif /* PYPY_NOT_MAIN_FILE */
