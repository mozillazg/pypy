
from pypy.conftest import gettestobjspace

class AppTestSDArray(object):
    def setup_class(cls):
        cls.space = gettestobjspace(usemodules=('micronumpy',))
        cls.w_compare = cls.space.appexec([],
        """():
           def compare(a, b):
               for x, y in zip(a, b):
                   if x != y: return False
                   assert type(x) == type(y)
               return True
           return compare""")
        cls.w_length = cls.space.appexec([], """(): return 16""")
        cls.w_value = cls.space.appexec([], """(): return 3.0""")

    def test_type_array(self):
        compare = self.compare
        from numpy import array
        for data_type in (int, float):
            data = [data_type(x) for x in xrange(4)] 
            ar = array(data)
            assert compare(ar, data)

    def test_sdarray_operators(self):
        from numpy import array
        from operator import mul, div, add, sub
        compare = self.compare
        d = range(1, self.length)
        #skip('overkill...')
        for data_type in (int, float):
            data = [data_type(x) for x in d]
            ar = array(data)
            data.reverse()
            ar2 = array(data)
            for operator in (mul, div, add, sub):
                for value in xrange(1, 16):
                    assert compare(operator(ar2, value), [operator(x, value) for x in data])
                assert compare(operator(ar, ar2), [operator(x, y) for (x, y) in zip(ar, ar2)])

    def test_operator_result_types(self):
        from operator import mul, div, add, sub
        from numpy import array
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
        from numpy import array
        for iterable_type in (list, tuple):
            for data_type in (int, float):
                data = iterable_type([data_type(x) for x in xrange(self.length)])
                ar = array(data, dtype=data_type)
                ar_data = iterable_type([x for x in ar])
                assert ar_data == data

    def test_iterable_construction(self):
        compare = self.compare
        from numpy import array
        ar = array(xrange(4))

        assert compare(ar, xrange(4))

    def test_zeroes(self):
        from numpy import zeros
        for data_type in (int, float):
            ar = zeros(3, dtype=int)
            assert ar[0] == data_type(0.0)
    
    def test_setitem_getitem(self):
        from numpy import zeros
        ar = zeros(8, dtype=int)
        assert ar[0] == 0
        ar[1] = 3
        assert ar[1] == 3
        raises((TypeError, ValueError), ar.__getitem__, 'xyz')
        raises(IndexError, ar.__getitem__, 38)
        assert ar[-2] == 0
        assert ar[-7] == 3
        assert len(ar) == 8

        ar[2:3] = [5]
        assert ar[2] == 5
        compare = self.compare
        assert compare(ar[1:3], [3, 5])
        assert compare(ar[-6:-4], [5, 0])
        assert compare(ar[-6:-8:-1], [5, 3])


    def test_minimum(self):
        from numpy import zeros, minimum
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
               for x, y in zip(a, b):
                   if x != y: return False
                   assert type(x) == type(y)
               return True
           return compare""")
                                

    def test_multidim(self):
        from numpy import zeros
        ar = zeros((3, 3), dtype=int)
        assert ar[0, 2] == 0
        raises(IndexError, ar.__getitem__, (3, 0))
        assert ar[-2, 1] == 0

    def test_construction(self):
        from numpy import array
        gen_array = self.gen_array

        #3x3
        ar = array(gen_array((3,3)))
        assert len(ar) == 3

        #2x3
        ar = array(gen_array((2,3)))
        assert len(ar) == 2
        assert ar.shape == (2, 3)

        #3x2
        ar = array(gen_array((3,2)))
        assert len(ar) == 3
        assert ar.shape == (3, 2)

        raises(ValueError, array, [[2, 3, 4], [5, 6]])
        raises(ValueError, array, [2, [3, 4]])

    def test_getset(self):
        from numpy import zeros
        ar = zeros((3, 3, 3), dtype=int)
        ar[1, 2, 1] = 3
        assert ar[1, 2, 1] == 3
        assert ar[-2, 2, 1] == 3
        assert ar[2, 2, 1] == 0
        assert ar[-2, 2, -2] == 3

    def test_len(self):
        from numpy import zeros
        assert len(zeros((3, 2, 1), dtype=int)) == 3

    def test_shape_detect(self):
        from numpy import array
        ar = array([range(i*3, i*3+3) for i in range(3)])
        assert len(ar) == 3
        assert ar.shape == (3, 3)
        for i in range(3):
            for j in range(3):
                assert ar[i, j] == i*3+j
    
    def test_get_set_slices(self):
        from numpy import array
        gen_array = self.gen_array
        compare = self.compare
        #getitem
        ar = array(gen_array((3,3)))
        s1 = ar[0]
        assert s1[1]==1
        s2 = ar[1:3]
        assert s2[0][0] == 3
        raises(IndexError, ar.__getitem__, 'what a strange index')
        raises(IndexError, ar.__getitem__, (2, 2, 2)) #too many
        raises(IndexError, ar.__getitem__, 5)
        raises(IndexError, ar.__getitem__, (0, 6))
        #print ar[2:2].shape
        assert 0 in ar[2:2].shape
        assert compare(ar[-1], ar[2])
        assert compare(ar[2:3][0], ar[2])
        assert compare(ar[1, 0::2], [3, 5])
        assert compare(ar[0::2, 0], [0, 6])
        #setitem
        ar[2] = 3
        assert ar[2, 0] == ar[2, 1] == ar[2, 2] == 3
        raises(ValueError, ar.__setitem__, slice(2, 3), [1])
        ar[2] = [0, 1, 2]
        assert compare(ar[0], ar[2])
        assert compare(ar[..., 0], [0, 3, 0])


            
