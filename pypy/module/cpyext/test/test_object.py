from pypy.module.cpyext.test.test_cpyext import AppTestCpythonExtensionBase

import py
import sys


class AppTestObject(AppTestCpythonExtensionBase):
    def test_IsTrue(self):
        module = self.import_extension('foo', [
            ("is_true", "METH_VARARGS",
             """
                 PyObject* arg = PyTuple_GetItem(args, 0);
                 return PyBool_FromLong(PyObject_IsTrue(arg));
             """),
            ])
        assert module.is_true(True)
        assert module.is_true(1.0)
        assert not module.is_true(False)
        assert not module.is_true(0)

    def test_Not(self):
        module = self.import_extension('foo', [
            ("not_", "METH_VARARGS",
             """
                 PyObject* arg = PyTuple_GetItem(args, 0);
                 return PyBool_FromLong(PyObject_Not(arg));
             """),
            ])
        assert module.not_(False)
        assert module.not_(0)
        assert not module.not_(True)
        assert not module.not_(3.14)

    def test_HasAttr(self):
        module = self.import_extension('foo', [
            ("hasattr", "METH_VARARGS",
             """
                 PyObject* obj = PyTuple_GetItem(args, 0);
                 PyObject* name = PyTuple_GetItem(args, 1);
                 return PyBool_FromLong(PyObject_HasAttr(obj, name));
             """),
            ])
        assert module.hasattr('', '__len__')
        assert module.hasattr(int, '__eq__')
        assert not module.hasattr(int, 'nonexistingattr')

    def test_SetAttr(self):
        module = self.import_extension('foo', [
            ("setattr", "METH_VARARGS",
             """
                 PyObject* obj = PyTuple_GetItem(args, 0);
                 PyObject* name = PyTuple_GetItem(args, 1);
                 PyObject* value = PyTuple_GetItem(args, 2);
                 PyObject_SetAttr(obj, name, value);
                 Py_INCREF(Py_None);
                 return Py_None;
             """),
            ])
        class X:
            pass
        x = X()
        module.setattr(x, 'test', 5)
        assert hasattr(x, 'test')
        assert x.test == 5
        module.setattr(x, 'test', 10)
        assert x.test == 10
