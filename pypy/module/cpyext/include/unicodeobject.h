#ifndef Py_UNICODEOBJECT_H
#define Py_UNICODEOBJECT_H

#ifdef __cplusplus
extern "C" {
#endif


typedef struct {
    PyObject_HEAD
    void *buffer;
    Py_ssize_t size;
} PyUnicodeObject;


//XXX
typedef unsigned int Py_UCS4; 
// pypy only supports only UCS4
#define PY_UNICODE_TYPE Py_UCS4
typedef PY_UNICODE_TYPE Py_UNICODE;

  
#ifdef __cplusplus
}
#endif
#endif /* !Py_UNICODEOBJECT_H */
