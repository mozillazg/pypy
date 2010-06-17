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

        int fvoid(void)
        {
           return 1;
        }

        void return_void(int a, int b)
        {
            int c;
            c = a + b;
        }
        '''
        ))

        symbols = ['add_integers', 'add_floats', 'return_float',
                   'max3', 'fvoid', 'return_void']
        eci = ExternalCompilationInfo(export_symbols=symbols)

        return str(platform.compile([c_file], eci, 'x', standalone=False))

    def setup_class(cls):
        space = gettestobjspace(usemodules=('jitffi',))
        cls.space = space
        cls.w_lib_name = space.wrap(cls.preprare_c_example())

    #def test_missing_lib(self):
    #    py.test.raises(OSError, rjitffi.CDLL, 'xxxfoo888baryyy')

    def test_get(self):
        import jitffi
        lib = jitffi.CDLL(self.lib_name)

        func = lib.get('add_integers', ['int', 'int'], 'int')
        assert 3 == func.call(1,2)
        func = lib.get('add_integers', ['int', 'int'], 'int')
        assert 1 == func.call(-1,2)
        func = lib.get('add_integers', ['int', 'int'], 'int')
        assert 0 == func.call(0,0)

        func = lib.get('max3', ['int', 'int', 'int'], 'int')
        assert 8 == func.call(2, 8, 3)

        func = lib.get('add_floats', ['float', 'float'], 'float')
        assert 2.7 == func.call(1.2, 1.5)

    def test_get_void(self):
        import jitffi
        lib = jitffi.CDLL(self.lib_name)

        func = lib.get('fvoid', [], 'int')
        assert 1 == func.call()

        func = lib.get('return_void', ['int', 'int'], 'void')
        assert func.call(1, 2) is None
        func = lib.get('return_void', ['int', 'int'])
        assert func.call(1, 2) is None

    def test_undefined_func(self):
        import jitffi
        lib = jitffi.CDLL(self.lib_name)
        # xxxfoo888baryyy - not existed function
        py.test.raises(ValueError, lib.get, 'xxxfoo888baryyy', [])
        py.test.raises(ValueError, lib.get, 'xxxfoo888baryyy', ['int'], 'int')
