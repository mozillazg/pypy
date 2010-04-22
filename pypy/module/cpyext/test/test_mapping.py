from pypy.module.cpyext.test.test_api import BaseApiTest


class TestMapping(BaseApiTest):
    def test_check(self, space, api):
        assert api.PyMapping_Check(space.newdict())
        assert not api.PyMapping_Check(space.newlist([]))

    def test_keys(self, space, api):
        w_d = space.newdict()
        space.setitem(w_d, space.wrap("a"), space.wrap("a"))
        assert space.eq_w(api.PyMapping_Keys(w_d), space.wrap(["a"]))

    def test_items(self, space, api):
        w_d = space.newdict()
        space.setitem(w_d, space.wrap("a"), space.wrap("b"))
        assert space.eq_w(api.PyMapping_Items(w_d), space.wrap([("a", "b")]))
