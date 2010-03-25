
/* String object interface */

#ifndef Py_STRINGOBJECT_H
#define Py_STRINGOBJECT_H
#ifdef __cplusplus
extern "C" {
#endif

typedef struct {
    PyObject_VAR_HEAD
    char* buffer;
    Py_ssize_t size;
} PyStringObject;

#ifdef __cplusplus
}
#endif
#endif
