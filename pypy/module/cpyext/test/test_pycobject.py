import py

from pypy.rpython.lltypesystem import rffi, lltype
from pypy.module.cpyext.test.test_api import BaseApiTest
from pypy.module.cpyext.pycobject import destructor_short, PyCObject

class TestPyCObject(BaseApiTest):
    def test_pycobject(self, space, api):
        ptr = rffi.cast(rffi.VOIDP_real, 1234)
        obj = api.PyCObject_FromVoidPtr(ptr, lltype.nullptr(destructor_short.TO))
        assert api.PyCObject_Check(obj)
        assert api.PyCObject_AsVoidPtr(obj) == ptr
        assert rffi.cast(PyCObject, obj).c_cobject == ptr
        api.Py_DecRef(obj)

        obj = api.PyCObject_FromVoidPtrAndDesc(ptr, ptr,
                                               lltype.nullptr(destructor_short.TO))
        api.Py_DecRef(obj)
