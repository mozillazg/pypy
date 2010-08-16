from pypy.conftest import gettestobjspace
from pypy.translator.tool.cbuild import ExternalCompilationInfo
from pypy.translator.platform import platform

import py

class AppTestJitffi(object):
    @staticmethod
    def preprare_c_example():
        from pypy.tool.udir import udir
        c_file = udir.ensure("test_ctypes", dir=True).join("xlib.c")
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
        int return_ptrvalue(int a, int *b)
        {
            return a+(*b);
        }
        int sum_intarray(int *a)
        {
            int i;
            int sum = 0;
            for(i=0; i<5; i++)
            {
                sum += *a+i;
            }
            return sum;
        }
        void a2b(char *txt)
        {
            int i;
            for(i=0; txt[i] != '\0'; i++)
            {
                if (txt[i] == 'a') txt[i] = 'b';
            }
        }
        int *return_intptr(int a)
        {
            int *x = malloc(sizeof(int));
            *x = a;
            return x;
        }
        '''
        ))

        symbols = ['add_integers', 'add_floats', 'add_intfloat',
                   'return_float', 'max3', 'fvoid', 'return_void',
                   'return_ptrvalue', 'sum_intarray', 'a2b', 'return_intptr']
        eci = ExternalCompilationInfo(export_symbols=symbols)

        return str(platform.compile([c_file], eci, 'x', standalone=False))

    def setup_class(cls):
        space = gettestobjspace(usemodules=('_ctypes',))
        cls.space = space
        cls.w_lib_name = space.wrap(cls.preprare_c_example())

    def test_missing_lib(self):
        from _ctypes import dlopen
        raises(OSError, dlopen, 'xxxfoo888baryyy')

    def test_get(self):
        from _ctypes import dlopen
        lib = dlopen(self.lib_name)

        func = lib.get('add_integers', ['i', 'i'], 'i')
        assert 3 == func.call([1,2])
        func = lib.get('add_integers', ['i', 'i'], 'i')
        assert 1 == func.call([-1,2])
        func = lib.get('add_integers', ['i', 'i'], 'i')
        assert 0 == func.call([0,0])

        func = lib.get('max3', ['i', 'i', 'i'], 'i')
        assert 8 == func.call([2, 8, 3])

        func = lib.get('add_floats', ['f', 'f'], 'f')
        assert 2.7 == func.call([1.2, 1.5])

    def test_get_void(self):
        from _ctypes import dlopen
        lib = dlopen(self.lib_name)

        func = lib.get('fvoid', [], 'i')
        assert 1 == func.call()

        func = lib.get('return_void', ['i', 'i'], 'v')
        assert func.call([1, 2]) is None
        func = lib.get('return_void', ['i', 'i'])
        assert func.call([1, 2]) is None

    def test_various_type_args(self):
        from _ctypes import dlopen
        lib = dlopen(self.lib_name)

        func = lib.get('add_intfloat', ['i', 'f'], 'i')
        assert func.call([1, 2.9]) == 3
        assert func.call([0, 1.3]) == 1

    def test_ptrargs(self):
        from _ctypes import dlopen, Test
        t = Test()
        lib = dlopen(self.lib_name)

        func = lib.get('return_ptrvalue', ['i', 'p'], 'i')
        intp = t.get_intp(1, [10])
        assert func.call([20, intp]) == 30

        func = lib.get('sum_intarray', ['p'], 'i')
        intp = t.get_intp(5, [ i for i in xrange(5) ])
        assert func.call([intp]) == 10

        func = lib.get('a2b', ['p'])
        charp = t.get_charp('xaxaxa')
        func.call([charp])
        assert t.get_str(charp) == 'xbxbxb'

    def test_get_ptr(self):
        from _ctypes import dlopen, Test
        t = Test()
        lib = dlopen(self.lib_name)

        func = lib.get('return_intptr', ['i'], 'p')
        addr = func.call([22])
        ret = t.get_int_from_addr(addr)
        assert ret == 22

    def test_undefined_func(self):
        from _ctypes import dlopen
        lib = dlopen(self.lib_name)
        # xxxfoo888baryyy - not existed function
        raises(ValueError, lib.get, 'xxxfoo888baryyy', [])
        raises(ValueError, lib.get, 'xxxfoo888baryyy', ['i'], 'i')

    def test_unknown_types(self):
        from _ctypes import dlopen
        lib = dlopen(self.lib_name)
        # xxxfoo888baryyy - not defined types (args_type, res_type etc.)
        raises(ValueError, lib.get, 'fvoid', ['xxxfoo888baryyy'])
        raises(ValueError, lib.get, 'fvoid', ['i','xxxfoo888baryyy'])
        raises(ValueError, lib.get, 'fvoid', ['xxxfoo888baryyy'],'i')
        raises(ValueError, lib.get, 'fvoid', [], 'xxxfoo888baryyy')
