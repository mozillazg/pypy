
from pypy.module._ctypes.test.support import BasicAppTest

class AppTestBasic(BasicAppTest):
    def test_int_base(self):
        from _ctypes import CDLL
        dll = CDLL(self.so_file)
        assert dll.get_an_integer() == 42

