#include "Python.h"
#include "structmember.h"

typedef struct {
	PyObject_HEAD
    int	foo;		/* the context holder */
} fooobject;

static PyTypeObject footype;

static fooobject *
newfooobject(void)
{
	fooobject *foop;

	foop = PyObject_New(fooobject, &footype);
	if (foop == NULL)
		return NULL;

	foop->foo = 42;
	return foop;
}


/* foo methods */

static void
foo_dealloc(fooobject *foop)
{
	PyObject_Del(foop);
}


/* foo methods-as-attributes */

static PyObject *
foo_copy(fooobject *self)
{
	fooobject *foop;

	if ((foop = newfooobject()) == NULL)
		return NULL;

	foop->foo = self->foo;

	return (PyObject *)foop;
}


static PyMethodDef foo_methods[] = {
	{"copy",      (PyCFunction)foo_copy,      METH_NOARGS,  NULL},
	{NULL, NULL}			     /* sentinel */
};

static PyObject *
foo_get_name(PyObject *self, void *closure)
{
    return PyString_FromStringAndSize("Foo Example", 11);
}

static PyObject *
foo_get_foo(PyObject *self, void *closure)
{
  return PyInt_FromLong(((fooobject*)self)->foo);
}

static PyGetSetDef foo_getseters[] = {
    {"name",
     (getter)foo_get_name, NULL,
     NULL,
     NULL},
     {"foo",
     (getter)foo_get_foo, NULL,
     NULL,
     NULL},
    {NULL}  /* Sentinel */
};

static PyObject *
foo_repr(PyObject *self)
{
    PyObject *format;

    format = PyString_FromString("<Foo>");
    if (format == NULL) return NULL;
    return format;
}

static PyObject *
foo_call(PyObject *self, PyObject *args, PyObject *kwds)
{
    Py_INCREF(kwds);
    return kwds;
}

static PyMemberDef foo_members[] = {
    {"int_member", T_INT, offsetof(fooobject, foo), 0,
     "A helpful docstring."},
    {"int_member_readonly", T_INT, offsetof(fooobject, foo), READONLY,
     "A helpful docstring."},
    {"broken_member", 0xaffe, 0, 0, ""},
    {NULL}  /* Sentinel */
};

static PyTypeObject footype = {
	PyVarObject_HEAD_INIT(NULL, 0)
	"foo.foo",		  /*tp_name*/
	sizeof(fooobject),	  /*tp_size*/
	0,			  /*tp_itemsize*/
	/* methods */
	(destructor)foo_dealloc,  /*tp_dealloc*/
	0,			  /*tp_print*/
	0,                        /*tp_getattr*/
	0,			  /*tp_setattr*/
	0,			  /*tp_compare*/
	foo_repr,			  /*tp_repr*/
    0,			  /*tp_as_number*/
	0,                        /*tp_as_sequence*/
	0,			  /*tp_as_mapping*/
	0, 			  /*tp_hash*/
	foo_call,			  /*tp_call*/
	0,			  /*tp_str*/
	0,			  /*tp_getattro*/
	0,			  /*tp_setattro*/
	0,	                  /*tp_as_buffer*/
	Py_TPFLAGS_DEFAULT,	  /*tp_flags*/
	0,		  /*tp_doc*/
        0,                        /*tp_traverse*/
        0,			  /*tp_clear*/
        0,			  /*tp_richcompare*/
        0,			  /*tp_weaklistoffset*/
        0,			  /*tp_iter*/
        0,			  /*tp_iternext*/
        foo_methods,	          /*tp_methods*/
        foo_members,              /*tp_members*/
        foo_getseters,            /*tp_getset*/
};


/* foo functions */

static PyObject *
foo_new(PyObject *self, PyObject *args)
{
	fooobject *foop;

	if ((foop = newfooobject()) == NULL) {
		return NULL;
	}
	
	return (PyObject *)foop;
}


/* List of functions exported by this module */

static PyMethodDef foo_functions[] = {
	{"new",		(PyCFunction)foo_new, METH_NOARGS, NULL},
	{NULL,		NULL}	/* Sentinel */
};


/* Initialize this module. */

void initfoo(void)
{
	PyObject *m, *d;

    Py_TYPE(&footype) = &PyType_Type;
    if (PyType_Ready(&footype) < 0)
        return;
	m = Py_InitModule("foo", foo_functions);
	if (m == NULL)
	    return;
	d = PyModule_GetDict(m);
	if (d)
	    PyDict_SetItemString(d, "fooType", (PyObject *)&footype);
   	/* No need to check the error here, the caller will do that */
}
