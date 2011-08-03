import py

from pypy.module.micronumpy.test.test_base import BaseNumpyAppTest

class AppTestDtype(BaseNumpyAppTest):
    def test_dtype(self):
        from numpy import dtype
        d = dtype('l')
        assert d.num == 7
        assert d.kind == 'i'

    def test_too_large_int(self):
        from numpy import array
        # only one 32-bit system for now.. will change to 'i' when we can
        raises(OverflowError, "array([2147483648], 'l')")

    def test_int_array(self):
        from numpy import array
        a = array([1.5, 2.5, 3.5], 'l')
        assert a[0] == 1
        assert a[1] == 2
        assert a[2] == 3
