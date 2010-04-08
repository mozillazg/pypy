#include <stdlib.h>


#define PyMem_MALLOC(n)		malloc((n) ? (n) : 1)
#define PyMem_REALLOC(p, n)	realloc((p), (n) ? (n) : 1)
#define PyMem_FREE		free

/* XXX use obmalloc like cpython and pypy do, otherwise we might get segfaults */
#define PyObject_MALLOC		PyMem_MALLOC
//#define PyObject_REALLOC	PyMem_REALLOC
#define PyObject_FREE		PyMem_FREE

#define PyMem_Malloc PyMem_MALLOC
#define PyMem_Free  PyMem_FREE
