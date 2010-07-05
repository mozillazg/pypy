from pypy.rlib import rjitffi
from pypy.translator.tool.cbuild import ExternalCompilationInfo
from pypy.translator.platform import platform
from pypy.rpython.lltypesystem import rffi, lltype

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

        int add_intfloat(int a, double b)
        {
           int rb = (int)b;
           return a+rb;
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

        symbols = ['add_integers', 'add_floats', 'add_intfloat',
                   'return_float', 'max3', 'fvoid', 'return_void']
        eci = ExternalCompilationInfo(export_symbols=symbols)

        return str(platform.compile([c_file], eci, 'x', standalone=False))

    def setup_class(cls):
        cls.lib_name = cls.preprare_c_example()

    def test_missing_lib(self):
        py.test.raises(OSError, rjitffi.CDLL, 'xxxfoo888baryyy')

    def test_get(self):
        lib = rjitffi.CDLL(self.lib_name)

        func = lib.get('add_integers', ['int', 'int'], 'int')
        func.push_int(1)
        func.push_int(2)
        assert func.call() == 3

        func = lib.get('add_integers', ['int', 'int'], 'int')
        func.push_int(-1)
        func.push_int(2)
        assert func.call() == 1

        func = lib.get('add_integers', ['int', 'int'], 'int')
        func.push_int(0)
        func.push_int(0)
        assert func.call() == 0

        func = lib.get('max3', ['int', 'int', 'int'], 'int')
        func.push_int(2)
        func.push_int(8)
        func.push_int(3)
        assert func.call() == 8

        func = lib.get('add_floats', ['float', 'float'], 'float')
        func.push_float(1.2)
        func.push_float(1.5)
        assert func.call() == 2.7

    def test_get_void(self):
        lib = rjitffi.CDLL(self.lib_name)

        func = lib.get('fvoid', [], 'int')
        assert func.call() == 1

        func = lib.get('return_void', ['int', 'int'], 'void')
        func.push_int(1)
        func.push_int(2)
        assert func.call() is None

        func = lib.get('return_void', ['int', 'int'])
        func.push_int(1)
        func.push_int(2)
        assert func.call() is None

    def test_various_type_args(self):
        lib = rjitffi.CDLL(self.lib_name)

        func = lib.get('add_intfloat', ['int', 'float'], 'int')
        func.push_int(1)
        func.push_float(2.9)
        assert func.call() == 3
        
        # stack is cleaned up after calling
        func.push_int(0)
        func.push_float(1.3)
        assert func.call() == 1

    def test_undefined_func(self):
        lib = rjitffi.CDLL(self.lib_name)
        # xxxfoo888baryyy - not existed function
        py.test.raises(ValueError, lib.get, 'xxxfoo888baryyy', [])
        py.test.raises(ValueError, lib.get, 'xxxfoo888baryyy', ['int'], 'int')

    def test_unknown_types(self):
        lib = rjitffi.CDLL(self.lib_name)
        # xxxfoo888baryyy - not defined types (args_type, res_type etc.)
        py.test.raises(ValueError, lib.get, 'fvoid', ['xxxfoo888baryyy'])
        py.test.raises(ValueError, lib.get, 'fvoid', ['int','xxxfoo888baryyy'])
        py.test.raises(ValueError, lib.get, 'fvoid', ['xxxfoo888baryyy'],'int')
        py.test.raises(ValueError, lib.get, 'fvoid', [], 'xxxfoo888baryyy')
