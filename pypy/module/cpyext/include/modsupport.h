
/* Module support interface */

#ifndef Py_MODSUPPORT_H
#define Py_MODSUPPORT_H
#ifdef __cplusplus
extern "C" {
#endif

#define PYTHON_API_VERSION 1013
#define PYTHON_API_STRING "1013"

#define Py_InitModule(name, methods) \
	Py_InitModule4(name, methods, (char *)NULL, (PyObject *)NULL, \
		       PYTHON_API_VERSION)

#define Py_InitModule3(name, methods, doc) \
	Py_InitModule4(name, methods, doc, (PyObject *)NULL, \
		       PYTHON_API_VERSION)



#ifdef __cplusplus
}
#endif
#endif /* !Py_MODSUPPORT_H */
