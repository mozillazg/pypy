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
        assert api.PyErr_Occurred() is space.w_KeyError
        api.PyErr_Clear()
