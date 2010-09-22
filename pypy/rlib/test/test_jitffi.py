import sys
from pypy.rpython.lltypesystem import rffi, lltype
from pypy.rlib.clibffi import CDLL, ffi_type_double
from pypy.rlib.jitffi import Func, FloatArg
from pypy.rlib.test.test_libffi import get_libc_name, get_libm_name

class TestJitffi(object):

    def get_libc(self):
        return CDLL(get_libc_name())
    
    def get_libm(self):
        return CDLL(get_libm_name(sys.platform))
    
    def test_call_argchain(self):
        libm = self.get_libm()
        pow_ptr = libm.getpointer('pow', [ffi_type_double, ffi_type_double],
                              ffi_type_double)
        pow = Func(pow_ptr)
        argchain = FloatArg(2.0)
        argchain.next = FloatArg(3.0)
        res = pow.call(argchain, rffi.DOUBLE)
        assert res == 8.0
