from pypy.conftest import gettestobjspace
from pypy.translator.tool.cbuild import ExternalCompilationInfo
from pypy.translator.platform import platform

import py

class AppTestJitffi(object):
    @staticmethod
    def preprare_c_example():
        from pypy.tool.udir import udir
        c_file = udir.ensure("test_jitffi", dir=True).join("xlib.c")
        c_file.write(py.code.Source('''
        int add_integers(int a, int b)
        {
           return a+b;
        }

        float return_float(int a, int b)
        {
           return a+b;
        }

        int max3(int a, int b, int c)
        {
           int max = a;
           if (b > max) max = b;
           if (c > max) max = c;
           return max;
        }
        '''
        ))

        symbols = ["add_integers"]
        eci = ExternalCompilationInfo(export_symbols=symbols)

        return str(platform.compile([c_file], eci, 'x', standalone=False))

    def setup_class(cls):
        space = gettestobjspace(usemodules=('jitffi',))
        cls.space = space
        cls.w_lib_name = space.wrap(cls.preprare_c_example())

    def test_call(self):
        import jitffi
        lib = jitffi.CDLL(self.lib_name)

        res = lib.call('add_integers', [1, 2], 'int')
        assert 3 == res
        assert isinstance(res, int)
        res = lib.call('add_integers', [-1, 2], 'int')
        assert 1 == res
        res = lib.call('add_integers', [0, 0], 'int')
        assert 0 == res

        res = lib.call('max3', [2, 8, 3], 'int')
        assert 8 == res

        res = lib.call('return_float', [1, 2], 'float')
        assert 3.0 == res
        assert isinstance(res, float)
        #res = lib.call('return_float', [1.5, 1.2], 'float')
        #assert 2.7 == res
