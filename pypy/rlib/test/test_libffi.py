import py
import sys
from pypy.rpython.lltypesystem import rffi, lltype
from pypy.rpython.lltypesystem.ll2ctypes import ALLOCATED
from pypy.rlib.test.test_clibffi import BaseFfiTest, get_libm_name
from pypy.rlib.libffi import CDLL, Func, get_libc_name, ArgChain, types

class TestLibffiMisc(BaseFfiTest):

    CDLL = CDLL

    def test_argchain(self):
        chain = ArgChain()
        assert chain.numargs == 0
        chain2 = chain.arg(42)
        assert chain2 is chain
        assert chain.numargs == 1
        intarg = chain.first
        assert chain.last is intarg
        assert intarg.intval == 42
        chain.arg(123.45)
        assert chain.numargs == 2
        assert chain.first is intarg
        assert intarg.next is chain.last
        floatarg = intarg.next
        assert floatarg.floatval == 123.45

    def test_library_open(self):
        lib = self.get_libc()
        del lib
        assert not ALLOCATED

    def test_library_get_func(self):
        lib = self.get_libc()
        ptr = lib.getpointer('fopen', [], types.void)
        py.test.raises(KeyError, lib.getpointer, 'xxxxxxxxxxxxxxx', [], types.void)
        del ptr
        del lib
        assert not ALLOCATED


class TestLibffiCall(BaseFfiTest):
    """
    Test various kind of calls through libffi.

    The peculiarity of these tests is that they are run both directly (going
    really through libffi) and by jit/metainterp/test/test_fficall.py, which
    tests the call when JITted.

    If you need to test a behaviour than it's not affected by JITing (e.g.,
    typechecking), you should put your test in TestLibffiMisc.
    """

    CDLL = CDLL

    @classmethod
    def setup_class(cls):
        from pypy.tool.udir import udir
        from pypy.translator.tool.cbuild import ExternalCompilationInfo
        from pypy.translator.platform import platform

        BaseFfiTest.setup_class()
        # prepare C code as an example, so we can load it and call
        # it via rlib.libffi
        c_file = udir.ensure("test_libffi", dir=1).join("foolib.c")
        c_file.write(py.code.Source('''
        int sum_xy(int x, double y)
        {
            return (x + (int)y);
        }

        unsigned char cast_to_uchar_and_ovf(int x)
        {
            return 200+(unsigned char)x;
        }
        '''))
        eci = ExternalCompilationInfo(export_symbols=[])
        cls.libfoo_name = str(platform.compile([c_file], eci, 'x',
                                               standalone=False))

    def get_libfoo(self):
        return self.CDLL(self.libfoo_name)

    def call(self, funcspec, args, RESULT, init_result=0):
        """
        Call the specified function after constructing and ArgChain with the
        arguments in ``args``.

        The function is specified with ``funcspec``, which is a tuple of the
        form (lib, name, argtypes, restype).

        This method is overridden by metainterp/test/test_fficall.py in
        order to do the call in a loop and JIT it. The optional arguments are
        used only by that overridden method.
        
        """
        lib, name, argtypes, restype = funcspec
        func = lib.getpointer(name, argtypes, restype)
        chain = ArgChain()
        for arg in args:
            chain.arg(arg)
        return func.call(chain, RESULT)

    def check_loops(self, *args, **kwds):
        """
        Ignored here, but does something in the JIT tests
        """
        pass

    # ------------------------------------------------------------------------

    def test_simple(self):
        libfoo = self.get_libfoo() 
        func = (libfoo, 'sum_xy', [types.sint, types.double], types.sint)
        res = self.call(func, [38, 4.2], rffi.LONG)
        assert res == 42
        self.check_loops({
                'call': 1,
                'guard_no_exception': 1,
                'int_add': 1,
                'int_lt': 1,
                'guard_true': 1,
                'jump': 1})

    def test_float_result(self):
        libm = self.get_libm()
        func = (libm, 'pow', [types.double, types.double], types.double)
        res = self.call(func, [2.0, 3.0], rffi.DOUBLE, init_result=0.0)
        assert res == 8.0
        self.check_loops(call=1)

    def test_cast_result(self):
        libfoo = self.get_libfoo()
        func = (libfoo, 'cast_to_uchar_and_ovf', [types.sint], types.uchar)
        res = self.call(func, [0], rffi.UCHAR)
        assert res == 200
        self.check_loops(call=1)
