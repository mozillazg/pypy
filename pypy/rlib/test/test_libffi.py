import py
import sys
from pypy.rpython.lltypesystem import rffi, lltype
from pypy.rpython.lltypesystem.ll2ctypes import ALLOCATED
from pypy.rlib.test.test_clibffi import BaseFfiTest, get_libm_name
from pypy.rlib.libffi import CDLL, Func, get_libc_name, ArgChain
from pypy.rlib.libffi import ffi_type_double, ffi_type_void


class TestLibffi(BaseFfiTest):
    """
    Test the new JIT-friendly interface to libffi
    """

    def get_libc(self):
        return CDLL(get_libc_name())
    
    def get_libm(self):
        return CDLL(get_libm_name(sys.platform))

    def test_argchain(self):
        chain = ArgChain()
        assert chain.numargs == 0
        chain2 = chain.int(42)
        assert chain2 is chain
        assert chain.numargs == 1
        intarg = chain.first
        assert chain.last is intarg
        assert intarg.intval == 42
        chain.float(123.45)
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
        ptr = lib.getpointer('fopen', [], ffi_type_void)
        py.test.raises(KeyError, lib.getpointer, 'xxxxxxxxxxxxxxx', [], ffi_type_void)
        del ptr
        del lib
        assert not ALLOCATED

    def test_call_argchain(self):
        libm = self.get_libm()
        pow = libm.getpointer('pow', [ffi_type_double, ffi_type_double],
                              ffi_type_double)
        argchain = ArgChain()
        argchain.float(2.0).float(3.0)
        res = pow.call(argchain, rffi.DOUBLE)
        assert res == 8.0
