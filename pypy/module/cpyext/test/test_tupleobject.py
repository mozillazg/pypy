import py

from pypy.module.cpyext.pyobject import PyObject, PyObjectP, make_ref, from_ref
from pypy.module.cpyext.test.test_api import BaseApiTest
from pypy.rpython.lltypesystem import rffi, lltype

class TestTupleObject(BaseApiTest):
    def test_tupleobject(self, space, api):
        XXX
        assert not api.PyTuple_Check(space.w_None)
        #assert api.PyTuple_SetItem(space.w_None, 0, space.w_None) == -1     XXX
        atuple = space.newtuple([0, 1, 'yay'])
        assert api.PyTuple_Size(atuple) == 3
        assert api.PyTuple_GET_SIZE(atuple) == 3
        #raises(TypeError, api.PyTuple_Size(space.newlist([])))     XXX
        api.PyErr_Clear()
    
    def test_tuple_resize(self, space, api):
        XXX
        ref_tup = api.PyTuple_New(3)
        ar = lltype.malloc(PyObjectP.TO, 1, flavor='raw')
        ar[0] = rffi.cast(PyObject, ref_tup)
        api._PyTuple_Resize(ar, 2)
        assert ar[0] == rffi.cast(PyObject, ref_tup)
        # ^^^ our _PyTuple_Resize does not actually need to change the ptr so far
        assert api.PyTuple_Size(ar[0]) == 2
        assert api.PyTuple_GET_SIZE(ar[0]) == 2
        
        api._PyTuple_Resize(ar, 10)
        assert api.PyTuple_Size(ar[0]) == 10
        
        api.Py_DecRef(ar[0])
        lltype.free(ar, flavor='raw')
