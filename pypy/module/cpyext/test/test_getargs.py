
from pypy.module.cpyext.test.test_api import BaseApiTest
from pypy.module.cpyext.test.test_cpyext import AppTestCpythonExtensionBase

class AppTestGetargs(AppTestCpythonExtensionBase):
    def test_pyarg_parse(self):
        mod = self.import_extension('foo', [
            ('oneargint', 'METH_VARARGS',
             '''
             int l;
             //if (!PyArg_Parse(args, "i", &l)) {
             //    return NULL;
             //}
             return PyInt_FromLong(l);
             '''
             )])
        assert mod.oneargint(1) == 1
