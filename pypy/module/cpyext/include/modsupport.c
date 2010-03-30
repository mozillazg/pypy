#include <Python.h>
#if 0
unsupported functions in it
int
PyModule_AddObject(PyObject *m, const char *name, PyObject *o)
{
	PyObject *dict;
	if (!PyModule_Check(m)) {
		PyErr_SetString(PyExc_TypeError,
			    "PyModule_AddObject() needs module as first arg");
		return -1;
	}
	if (!o) {
		if (!PyErr_Occurred())
			PyErr_SetString(PyExc_TypeError,
					"PyModule_AddObject() needs non-NULL value");
		return -1;
	}

	dict = PyModule_GetDict(m);
	if (dict == NULL) {
		/* Internal error -- modules must have a dict! */
		PyErr_Format(PyExc_SystemError, "module '%s' has no __dict__",
			     PyModule_GetName(m));
		return -1;
	}
	if (PyDict_SetItemString(dict, name, o))
		return -1;
	Py_DECREF(o);
	return 0;
}
#endif
