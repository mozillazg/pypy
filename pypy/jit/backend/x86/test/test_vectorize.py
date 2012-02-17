
from pypy.rpython.lltypesystem import lltype, rffi
from pypy.jit.backend.x86.test.test_basic import Jit386Mixin
from pypy.rlib import jit, libffi, clibffi

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

    def test_vector_ops_libffi(self):
        TP = rffi.CArray(lltype.Float)
        elem_size = rffi.sizeof(lltype.Float)
        ftype = clibffi.cast_type_to_ffitype(lltype.Float)

        driver = jit.JitDriver(greens = [], reds = ['a', 'i', 'b', 'size'])

        def read_item(arr, item):
            return libffi.array_getitem(ftype, elem_size, arr, item, 0)

        def store_item(arr, item, v):
            libffi.array_setitem(ftype, elem_size, arr, item, 0, v)

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
                store_item(b, i, read_item(a, i) + read_item(a, i))
                i += 1
                store_item(b, i, read_item(a, i) + read_item(a, i))
                i += 1
            r = sum(b, size)
            lltype.free(a, flavor='raw')
            lltype.free(b, flavor='raw')
            return r

        res = f(20)
        assert self.meta_interp(f, [20]) == res
        
