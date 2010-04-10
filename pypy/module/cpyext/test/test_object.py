import py

from pypy.module.cpyext.test.test_api import BaseApiTest
from pypy.rpython.lltypesystem import rffi, lltype
from pypy.module.cpyext.api import Py_LT, Py_LE, Py_NE, Py_EQ,\
    Py_GE, Py_GT

class TestObject(BaseApiTest):
    def test_IsTrue(self, space, api):
        assert api.PyObject_IsTrue(space.wrap(1.0)) == 1
        assert api.PyObject_IsTrue(space.wrap(False)) == 0
        assert api.PyObject_IsTrue(space.wrap(0)) == 0

    def test_Not(self, space, api):
        assert api.PyObject_Not(space.wrap(False)) == 1
        assert api.PyObject_Not(space.wrap(0)) == 1
        assert api.PyObject_Not(space.wrap(True)) == 0
        assert api.PyObject_Not(space.wrap(3.14)) == 0

    def test_exception(self, space, api):
        class C:
            def __nonzero__(self):
                raise ValueError

        assert api.PyObject_IsTrue(space.wrap(C())) == -1
        assert api.PyObject_Not(space.wrap(C())) == -1
        api.PyErr_Clear()

    def test_HasAttr(self, space, api):
        hasattr_ = lambda w_obj, name: api.PyObject_HasAttr(w_obj,
                                                            space.wrap(name))
        assert hasattr_(space.wrap(''), '__len__')
        assert hasattr_(space.w_int, '__eq__')
        assert not hasattr_(space.w_int, 'nonexistingattr')

    def test_SetAttr(self, space, api):
        class X:
            pass
        x = X()
        api.PyObject_SetAttr(space.wrap(x), space.wrap('test'), space.wrap(5))
        assert not api.PyErr_Occurred()
        assert x.test == 5
        assert api.PyObject_HasAttr(space.wrap(x), space.wrap('test'))
        api.PyObject_SetAttr(space.wrap(x), space.wrap('test'), space.wrap(10))
        assert x.test == 10
    
    def test_getattr_string(self, space, api):
        charp1 = rffi.str2charp("__len__")
        charp2 = rffi.str2charp("not_real")
        assert api.PyObject_GetAttrString(space.wrap(""), charp1)
        assert not api.PyObject_GetAttrString(space.wrap(""), charp2)
        assert api.PyErr_Occurred() is space.w_AttributeError
        api.PyErr_Clear()
        lltype.free(charp1, flavor="raw")
        lltype.free(charp2, flavor="raw")

    def test_getitem(self, space, api):
        w_t = space.wrap((1, 2, 3, 4, 5))
        assert space.unwrap(api.PyObject_GetItem(w_t, space.wrap(3))) == 4

        w_d = space.newdict()
        space.setitem(w_d, space.wrap("a key!"), space.wrap(72))
        assert space.unwrap(api.PyObject_GetItem(w_d, space.wrap("a key!"))) == 72

    def test_size(self, space, api):
        assert api.PyObject_Size(space.newlist([space.w_None])) == 1
        
    def test_repr(self, space, api):
        w_list = space.newlist([space.w_None, space.wrap(42)])
        assert space.str_w(api.PyObject_Repr(w_list)) == "[None, 42]"
        
    def test_RichCompare(self, space, api):
        def compare(w_o1, w_o2, opid):
            res = api.PyObject_RichCompareBool(w_o1, w_o2, opid)
            w_res = api.PyObject_RichCompare(w_o1, w_o2, opid)
            assert space.is_true(w_res) == res
            return res
        
        def test_compare(o1, o2):
            w_o1 = space.wrap(o1)
            w_o2 = space.wrap(o2)
            
            for opid, expected in [
                    (Py_LT, o1 <  o2), (Py_LE, o1 <= o2),
                    (Py_NE, o1 != o2), (Py_EQ, o1 == o2),
                    (Py_GT, o1 >  o2), (Py_GE, o1 >= o2)]:
                assert compare(w_o1, w_o2, opid) == expected

        test_compare(1, 2)
        test_compare(2, 2)
        test_compare('2', '1')
        
        w_i = space.wrap(1)
        assert api.PyObject_RichCompareBool(w_i, w_i, 123456) == -1
        assert api.PyErr_Occurred() is space.w_SystemError
        api.PyErr_Clear()
