
/* Exception interface */

#ifndef Py_PYERRORS_H
#define Py_PYERRORS_H
#ifdef __cplusplus
extern "C" {
#endif

PyObject *PyErr_NewException(char *name, PyObject *base, PyObject *dict);

PyAPI_DATA(PyObject *) PyExc_Exception;

#ifdef __cplusplus
}
#endif
#endif /* !Py_PYERRORS_H */
