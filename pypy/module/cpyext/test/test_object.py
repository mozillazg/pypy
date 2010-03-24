from pypy.module.cpyext.test.test_cpyext import AppTestCpythonExtensionBase

import py
import sys

class AppTestObject(AppTestCpythonExtensionBase):
    def test_IsTrue(self):
        module = self.import_extension('foo', [
            ("test_IsTrue", "METH_VARARGS",
             """
                 PyObject* arg = PyTuple_GetItem(args, 0);
                 return PyBool_FromLong(PyObject_IsTrue(arg));
             """),
            ])
        assert module.test_IsTrue(True)
        assert module.test_IsTrue(1.0)
        assert not module.test_IsTrue(False)
        assert not module.test_IsTrue(0)

    def test_Not(self):
        module = self.import_extension('foo', [
            ("test_Not", "METH_VARARGS",
             """
                 PyObject* arg = PyTuple_GetItem(args, 0);
                 return PyBool_FromLong(PyObject_Not(arg));
             """),
            ])
        assert module.test_Not(False)
        assert module.test_Not(0)
        assert not module.test_Not(True)
        assert not module.test_Not(3.14)
