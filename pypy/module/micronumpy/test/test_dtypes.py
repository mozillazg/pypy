import py

from pypy.module.micronumpy.test.test_base import BaseNumpyAppTest

class AppTestDtype(BaseNumpyAppTest):
    def test_dtype(self):
        from numpy import dtype
        d = dtype('l')
