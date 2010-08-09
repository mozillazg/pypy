from pypy.rlib import rjitffi
from pypy.translator.tool.cbuild import ExternalCompilationInfo
from pypy.translator.platform import platform
from pypy.rpython.lltypesystem import rffi, lltype
from pypy.rpython.test.test_llinterp import interpret
from pypy.jit.backend.llsupport import descr

import py

class TestJitffi(object):
    @staticmethod
    def preprare_c_example():
        from pypy.tool.udir import udir
        c_file = udir.ensure("test_rjitffi", dir=True).join("xlib1.c")
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
        '''
        ))

        symbols = ['add_integers', 'add_floats', 'add_intfloat',
                   'return_float', 'max3', 'fvoid', 'return_void',
                   'return_ptrvalue', 'sum_intarray', 'a2b']
        eci = ExternalCompilationInfo(export_symbols=symbols)

        return str(platform.compile([c_file], eci, 'x1', standalone=False))

    def setup_class(cls):
        cls.lib_name = cls.preprare_c_example()

    def push_result(self, value): # mock function
        return value

    def fromcache(self, f, args_type, res_type):
        if not hasattr(self, 'cache'):
            self.cache = {}

        arg_classes = ''.join(args_type)
        key = (res_type, arg_classes)
        try:
            f.looptoken = self.cache[key]
        except KeyError:
            f.gen_looptaken()
            self.cache[key] = f.looptoken

    def test_missing_lib(self):
        py.test.raises(OSError, rjitffi.CDLL, 'xxxfoo888baryyy')

    def test_get(self):
        lib = rjitffi.CDLL(self.lib_name)

        args_type = ['i', 'i']
        res_type = 'i'

        func = lib.get('add_integers', args_type, res_type, self.push_result, cache=True)
        self.fromcache(func, args_type, res_type)
        func.push_int(1)
        func.push_int(2)
        assert func.call() == 3

        func = lib.get('add_integers', args_type, res_type, self.push_result, cache=True)
        self.fromcache(func, args_type, res_type)
        func.push_int(-1)
        func.push_int(2)
        assert func.call() == 1

        func = lib.get('add_integers', args_type, res_type, self.push_result, cache=True)
        self.fromcache(func, args_type, res_type)
        func.push_int(0)
        func.push_int(0)
        assert func.call() == 0

        args_type = ['i', 'i', 'i']
        res_type = 'i'

        func = lib.get('add_integers', args_type, res_type, self.push_result, cache=True)
        self.fromcache(func, args_type, res_type)
        func = lib.get('max3', ['i', 'i', 'i'], 'i', self.push_result)
        func.push_int(2)
        func.push_int(8)
        func.push_int(3)
        assert func.call() == 8

        args_type = ['f', 'f']
        res_type = 'f'

        func = lib.get('add_floats', args_type, res_type, self.push_result, cache=True)
        self.fromcache(func, args_type, res_type)
        func.push_float(1.2)
        func.push_float(1.5)
        assert func.call() == 2.7

    def test_get_void(self):
        lib = rjitffi.CDLL(self.lib_name)

        args_type = []
        res_type = 'i'

        func = lib.get('fvoid', args_type, res_type, self.push_result, cache=True)
        self.fromcache(func, args_type, res_type)
        assert func.call() == 1

        args_type = ['i', 'i']
        res_type = 'v'

        func = lib.get('return_void', args_type, res_type, self.push_result, cache=True)
        self.fromcache(func, args_type, res_type)
        func.push_int(1)
        func.push_int(2)
        assert func.call() is None

        func = lib.get('return_void', args_type, push_result=self.push_result, cache=True)
        self.fromcache(func, args_type, res_type)
        func.push_int(1)
        func.push_int(2)
        assert func.call() is None

    def test_various_type_args(self):
        lib = rjitffi.CDLL(self.lib_name)

        args_type = ['i', 'f']
        res_type = 'i'
        func = lib.get('add_intfloat', args_type, res_type, self.push_result, cache=True)
        self.fromcache(func, args_type, res_type)
        func.push_int(1)
        func.push_float(2.9)
        assert func.call() == 3
        
        # stack is cleaned up after calling
        func.push_int(0)
        func.push_float(1.3)
        assert func.call() == 1

    def test_ptrargs(self):
        lib = rjitffi.CDLL(self.lib_name)

        func = lib.get('return_ptrvalue', ['i', 'p'], 'i', self.push_result)
        func.push_int(20)
        try:
            intp = lltype.malloc(rffi.INTP.TO, 1, flavor='raw')
            intp[0] = 10
            func.push_ref(rffi.cast(lltype.Signed, intp))
            assert func.call() == 30
        finally:
            lltype.free(intp, flavor='raw')

        func = lib.get('sum_intarray', ['p'], 'i', self.push_result)
        intp = lltype.malloc(rffi.INTP.TO, 5, flavor='raw')
        try:
            for i in xrange(5):
                intp[i] = i
            func.push_ref(rffi.cast(lltype.Signed, intp))
            assert func.call() == 10
        finally:
            lltype.free(intp, flavor='raw')

        func = lib.get('a2b', ['p'], push_result=self.push_result)
        charp = rffi.str2charp('xaxaxa')
        try:
            func.push_ref(rffi.cast(lltype.Signed, charp))
            func.call()
            assert rffi.charp2str(charp) == 'xbxbxb'
        finally:
            rffi.free_charp(charp)

    def test_nocache(self):
        lib = rjitffi.CDLL(self.lib_name)

        func = lib.get('add_integers', ['i', 'i'], 'i', self.push_result)
        func.push_int(1)
        func.push_int(0)
        assert func.call() == 1

    def test_undefined_func(self):
        lib = rjitffi.CDLL(self.lib_name)
        # xxxfoo888baryyy - not existed function
        py.test.raises(ValueError, lib.get, 'xxxfoo888baryyy', [])
        py.test.raises(ValueError, lib.get, 'xxxfoo888baryyy', ['i'], 'i')

    def test_unknown_types(self):
        lib = rjitffi.CDLL(self.lib_name)
        # xxxfoo888baryyy - not defined types (args_type, res_type etc.)
        py.test.raises(ValueError, lib.get, 'fvoid', ['xxxfoo888baryyy'])
        py.test.raises(ValueError, lib.get, 'fvoid', ['i','xxxfoo888baryyy'])
        py.test.raises(ValueError, lib.get, 'fvoid', ['xxxfoo888baryyy'],'i')
        py.test.raises(ValueError, lib.get, 'fvoid', [], 'xxxfoo888baryyy')

class TestTranslation(object):
    @staticmethod
    def preprare_c_example():
        from pypy.tool.udir import udir
        c_file = udir.ensure("test_rjitffi", dir=True).join("xlib2.c")
        c_file.write(py.code.Source('''
        int add_int(int a, int b)
        {
           return a+b;
        }
        float add_float(float a, float b)
        {
           return a+b;
        }
        void ret_void(int a)
        {
        }     
        '''
        ))

        symbols = ['add_int', 'add_float', 'ret_void']
        eci = ExternalCompilationInfo(export_symbols=symbols)

        return str(platform.compile([c_file], eci, 'x2', standalone=False))

    def setup_class(cls):
        cls.lib_name = cls.preprare_c_example()

    def test_get_calldescr(self):
        lib = rjitffi.CDLL(self.lib_name)
        def ret_int():
            func = lib.get('add_int', ['i', 'i'], 'i')
            assert isinstance(func.get_calldescr(), descr.SignedCallDescr)
        interpret(ret_int, [])

        def ret_float():
            func = lib.get('add_float', ['f', 'f'], 'f')
            assert isinstance(func.get_calldescr(), descr.FloatCallDescr)
        interpret(ret_float, [])

        def ret_void():
            func = lib.get('ret_void', ['i'], 'v')
            assert isinstance(func.get_calldescr(), descr.VoidCallDescr)
        interpret(ret_void, [])
