#ifndef Py_UNICODEOBJECT_H
#define Py_UNICODEOBJECT_H

#ifdef __cplusplus
extern "C" {
#endif


typedef unsigned int Py_UCS4;
#ifdef HAVE_USABLE_WCHAR_T
#define PY_UNICODE_TYPE wchar_t
#elif Py_UNICODE_SIZE == 4
#define PY_UNICODE_TYPE Py_UCS4
#else
#define PY_UNICODE_TYPE unsigned short
#endif
typedef PY_UNICODE_TYPE Py_UNICODE;

#define Py_UNICODE_REPLACEMENT_CHARACTER ((Py_UNICODE) 0xFFFD)

typedef struct {
    PyObject_VAR_HEAD
    Py_UNICODE ob_uval_pypy[1];
} PyUnicodeObject;


/* Macro, trading safety for speed */
#define PyUnicode_GET_SIZE(op)   Py_SIZE(op)
#define PyUnicode_AS_UNICODE(op)  (                                       \
    ((PyUnicodeObject *)(op))->ob_uval_pypy[((PyUnicodeObject *)(op))->ob_size]\
    == 0 ? ((PyUnicodeObject *)(op))->ob_uval_pypy : PyUnicode_AsUnicode(op))

#define PyUnicode_AS_DATA(op)         ((char *)PyUnicode_AS_UNICODE(op))
#define PyUnicode_GET_DATA_SIZE(op)   (sizeof(Py_UNICODE) * Py_SIZE(op))


#ifdef __cplusplus
}
#endif
#endif /* !Py_UNICODEOBJECT_H */
