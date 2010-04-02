
/* String object interface */

#ifndef Py_STRINGOBJECT_H
#define Py_STRINGOBJECT_H
#ifdef __cplusplus
extern "C" {
#endif

#define PyString_AS_STRING(op) PyString_AsString(op)

typedef struct {
    PyObject_HEAD
    char* buffer;
    Py_ssize_t size;
} PyStringObject;

PyObject *
PyString_FromFormatV(const char *format, va_list vargs);

#ifdef __cplusplus
}
#endif
#endif
