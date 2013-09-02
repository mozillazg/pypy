#include "common_header.h"
#include "structdef.h"
#include "forwarddecl.h"
#include "preimpl.h"
#include "src/exception.h"

#if defined(PYPY_CPYTHON_EXTENSION)
   PyObject *RPythonError;
#endif 

/******************************************************************/
#ifdef HAVE_RTYPER               /* RPython version of exceptions */
/******************************************************************/

void RPyDebugReturnShowException(const char *msg, const char *filename,
                                 long lineno, const char *functionname)
{
#ifdef DO_LOG_EXC
  fprintf(stderr, "%s %s: %s:%ld %s\n", msg,
          RPyFetchExceptionType()->ov_name->items,
          filename, lineno, functionname);
#endif
}

/* Hint: functions and macros not defined here, like RPyRaiseException,
   come from exctransformer via the table in extfunc.py. */

void _RPyRaiseSimpleException(RPYTHON_EXCEPTION rexc)
{
	/* XXX msg is ignored */
	RPyRaiseException(RPYTHON_TYPE_OF_EXC_INST(rexc), rexc);
}


/******************************************************************/
#endif                                             /* HAVE_RTYPER */
/******************************************************************/
