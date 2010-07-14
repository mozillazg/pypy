
import py

from pypy.conftest import gettestobjspace

class TestSDArray(object):
    def test_unwrap(self, space):
        skip("Irrelevant interplevel test")
        w_int = space.wrap(1)
        w_float = space.wrap(1.0)

        from pypy.interpreter.error import OperationError
        def interp_raises(exceptions, f, *args, **kwargs):
            try:
                f(*args, **kwargs)
            except OperationError, e:
                for ex in exceptions:
                    if e.match(space, ex):
                        return
                raise
            else:
                raise AssertionError("Expected one of %s to be raised" % str(exceptions))

        from pypy.module.micronumpy.dtype import unwrap_int
        assert 1 ==  unwrap_int(space, w_int)
        interp_raises((space.w_TypeError,), unwrap_int, space, w_float)

        from pypy.module.micronumpy.dtype import unwrap_float
        assert 1.0 == unwrap_float(space, w_float)
        #interp_raises((space.w_TypeError,), unwrap_float, space, w_int) #er, shouldn't this raise?

    def test_coerce(self, space):
        skip("Irrelevant interplevel test")
        w_int = space.wrap(1)
        w_float = space.wrap(1.0)

        from pypy.module.micronumpy.dtype import coerce_int
        assert 1 == coerce_int(space, w_int)
        assert 1 == coerce_int(space, w_float)

        from pypy.module.micronumpy.dtype import coerce_float
        assert 1.0 == coerce_float(space, w_int)
        assert 1.0 == coerce_float(space, w_float)

class AppTestSDArray(object):
    def setup_class(cls):
        cls.space = gettestobjspace(usemodules=('micronumpy',))
        cls.w_compare = cls.space.appexec([],
        """():
           def compare(a, b):
               assert a.dtype == type(b[0])
               for x, y in zip(a, b):
                   if x != y: return False
               return True
           return compare""")
        cls.w_length = cls.space.appexec([], """(): return 16""")
        cls.w_value = cls.space.appexec([], """(): return 3.0""")

    def test_type_array(self):
        compare = self.compare
        from micronumpy import array
        for data_type in (int, float):
            data = [data_type(x) for x in xrange(4)] 
            ar = array(data)
            assert compare(ar, data)

    @py.test.mark.xfail
    def test_sdarray_operators(self):
        from micronumpy import array
        from operator import mul, div, add, sub
        compare = self.compare
        d = range(1, self.length)
        for data_type in (int, float):
            data = [data_type(x) for x in d]
            ar = array(data)
            data.reverse()
            ar2 = array(data)
            for operator in (mul, div, add, sub):
                for value in xrange(1, 8): #less overkill
                    assert compare(operator(ar2, value), [operator(x, value) for x in data])
                    assert compare(operator(value, ar2), [operator(value, x) for x in data])
                assert compare(operator(ar, ar2), [operator(x, y) for (x, y) in zip(ar, ar2)])

    @py.test.mark.xfail
    def test_operator_result_types(self):
        from operator import mul, div, add, sub
        from micronumpy import array
        types = {
                 (int, int): int,
                 (int, float): float,
                 (float, int): float,
                 (float, float): float
                }

        typecodes = {int: 'i',
                     float: 'd'}

        typestrings = {int: 'int32',
                       float: 'float64'}

        def test_type(dtype, expected_type):
            assert dtype == expected_type
            assert dtype == typecodes[expected_type]
            assert dtype == typestrings[expected_type]

        for operand_types, result_type in types.iteritems():
            for operator in (mul, div, add, sub):
                a_type, b_type = operand_types
                a = array(xrange(1, self.length + 1), dtype=a_type)
                b = array(xrange(1, self.length + 1), dtype=b_type)

                c = operator(a, b)
                test_type(c.dtype, result_type)

                d = operator(b, a)
                test_type(d.dtype, result_type)

                e = operator(a, b_type(self.value))
                test_type(e.dtype, result_type)

                f = operator(a_type(self.value), b)
                test_type(f.dtype, result_type)

    def test_iter(self):
        from micronumpy import array
        for iterable_type in (list, tuple):
            for data_type in (int, float):
                data = iterable_type([data_type(x) for x in xrange(self.length)])
                ar = array(data, dtype=data_type)
                ar_data = iterable_type([x for x in ar])
                assert ar_data == data

    def test_iterable_construction(self):
        compare = self.compare
        from micronumpy import array
        ar = array(xrange(4))

        assert compare(ar, xrange(4))

    def test_zeroes(self):
        from micronumpy import zeros
        for data_type in (int, float):
            ar = zeros(3, dtype=int)
            assert ar[0] == data_type(0.0)
    
    @py.test.mark.xfail
    def test_setitem_getitem(self):
        from micronumpy import zeros
        compare = self.compare

        ar = zeros(8, dtype=int)
        assert ar[0] == 0
        ar[1] = 3
        assert ar[1] == 3
        raises((IndexError, ValueError), ar.__getitem__, 'xyz') #FIXME: why TypeError?
        raises(IndexError, ar.__getitem__, 38)
        assert ar[-2] == 0
        assert ar[-7] == 3
        assert len(ar) == 8

        #setitem
        ar[2:3] = [5]
        assert ar[2] == 5
        assert compare(ar[1:3], [3, 5])
        assert compare(ar[-6:-4], [5, 0])
        assert compare(ar[-6:-8:-1], [5, 3])

        ar[3] = 2
        assert ar[3] == 2
        ar[5] = 3.5
        assert ar[5] == 3
        raises(ValueError, ar.__setitem__, 0, [99])
        raises(ValueError, ar.__setitem__, 0, 'f')
        raises(ValueError, ar.__setitem__, slice(2, 3), [4, 5, 6])

    @py.test.mark.xfail
    def test_minimum(self):
        from micronumpy import zeros, minimum
        ar = zeros(5, dtype=int)
        ar2 = zeros(5, dtype=int)
        ar[0] = 3
        ar[1] = -3
        ar[2] = 8
        ar2[3] = -1
        ar2[4] = 8
        x = minimum(ar, ar2)
        assert x[0] == 0
        assert x[1] == -3
        assert x[2] == 0
        assert x[3] == -1
        assert x[4] == 0
        assert len(x) == 5
        raises(ValueError, minimum, ar, zeros(3, dtype=int))

    @py.test.mark.xfail
    def test_str(self):
        from micronumpy import zeros, array

        z = zeros(shape=(3,))
        assert str(z) == '[ 0.  0.  0.]'

        ar = array([1.0, 2.0, 3.0])
        assert str(ar) == '[ 1.  2.  3.]'

        ar = array([1.5, 2.5, 3.5])
        assert str(ar) == '[ 1.5  2.5  3.5]'

        ar = array([1, 2, 3], dtype=int)
        assert str(ar) == '[1 2 3]'

class AppTestMultiDim(object):
    def setup_class(cls):
        cls.space = gettestobjspace(usemodules=('micronumpy',))
        cls.w_gen_array = cls.space.appexec([],
        """():
           def gen_array(shape, data_type=int, start=0):
               if len(shape) == 1:
                   return [data_type(x) for x in xrange(start, start+shape[0])]
               else:
                   stride = 1
                   for dim in shape[1:]:
                       stride *= dim
                   result = []
                   for i in xrange(shape[0]):
                       result.append(gen_array(shape[1:], data_type, start + i*stride))
                   return result
           return gen_array
           """)
        cls.w_compare = cls.space.appexec([],
        """():
           def compare(a, b):
               assert a.dtype == type(b[0])
               for x, y in zip(a, b):
                   if x != y: return False
               return True
           return compare""")

    def test_multidim(self):
        from micronumpy import zeros
        ar = zeros((3, 3), dtype=int)
        assert ar[0, 2] == 0
        raises(IndexError, ar.__getitem__, (3, 0))
        assert ar[-2, 1] == 0

    @py.test.mark.xfail
    def test_construction(self):
        from micronumpy import array
        gen_array = self.gen_array

        #3x3
        ar = array(gen_array((3,3)))
        assert len(ar) == 3

        #2x3
        ar = array(gen_array((2,3)))
        assert len(ar) == 2
        assert ar.shape == (2, 3)

        #3x2
        ar = array(gen_array((3,2))) # XXX: here's the problem
        assert len(ar) == 3
        assert ar.shape == (3, 2)

        raises(ValueError, array, [[2, 3, 4], [5, 6]])
        raises(ValueError, array, [2, [3, 4]])

    def test_getset(self):
        from micronumpy import zeros
        ar = zeros((3, 3, 3), dtype=int)
        ar[1, 2, 1] = 3
        assert ar[1, 2, 1] == 3
        assert ar[-2, 2, 1] == 3
        assert ar[2, 2, 1] == 0
        assert ar[-2, 2, -2] == 3

    def test_len(self):
        from micronumpy import zeros
        assert len(zeros((3, 2, 1), dtype=int)) == 3

    def test_shape_detect(self):
        from micronumpy import array
        ar = array([range(i*3, i*3+3) for i in range(3)])
        assert len(ar) == 3
        assert ar.shape == (3, 3)
        for i in range(3):
            for j in range(3):
                assert ar[i, j] == i*3+j
    
    @py.test.mark.xfail
    def test_get_set_slices(self):
        from micronumpy import array
        gen_array = self.gen_array
        compare = self.compare

        #getitem
        ar = array(gen_array((3,3)))
        s1 = ar[0]
        assert s1[1]==1
        s2 = ar[1:3]
        assert s2[0][0] == 3
        assert compare(ar[1:3, 1:3][1], [7, 8])
        assert compare(ar[0], ar[...][0])
        assert ar[1][2] != ar[..., 1:3][1]
        assert not compare(ar[...][0], ar[..., 0])
        assert compare(ar[1:3, 0::2][1], [6, 8])
        #raises(ValueError, ar.__getitem__, 'what a strange index') #still unfixed
        raises(IndexError, ar.__getitem__, (2, 2, 2)) #too many
        raises(IndexError, ar.__getitem__, 5)
        raises(IndexError, ar.__getitem__, (0, 6))

        assert 0 in ar[2:2].shape
        assert compare(ar[-1], ar[2])
        assert compare(ar[2:3][0], ar[2])
        assert compare(ar[1, 0::2], [3, 5])
        assert compare(ar[0::2, 0], [0, 6])

        #setitem
        ar[2] = 3
        assert ar[2, 0] == ar[2, 1] == ar[2, 2] == 3
        ar[2:3] = [7]
        ar[2:3] = [5, 6, 7]
        ar[2] = [0, 1, 2]
        assert compare(ar[0], ar[2])
        assert compare(ar[..., 0], [0, 3, 0])
        raises(ValueError, ar.__setitem__, slice(1, 3), [1, 2, 3, 4]) #too much elems
        raises(ValueError, ar.__setitem__, slice(0, 3),
                [[[1], [2], [3]], [[4], [5], [6]], [[7], [8], [9]]]) #too large shape
        raises(ValueError, ar.__setitem__, slice(3, 4), [5, 6]) #attempting to check

        ar2 = array(gen_array((3, 3))) 
        ar2[...] = [0, 1, 2] #long slice
        #check preference
        assert ar2[0, 0] == ar2[1, 0] == 0
        assert ar2[1, 2] == 2

        ar3 = array(gen_array((3, 3, 3)))
        ar3[1:3] = [[0, 1, 2], [3, 4, 5]]
        assert compare(ar3[1, 2], [2, 2, 2])

    @py.test.mark.xfail
    def test_newaxis(self):
        from micronumpy import array
        gen_array = self.gen_array
        compare = self.compare

        ar = array(gen_array((3, 3)))

        assert compare(ar[[1, 2], 0], ar[1:3, 0])
        assert compare(ar[ [[1, 2], [0, 1]] ] [1, 0], ar[0]) # zip iterables into coordinates

    @py.test.mark.xfail
    def test_mdarray_operators(self):
        from micronumpy import array
        import operator
        compare = self.compare

        data1 = [[i*3+j+1 for j in range(3)] for i in range(3)]
        data2 = [[i*3+j for j in range(3, 0, -1)] for i in range(3, 0, -1)]

        ar1 = array(data1)
        ar2 = array(data2)

        const = 13

        for f in (operator.add,
                  operator.sub,
                  operator.mul,
                  operator.div):
            res = f(ar1, ar2)
            for i in range(3):
                assert compare(res[i],
                        [f(a, b) for a, b in zip(data1[i], data2[i])])
            rres = f(ar2, ar1)
            for i in range(3):
                assert compare(rres[i],
                        [f(b, a) for a, b in zip(data1[i], data2[i])])

            cres = f(ar1, const)
            for i in range(3):
                assert compare(cres[i],
                        [f(a, const) for a in data1[i]])

            crres = f(const, ar2)
            for i in range(3):
                assert compare(crres[i],
                        [f(const, b) for b in data2[i]])


class AppTestDType(object):
    def setup_class(cls):
        cls.space = gettestobjspace(usemodules=('micronumpy',))

    @py.test.mark.xfail
    def test_eq(self):
        from micronumpy import zeros

        a = zeros((4,), dtype=int)
        assert a.dtype == int
        assert a.dtype == 'i'
        assert a.dtype == 'int32'
        raises((TypeError,), a.dtype, 'in')
        raises((TypeError,), a.dtype.__eq__, 3)

        b = zeros((4,), dtype=float)
        assert b.dtype == float
        assert b.dtype == 'd'
        assert b.dtype == 'float64'
        raises((TypeError,), b.dtype, 'flo')
        raises((TypeError,), b.dtype.__eq__, 3)

class TestDType(object):
    def test_lookups(self, space):
        skip("Depends on interplevel stuff that doesn't exist really anymore.")
        from pypy.module.micronumpy.dtype import retrieve_dtype
        from pypy.module.micronumpy.dtype import get_dtype
        a = get_dtype(space, space.wrap('i'))
        b = get_dtype(space, space.wrap('d'))

        assert a == retrieve_dtype(space, 'i')
        assert b == retrieve_dtype(space, 'd')

    def test_result_types(self, space):
        skip("Depends on interplevel stuff that doesn't exist really anymore.")
        from pypy.module.micronumpy.dtype import get_dtype
        from pypy.module.micronumpy.dtype import result_mapping
        w_typecode_a = space.wrap('i')
        w_typecode_b = space.wrap('d')
        a = get_dtype(space, w_typecode_a)
        b = get_dtype(space, w_typecode_b)

        assert 'i' == result_mapping(space, (w_typecode_a, w_typecode_a))
        assert 'd' == result_mapping(space, (w_typecode_b, w_typecode_a))
        assert 'd' == result_mapping(space, (w_typecode_a, w_typecode_b))
        assert 'd' == result_mapping(space, (w_typecode_b, w_typecode_b))

    def test_iterable_type(self, space):
        from pypy.module.micronumpy.dtype import infer_from_iterable

        data = [(space.wrap([1, 2, 3, 4, 5]), 'i'),
                (space.wrap([1, 2, 3.0, 4, 5]), 'd'),
                (space.wrap([1, 2.0, 3.0, 4, 5]), 'd'),
                (space.wrap([1.0, 2, 3, 4, 5]), 'd'),
                (space.wrap([1, 2, 3, 4, 5.0]), 'd'),
                (space.wrap([1.0, 2, 3, 4, 5.0]), 'd')]

        for w_xs, typecode in data:
            assert typecode == infer_from_iterable(space, w_xs).typecode

class TestMicroArray(object):
    def test_strides(self, space):
        from pypy.module.micronumpy.microarray import stride_row, stride_column

        shape = (2, 3)
        assert stride_row(shape, 0) == 3
        assert stride_row(shape, 1) == 1

        assert stride_column(shape, 0) == 1
        assert stride_column(shape, 1) == 2

        # TODO: more, N-dimensional too

    def test_memory_layout(self, space):
        from pypy.module.micronumpy.microarray import MicroArray
        from pypy.module.micronumpy.microarray import array
        from pypy.module.micronumpy.dtype import w_int_descr

        data = [[1, 2, 3],
                [4, 5, 6]]

        w_data = space.wrap(data)
        column_major = [1, 4, 2, 5, 3, 6]
        row_major = [1, 2, 3, 4, 5, 6]

        assert len(column_major) == len(row_major)
        memlen = len(column_major)

        ar = array(space, w_data, w_dtype=w_int_descr, order='C') #C for C not column
        
        for i in range(memlen):
            array_element = space.unwrap(ar.getitem(space, i)) # ugly, but encapsulates everything
            assert array_element == row_major[i]

        ar = array(space, w_data, w_dtype=w_int_descr, order='F')
        for i in range(memlen):
            array_element = space.unwrap(ar.getitem(space, i)) # ugly, but encapsulates everything
            assert array_element == column_major[i]

