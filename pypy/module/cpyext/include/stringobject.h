
/* String object interface */

#ifndef Py_STRINGOBJECT_H
#define Py_STRINGOBJECT_H
#ifdef __cplusplus
extern "C" {
#endif

/* Macro, trading safety for speed */
#define PyString_GET_SIZE(op)   Py_SIZE(op)
#define PyString_AS_STRING(op)  (                                       \
    ((PyStringObject *)(op))->ob_sval_pypy[((PyStringObject *)(op))->ob_size] \
    == 0 ? ((PyStringObject *)(op))->ob_sval_pypy : PyString_AsString(op))


typedef struct {
    PyObject_VAR_HEAD
    char ob_sval_pypy[1];
} PyStringObject;

PyAPI_FUNC(int) _PyString_Resize(PyObject **pv, Py_ssize_t newsize);
PyAPI_FUNC(PyObject *) PyString_FromFormatV(const char *format, va_list vargs);
PyAPI_FUNC(PyObject *) PyString_FromFormat(const char *format, ...);

#ifdef __cplusplus
}
#endif
#endif
