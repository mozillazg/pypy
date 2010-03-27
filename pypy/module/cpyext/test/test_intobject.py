
from pypy.module.cpyext.test.test_cpyext import AppTestCpythonExtensionBase

class AppTestIntObject(AppTestCpythonExtensionBase):
    def test_intobject(self):
        module = self.import_extension('foo', [
            ("check_int", "METH_VARARGS",
             """
             PyObject* a = PyTuple_GetItem(args, 0);
             if (PyInt_Check(a)) {
                 Py_RETURN_TRUE;
             }
             Py_RETURN_FALSE;
             """)])
        assert module.check_int(3)
        assert module.check_int(True)
        assert not module.check_int((1, 2, 3))
