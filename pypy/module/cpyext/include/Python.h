#ifndef Py_PYTHON_H
#define Py_PYTHON_H

/* Compat stuff */
#ifndef _WIN32
# include <inttypes.h>
# include <stdint.h>
# include <stddef.h>
# include <limits.h>
# define Py_DEPRECATED(VERSION_UNUSED) __attribute__((__deprecated__))
# define PyAPI_DATA(RTYPE) extern RTYPE
#else
# define MS_WIN32 1
# include <crtdefs.h>
# define Py_DEPRECATED(VERSION_UNUSED)
# ifdef Py_BUILD_CORE
#  define PyAPI_DATA(RTYPE) extern __declspec(dllexport) RTYPE
# else
#  define PyAPI_DATA(RTYPE) extern __declspec(dllimport) RTYPE
# endif
#endif

#define Py_ssize_t long
#define PY_SSIZE_T_MAX ((Py_ssize_t)(((size_t)-1)>>1))
#define PY_SSIZE_T_MIN (-PY_SSIZE_T_MAX-1)
#define Py_SAFE_DOWNCAST(VALUE, WIDE, NARROW) (NARROW)(VALUE)
// obviously wrong

// from pyport.h
#ifdef SIZE_MAX
#define PY_SIZE_MAX SIZE_MAX
#else
#define PY_SIZE_MAX ((size_t)-1)
#endif

/* Convert a possibly signed character to a nonnegative int */
/* XXX This assumes characters are 8 bits wide */
#ifdef __CHAR_UNSIGNED__
#define Py_CHARMASK(c)		(c)
#else
#define Py_CHARMASK(c)		((unsigned char)((c) & 0xff))
#endif

#define statichere static

#define Py_MEMCPY memcpy

#include <pypy_macros.h>

int PyOS_snprintf(char *str, size_t size, const  char  *format, ...);
#include "patchlevel.h"

#include "object.h"
#include "pyport.h"
#include "warnings.h"

#include <stdarg.h>
#include <stdio.h>
#include <string.h>
#include <assert.h>
#include <locale.h>
#include <ctype.h>
#include <stdlib.h>

#include "pyconfig.h"

#include "boolobject.h"
#include "floatobject.h"
#include "methodobject.h"

#include "modsupport.h"
#include "pythonrun.h"
#include "pyerrors.h"
#include "stringobject.h"
#include "descrobject.h"
#include "tupleobject.h"
#include "dictobject.h"
#include "intobject.h"
#include "listobject.h"
#include "unicodeobject.h"
#include "eval.h"
#include "pymem.h"
#include "pycobject.h"
#include "bufferobject.h"
#include "sliceobject.h"

// XXX This shouldn't be included here
#include "structmember.h"

#include <pypy_decl.h>

/* Define macros for inline documentation. */
#define PyDoc_VAR(name) static char name[]
#define PyDoc_STRVAR(name,str) PyDoc_VAR(name) = PyDoc_STR(str)
#ifdef WITH_DOC_STRINGS
#define PyDoc_STR(str) str
#else
#define PyDoc_STR(str) ""
#endif

#endif
