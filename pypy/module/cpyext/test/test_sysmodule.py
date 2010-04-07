from pypy.module.cpyext.test.test_api import BaseApiTest
from pypy.rpython.lltypesystem import rffi

class TestSysModule(BaseApiTest):
    def test_sysmodule(self, space, api):
        version_info = rffi.str2charp("version_info")
        assert api.PySys_GetObject(version_info)
        assert not api.PyErr_Occurred()
        rffi.free_charp(version_info)

        i_do_not_exist = rffi.str2charp("i_do_not_exist")
        assert not api.PySys_GetObject(i_do_not_exist)
        assert not api.PyErr_Occurred()
        rffi.free_charp(i_do_not_exist)
