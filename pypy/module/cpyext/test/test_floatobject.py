from pypy.module.cpyext.test.test_api import BaseApiTest
from pypy.module.cpyext.test.test_cpyext import AppTestCpythonExtensionBase

class TestFloatObject(BaseApiTest):
    def test_floatobject(self, space, api):
        assert space.unwrap(api.PyFloat_FromDouble(3.14)) == 3.14
        assert api.PyFloat_AsDouble(space.wrap(23.45)) == 23.45

        assert api.PyFloat_AsDouble(space.w_None) == -1
        api.PyErr_Clear()

class AppTestFloatObject(AppTestCpythonExtensionBase):
    def test_float(self):
        module = self.import_extension("foo", [
        ("test_float_coerce", "METH_NOARGS",
        """
            PyObject *p = PyNumber_Float(PyTuple_GetItem(args, 0));
            if (p != NULL) {
                return p;
            }
            Py_RETURN_NONE;
        """),
        ])
        
        assert type(module.test_float_coerce(3)) is float
        assert module.test_float_coerce([]) is None
        
        class Coerce(object):
            def __float__(self):
                return 42.5
        
        assert module.test_float_coerce(Coerce()) == 42.5
