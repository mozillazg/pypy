from pypy.module.cpyext.test.test_cpyext import AppTestCpythonExtensionBase
from pypy.rpython.lltypesystem import rffi

class AppTestSysModule(AppTestCpythonExtensionBase):
    def test_sysmodule(self):
        module = self.import_extension('foo', [
            ("get", "METH_VARARGS",
             """
                 char *name = PyString_AsString(PyTuple_GetItem(args, 0));
                 PyObject *retval = PySys_GetObject(name);
                 return PyBool_FromLong(retval != NULL);
             """)])
        assert module.get("excepthook")
        assert not module.get("spam_spam_spam")

