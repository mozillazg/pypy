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

    def test_wrong_args(self):
        # so far the test passes but for the wrong reason :-), i.e. because
        # .arg() only supports integers and floats
        chain = ArgChain()
        x = lltype.malloc(lltype.GcStruct('xxx'))
        y = lltype.malloc(lltype.GcArray(rffi.LONG), 3)
        z = lltype.malloc(lltype.Array(rffi.LONG), 4, flavor='raw')
        py.test.raises(TypeError, "chain.arg(x)")
        py.test.raises(TypeError, "chain.arg(y)")
        py.test.raises(TypeError, "chain.arg(z)")
        lltype.free(z, flavor='raw')

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
        # automatically collect the C source from the docstrings of the tests
        snippets = []
        for name in dir(cls):
            if name.startswith('test_'):
                meth = getattr(cls, name)
                # the heuristic to determine it it's really C code could be
                # improved: so far we just check that there is a '{' :-)
                if meth.__doc__ is not None and '{' in meth.__doc__:
                    snippets.append(meth.__doc__)
        #
        c_file.write(py.code.Source('\n'.join(snippets)))
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
        """
            int sum_xy(int x, double y)
            {
                return (x + (int)y);
            }
        """
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
        """
            unsigned char cast_to_uchar_and_ovf(int x)
            {
                return 200+(unsigned char)x;
            }
        """
        libfoo = self.get_libfoo()
        func = (libfoo, 'cast_to_uchar_and_ovf', [types.sint], types.uchar)
        res = self.call(func, [0], rffi.UCHAR)
        assert res == 200
        self.check_loops(call=1)

    def test_cast_argument(self):
        """
            int many_args(char a, int b)
            {
                return a+b;
            }
        """
        libfoo = self.get_libfoo()
        func = (libfoo, 'many_args', [types.uchar, types.sint], types.sint)
        res = self.call(func, [chr(20), 22], rffi.LONG)
        assert res == 42

    def test_call_time(self):
        import time
        libc = self.get_libc()
        # XXX assume time_t is long
        # XXX: on msvcr80 the name of the function is _time32, fix it in that case
        func = (libc, 'time', [types.pointer], types.ulong)
        LONGP = rffi.CArray(rffi.LONG)
        null = lltype.nullptr(LONGP)
        t0 = self.call(func, [null], rffi.LONG)
        time.sleep(1)
        t1 = self.call(func, [null], rffi.LONG)
        assert t1 > t0
        #
        ptr_result = lltype.malloc(LONGP, 1, flavor='raw')
        t2 = self.call(func, [ptr_result], rffi.LONG)
        assert ptr_result[0] == t2
        lltype.free(ptr_result, flavor='raw')
        if self.__class__ is TestLibffiCall:
            # the test does not make sense when run with the JIT through
            # meta_interp, because the __del__ are not properly called (hence
            # we "leak" memory)
            del libc
            assert not ALLOCATED
