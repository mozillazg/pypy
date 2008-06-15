
from pypy.module._ctypes.test.support import BasicAppTest

class AppTestBasic(BasicAppTest):
    def test_int_base(self):
        assert self.dll.get_an_integer() == 42

    def test_restype(self):
        from _ctypes import _SimpleCData
        class c_int(_SimpleCData):
            _type_ = 'i'

        f = self.dll.get_an_integer
        f.restype = c_int
        assert f() == 42

    def test_float_restype(self):
        from _ctypes import _SimpleCData
        class c_float(_SimpleCData):
            _type_ = 'd'

        f = self.dll.my_sqrt
        f.restype = c_float
        assert f(4.0) == 2.0
