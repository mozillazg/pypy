typedef struct {
    PyObject_HEAD
} PyUnicodeObject;
//XXX
typedef unsigned int Py_UCS4; 
// pypy only supports only UCS4
#define PY_UNICODE_TYPE Py_UCS4
typedef PY_UNICODE_TYPE Py_UNICODE;

