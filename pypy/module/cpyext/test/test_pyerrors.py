from pypy.module.cpyext.test.test_api import BaseApiTest
from pypy.rpython.lltypesystem import rffi

class TestExceptions(BaseApiTest):
    def test_Occurred(self, space, api):
        assert not api.PyErr_Occurred()
        string = rffi.str2charp("spam and eggs")
        api.PyErr_SetString(space.w_ValueError, string)
        rffi.free_charp(string)
        assert api.PyErr_Occurred() is space.w_ValueError

        api.PyErr_Clear()
