import py

from pypy.rpython.lltypesystem import rffi, lltype
from pypy.module.cpyext.test.test_api import BaseApiTest
from pypy.module.cpyext.pycobject import destructor_short

class TestPyCObject(BaseApiTest):
    def test_pycobject(self, space, api):
        obj = api.PyCObject_FromVoidPtr(rffi.cast(rffi.VOIDP_real, 0), lltype.nullptr(destructor_short.TO))
        api.Py_DecRef(obj)
