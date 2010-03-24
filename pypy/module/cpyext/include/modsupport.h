
/* Module support interface */

#ifndef Py_MODSUPPORT_H
#define Py_MODSUPPORT_H
#ifdef __cplusplus
extern "C" {
#endif

#define PYTHON_API_VERSION 1013
#define PYTHON_API_STRING "1013"

PyObject *Py_InitModule4(const char* name, PyMethodDef* methods,
                         const char *doc, PyObject *self,
                         int apiver);

#define Py_InitModule(name, methods) \
	Py_InitModule4(name, methods, (char *)NULL, (PyObject *)NULL, \
		       PYTHON_API_VERSION)

#define Py_InitModule3(name, methods, doc) \
	Py_InitModule4(name, methods, doc, (PyObject *)NULL, \
		       PYTHON_API_VERSION)

PyObject * PyModule_GetDict(PyObject *);


#ifdef __cplusplus
}
#endif
#endif /* !Py_MODSUPPORT_H */
