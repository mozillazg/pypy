
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
        self.check_simple_loop(float_vector_add=1, getarrayitem_vector_raw=2,
                               setarrayitem_vector_raw=1)

    def test_vector_ops_libffi(self):
        TP = lltype.Array(lltype.Float, hints={'nolength': True,
                                               'memory_position_alignment': 16})
        elem_size = rffi.sizeof(lltype.Float)
        ftype = clibffi.cast_type_to_ffitype(lltype.Float)

        driver = jit.JitDriver(greens = [], reds = ['a', 'i', 'b', 'size'])

        def read_item(arr, item):
            return libffi.array_getitem(ftype, 1, arr, item, 0)

        def store_item(arr, item, v):
            libffi.array_setitem(ftype, 1, arr, item, 0, v)

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
            while i < size * elem_size:
                driver.jit_merge_point(a=a, i=i, size=size, b=b)
                jit.assert_aligned(a, i)
                jit.assert_aligned(b, i)
                store_item(b, i, read_item(a, i) + read_item(a, i))
                i += elem_size
                store_item(b, i, read_item(a, i) + read_item(a, i))
                i += elem_size
            r = sum(b, size)
            lltype.free(a, flavor='raw')
            lltype.free(b, flavor='raw')
            return r

        res = f(20)
        res2 = self.meta_interp(f, [20])
        self.check_simple_loop(float_vector_add=1,
                               getinteriorfield_vector_raw=2,
                               setinteriorfield_vector_raw=1)
        assert res2 == res
        
