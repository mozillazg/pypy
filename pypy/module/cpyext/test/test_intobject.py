
from pypy.module.cpyext.test.test_cpyext import AppTestCpythonExtensionBase

class AppTestIntObject(AppTestCpythonExtensionBase):
    def test_intobject(self):
        import sys
        module = self.import_extension('foo', [
            ("check_int", "METH_VARARGS",
             """
             PyObject* a = PyTuple_GetItem(args, 0);
             if (PyInt_Check(a)) {
                 Py_RETURN_TRUE;
             }
             Py_RETURN_FALSE;
             """),
            ("add_one", "METH_VARARGS",
             """
             PyObject *a = PyTuple_GetItem(args, 0);
             long x = PyInt_AsLong(a);
             if (x == -1) {
                if (PyErr_Occurred()) {
                   return NULL;
                }
             }
             PyObject *ret = PyInt_FromLong(x + 1);
             return ret;
             """
             )
            ])
        assert module.check_int(3)
        assert module.check_int(True)
        assert not module.check_int((1, 2, 3))
        for i in [3, -5, -1, -sys.maxint, sys.maxint - 1]:
            assert module.add_one(i) == i + 1
        assert type(module.add_one(3)) is int
        raises(TypeError, module.add_one, None)
