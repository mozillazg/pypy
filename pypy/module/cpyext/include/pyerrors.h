
/* Exception interface */

#ifndef Py_PYERRORS_H
#define Py_PYERRORS_H
#ifdef __cplusplus
extern "C" {
#endif

PyAPI_DATA(PyObject *) PyExc_Exception;
void PyErr_SetString(PyObject *, char *);
PyObject * PyErr_Occurred(void);
void PyErr_Clear(PyObject *, char *);

#ifdef __cplusplus
}
#endif
#endif /* !Py_PYERRORS_H */
