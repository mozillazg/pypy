from pypy.rpython.lltypesystem import rffi, lltype
from pypy.module.cpyext.test.test_api import BaseApiTest

class TestDictObject(BaseApiTest):
    def test_dict(self, space, api):
        d = api.PyDict_New()
        assert space.eq_w(d, space.newdict())

        assert space.eq_w(api.PyDict_GetItem(space.wrap({"a": 72}),
                                             space.wrap("a")),
                          space.wrap(72))

        assert api.PyDict_SetItem(d, space.wrap("c"), space.wrap(42)) >= 0
        assert space.eq_w(space.getitem(d, space.wrap("c")),
                          space.wrap(42))

        space.setitem(d, space.wrap("name"), space.wrap(3))
        assert space.eq_w(api.PyDict_GetItem(d, space.wrap("name")),
                          space.wrap(3))

        space.delitem(d, space.wrap("name"))
        assert not api.PyDict_GetItem(d, space.wrap("name"))
        assert not api.PyErr_Occurred()

        buf = rffi.str2charp("name")
        assert not api.PyDict_GetItemString(d, buf)
        rffi.free_charp(buf)
        assert not api.PyErr_Occurred()

        assert api.PyDict_DelItem(d, space.wrap("c")) == 0
        assert api.PyDict_DelItem(d, space.wrap("name")) < 0
        assert api.PyErr_Occurred() is space.w_KeyError
        api.PyErr_Clear()
        assert api.PyDict_Size(d) == 0

        d = space.wrap({'a': 'b'})
        api.PyDict_Clear(d)
        assert api.PyDict_Size(d) == 0

    def test_check(self, space, api):
        d = api.PyDict_New()
        assert api.PyDict_Check(d)
        assert api.PyDict_CheckExact(d)
        sub = space.appexec([], """():
            class D(dict):
                pass
            return D""")
        d = space.call_function(sub)
        assert api.PyDict_Check(d)
        assert not api.PyDict_CheckExact(d)
        i = space.wrap(2)
        assert not api.PyDict_Check(i)
        assert not api.PyDict_CheckExact(i)
