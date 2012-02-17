
from pypy.rpython.lltypesystem import lltype, rffi
from pypy.jit.backend.x86.test.test_basic import Jit386Mixin
from pypy.rlib import jit

class TestVectorize(Jit386Mixin):
    def test_vectorize(self):
        TP = rffi.CArray(lltype.Float)

        driver = jit.JitDriver(greens = [], reds = ['a', 'i', 'b', 'size'])

        def initialize(arr, size):
            for i in range(size):
                arr[i] = float(i)

        def sum(arr, size):
            s = 0
            for i in range(size):
                s += arr[i]
            return s

        def f(size):
            a = lltype.malloc(TP, size, flavor='raw')
            b = lltype.malloc(TP, size, flavor='raw')
            initialize(a, size)
            initialize(b, size)
            i = 0
            while i < size:
                driver.jit_merge_point(a=a, i=i, size=size, b=b)
                jit.assert_aligned(a, i)
                jit.assert_aligned(b, i)
                b[i] = a[i] + a[i]
                i += 1
                b[i] = a[i] + a[i]
                i += 1
            r = sum(b, size)
            lltype.free(a, flavor='raw')
            lltype.free(b, flavor='raw')
            return r

        assert self.meta_interp(f, [20]) == f(20)
