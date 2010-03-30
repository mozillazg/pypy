from pypy.module.cpyext.test.test_api import BaseApiTest
import sys

class TestIntObject(BaseApiTest):
    def test_intobject(self, space, api):
        assert api.PyInt_Check(space.wrap(3))
        assert api.PyInt_Check(space.w_True)
        assert not api.PyInt_Check(space.wrap((1, 2, 3)))
        for i in [3, -5, -1, -sys.maxint, sys.maxint - 1]:
            x = api.PyInt_AsLong(space.wrap(i))
            assert x == i
            w_x = api.PyInt_FromLong(x + 1)
            assert space.type(w_x) is space.w_int
            assert space.eq_w(w_x, space.wrap(i + 1))

        assert api.PyInt_AsLong(space.w_None) == -1
        assert api.PyErr_Occurred() is space.w_TypeError
        api.PyErr_Clear()
