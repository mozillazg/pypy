from pypy.rlib import jitffi
from pypy.translator.tool.cbuild import ExternalCompilationInfo
from pypy.translator.platform import platform

import py

class TestJitffi(object):
    @staticmethod
    def preprare_c_example():
        from pypy.tool.udir import udir
        c_file = udir.ensure("test_jitffi", dir=True).join("xlib.c")
        c_file.write(py.code.Source('''
        int add_integers(int a, int b)
        {
           return a+b;
        }

        double add_floats(double a, double b)
        {
           return a+b;
        }

        double return_float(int a, int b)
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

        symbols = ['add_integers', 'add_floats', 'return_float', 'max3']
        eci = ExternalCompilationInfo(export_symbols=symbols)

        return str(platform.compile([c_file], eci, 'x', standalone=False))

    def setup_class(cls):
        cls.lib_name = cls.preprare_c_example()

    def test_call(self):
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

    def test_get_with_same_type(self):
        lib = jitffi.CDLL(self.lib_name)

        func = lib.get('add_integers', ['int', 'int'], 'int')
        assert 3 == func(1,2)
        func = lib.get('add_integers', ['int', 'int'], 'int')
        assert 1 == func(-1,2)
        func = lib.get('add_integers', ['int', 'int'], 'int')
        assert 0 == func(0,0)

        func = lib.get('max3', ['int', 'int', 'int'], 'int')
        assert 8 == func(2, 8, 3)

        func = lib.get('add_floats', ['float', 'float'], 'float')
        assert 2.7 == func(1.2, 1.5)

    def test_get_void(self):
        lib = jitffi.CDLL(self.lib_name)
        py.test.raises(ValueError, lib.get,
                       'add_integers', ['void', 'int'], 'int')
