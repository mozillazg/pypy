import py

from rpython.rlib.rawrefcount import REFCNT_FROM_PYPY_LIGHT
from pypy.module.cpyext.pyobject import PyObject, PyObjectP
from pypy.module.cpyext.test.test_api import BaseApiTest
from rpython.rtyper.lltypesystem import rffi, lltype


class TestTupleObject(BaseApiTest):

    def test_tupleobject(self, space, api):
        assert not api.PyTuple_Check(space.w_None)
        py_none = api.get_pyobj_and_incref(space.w_None)
        assert api.PyTuple_SetItem(space.w_None, 0, py_none) == -1
        atuple = space.newtuple([space.wrap(0), space.wrap(1),
                                 space.wrap('yay')])
        assert api.PyTuple_Size(atuple) == 3
        #assert api.PyTuple_GET_SIZE(atuple) == 3   --- a C macro
        raises(TypeError, api.PyTuple_Size(space.newlist([])))
        api.PyErr_Clear()

    def test_tupleobject_spec_ii(self, space, api):
        atuple = space.newtuple([space.wrap(10), space.wrap(11)])
        assert api.PyTuple_Size(atuple) == 2
        w_obj1 = api.from_pyobj(api.PyTuple_GetItem(atuple, 0))
        w_obj2 = api.from_pyobj(api.PyTuple_GetItem(atuple, 1))
        assert space.eq_w(w_obj1, space.wrap(10))
        assert space.eq_w(w_obj2, space.wrap(11))

    def test_tupleobject_spec_oo(self, space, api):
        w_obj1 = space.newlist([])
        w_obj2 = space.newlist([])
        atuple = space.newtuple([w_obj1, w_obj2])
        assert api.PyTuple_Size(atuple) == 2
        assert api.from_pyobj(api.PyTuple_GetItem(atuple, 0)) is w_obj1
        assert api.from_pyobj(api.PyTuple_GetItem(atuple, 1)) is w_obj2

    def test_new_setitem(self, space, api):
        w_obj1 = space.newlist([])
        pyobj1 = api.get_pyobj_and_incref(w_obj1)
        w_obj2 = space.newlist([])
        pyobj2 = api.get_pyobj_and_incref(w_obj2)
        py_tuple = api.PyTuple_New(2)
        assert not api.pyobj_has_w_obj(py_tuple)

        assert pyobj1.c_ob_refcnt == REFCNT_FROM_PYPY_LIGHT + 1
        assert pyobj2.c_ob_refcnt == REFCNT_FROM_PYPY_LIGHT + 1
        api.PyTuple_SetItem(py_tuple, 0, pyobj1)
        api.PyTuple_SetItem(py_tuple, 1, pyobj2)
        assert pyobj1.c_ob_refcnt == REFCNT_FROM_PYPY_LIGHT + 1
        assert pyobj2.c_ob_refcnt == REFCNT_FROM_PYPY_LIGHT + 1

        assert api.PyTuple_GetItem(py_tuple, 0) == pyobj1
        assert pyobj1.c_ob_refcnt == REFCNT_FROM_PYPY_LIGHT + 1

        api.PyTuple_SetItem(py_tuple, 0, pyobj2)
        assert pyobj1.c_ob_refcnt == REFCNT_FROM_PYPY_LIGHT + 0
        assert pyobj2.c_ob_refcnt == REFCNT_FROM_PYPY_LIGHT + 1

        assert not api.pyobj_has_w_obj(py_tuple)
        w_tup = api.from_pyobj(py_tuple)
        assert w_tup is api.from_pyobj(py_tuple)
        assert api.PyTuple_GetItem(py_tuple, 1) == pyobj2
        assert pyobj1.c_ob_refcnt == REFCNT_FROM_PYPY_LIGHT + 0
        assert pyobj2.c_ob_refcnt == REFCNT_FROM_PYPY_LIGHT + 1

        assert space.getitem(w_tup, space.wrap(0)) is w_obj2
        assert space.getitem(w_tup, space.wrap(1)) is w_obj2

        assert api.PyTuple_SetItem(py_tuple, 0, pyobj1) == -1
        api.PyErr_Clear()

    def test_tuple_resize(self, space, api):
        py_tuple = api.PyTuple_New(3)
        ar = lltype.malloc(PyObjectP.TO, 1, flavor='raw')
        ar[0] = py_tuple
        api._PyTuple_Resize(ar, 2)
        py_tuple = ar[0]
        assert api.PyTuple_Size(py_tuple) == 2

        api._PyTuple_Resize(ar, 10)
        py_tuple = ar[0]
        assert api.PyTuple_Size(py_tuple) == 10

        api.Py_DecRef(py_tuple)
        lltype.free(ar, flavor='raw')

    def test_getslice(self, space, api):
        w_tuple = space.newtuple([space.wrap(i) for i in range(10)])
        w_slice = api.PyTuple_GetSlice(w_tuple, 3, -3)
        assert space.eq_w(w_slice,
                          space.newtuple([space.wrap(i) for i in range(3, 7)]))

