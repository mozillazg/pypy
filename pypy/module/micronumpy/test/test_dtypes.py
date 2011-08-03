import py

from pypy.module.micronumpy.test.test_base import BaseNumpyAppTest

class AppTestDtype(BaseNumpyAppTest):
    def test_dtype(self):
        from numpy import dtype
        d = dtype('l')
        assert d.num == 7
        assert d.kind == 'i'
    
    def test_bool_array(self):
        from numpy import array
        a = array([0, 1, 2, 2.5], '?')
        assert a[0] == False
        for i in xrange(1, 4):
            assert a[i] == True

    def test_overflow(self):
        from numpy import array
        # only one 32-bit system for now.. will change to 'i' when we can
        assert array([3], '?')[0] == True
        assert array([128], 'b')[0] == -128
        assert array([256], 'B')[0] == 0
        assert array([32768], 'h')[0] == -32768
        assert array([65536], 'H')[0] == 0
        raises(OverflowError, "array([2147483648], 'i')")
        raises(OverflowError, "array([4294967296], 'I')")
        raises(OverflowError, "array([9223372036854775808], 'q')")
        raises(OverflowError, "array([18446744073709551616], 'Q')")

    def test_int_array(self):
        from numpy import array
        a = array([1.5, 2.5, 3.5], 'l')
        assert a[0] == 1
        assert a[1] == 2
        assert a[2] == 3
