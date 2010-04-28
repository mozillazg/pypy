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

    def test_pycobject_import(self, space, api):
        ptr = rffi.cast(rffi.VOIDP_real, 1234)
        obj = api.PyCObject_FromVoidPtr(ptr, lltype.nullptr(destructor_short.TO))
        space.setattr(space.sys, space.wrap("_cpyext_cobject"), obj)

        charp1 = rffi.str2charp("sys")
        charp2 = rffi.str2charp("_cpyext_cobject")
        assert api.PyCObject_Import(charp1, charp2) == ptr
        rffi.free_charp(charp1)
        rffi.free_charp(charp2)

        api.Py_DecRef(obj)
        space.delattr(space.sys, space.wrap("_cpyext_cobject"))
