from pypy.module.cpyext.test.test_api import BaseApiTest
from pypy.module.cpyext.test.test_cpyext import AppTestCpythonExtensionBase

class AppTestGetargs(AppTestCpythonExtensionBase):
    def test_METH_O(self):
        mod = self.import_extension('foo', [
            ('getarg', 'METH_O',
             '''
             Py_INCREF(args);
             return args;
             '''
             ),
            ])
        assert mod.getarg(1) == 1
        raises(TypeError, mod.getarg)
        raises(TypeError, mod.getarg, 1, 1)
