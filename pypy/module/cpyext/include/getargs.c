
/* New getargs implementation */

#include "Python.h"

#include <ctype.h>


#ifdef __cplusplus
extern "C" { 
#endif

int PyArg_Parse(PyObject *, const char *, ...);
int PyArg_ParseTuple(PyObject *, const char *, ...);
int PyArg_VaParse(PyObject *, const char *, va_list);

int PyArg_ParseTupleAndKeywords(PyObject *, PyObject *,
				const char *, char **, ...);
int PyArg_VaParseTupleAndKeywords(PyObject *, PyObject *,
				const char *, char **, va_list);

#ifdef HAVE_DECLSPEC_DLL
/* Export functions */
/*PyAPI_FUNC(int) _PyArg_Parse_SizeT(PyObject *, char *, ...);
PyAPI_FUNC(int) _PyArg_ParseTuple_SizeT(PyObject *, char *, ...);
PyAPI_FUNC(int) _PyArg_ParseTupleAndKeywords_SizeT(PyObject *, PyObject *,
                                                  const char *, char **, ...);
PyAPI_FUNC(PyObject *) _Py_BuildValue_SizeT(const char *, ...);
PyAPI_FUNC(int) _PyArg_VaParse_SizeT(PyObject *, char *, va_list);
PyAPI_FUNC(int) _PyArg_VaParseTupleAndKeywords_SizeT(PyObject *, PyObject *,
const char *, char **, va_list);*/
#endif

#define FLAG_COMPAT 1
#define FLAG_SIZE_T 2


/* Forward */
int pypy_vgetargs1(struct _object *, char *, va_list *, int);
  //static void seterror(int, const char *, int *, const char *, const char *);
  //static char *convertitem(PyObject *, const char **, va_list *, int, int *, 
  //                       char *, size_t, PyObject **);
//static char *converttuple(PyObject *, const char **, va_list *, int,
//			  int *, char *, size_t, int, PyObject **);
//static char *convertsimple(PyObject *, const char **, va_list *, int, char *,
//			   size_t, PyObject **);
//static Py_ssize_t convertbuffer(PyObject *, void **p, char **);
//static int getbuffer(PyObject *, Py_buffer *, char**);

//static int vgetargskeywords(PyObject *, PyObject *,
//			    const char *, char **, va_list *, int);
//static char *skipitem(const char **, va_list *, int);

int
PyArg_Parse(PyObject *args, const char *format, ...)
{
	int retval;
	va_list va;
	
	va_start(va, format);
	retval = pypy_vgetargs1(args, format, &va, FLAG_COMPAT);
	va_end(va);
	return retval;
}

int
_PyArg_Parse_SizeT(PyObject *args, char *format, ...)
{
	int retval;
	va_list va;
	
	va_start(va, format);
	retval = pypy_vgetargs1(args, format, &va, FLAG_COMPAT|FLAG_SIZE_T);
	va_end(va);
	return retval;
}


int
PyArg_ParseTuple(PyObject *args, const char *format, ...)
{
	int retval;
	va_list va;
	
	va_start(va, format);
	retval = pypy_vgetargs1(args, format, &va, 0);
	va_end(va);
	return retval;
}

int
_PyArg_ParseTuple_SizeT(PyObject *args, char *format, ...)
{
	int retval;
	va_list va;
	
	va_start(va, format);
	retval = pypy_vgetargs1(args, format, &va, FLAG_SIZE_T);
	va_end(va);
	return retval;
}


int
PyArg_VaParse(PyObject *args, const char *format, va_list va)
{
	va_list lva;

#ifdef VA_LIST_IS_ARRAY
	memcpy(lva, va, sizeof(va_list));
#else
#ifdef __va_copy
	__va_copy(lva, va);
#else
	lva = va;
#endif
#endif

	return pypy_vgetargs1(args, format, &lva, 0);
}

int
_PyArg_VaParse_SizeT(PyObject *args, char *format, va_list va)
{
	va_list lva;

#ifdef VA_LIST_IS_ARRAY
	memcpy(lva, va, sizeof(va_list));
#else
#ifdef __va_copy
	__va_copy(lva, va);
#else
	lva = va;
#endif
#endif

	return pypy_vgetargs1(args, format, &lva, FLAG_SIZE_T);
}


// REST IS NOT COPIED FROM CPYTHON
