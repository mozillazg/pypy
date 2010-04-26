import py

from pypy.rpython.lltypesystem import rffi, lltype
from pypy.module.cpyext.test.test_api import BaseApiTest
from pypy.module.cpyext.pycobject import destructor_short, PyCObject

class TestPyCObject(BaseApiTest):
    def test_pycobject(self, space, api):
        ptr = rffi.cast(rffi.VOIDP_real, 1234)
        obj = api.PyCObject_FromVoidPtr(ptr, lltype.nullptr(destructor_short.TO))
        try:
            assert rffi.cast(PyCObject, obj).c_cobject == ptr
        finally:
            api.Py_DecRef(obj)
