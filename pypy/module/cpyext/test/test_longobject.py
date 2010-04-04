
import sys

from pypy.objspace.std.intobject import W_IntObject
from pypy.objspace.std.longobject import W_LongObject
from pypy.module.cpyext.test.test_api import BaseApiTest


class TestLongObject(BaseApiTest):
    def test_FromLong(self, space, api):
        value = api.PyLong_FromLong(3)
        assert isinstance(value, W_IntObject)
        assert space.unwrap(value) == 3

        value = api.PyLong_FromLong(sys.maxint + 1)
        assert isinstance(value, W_LongObject)
        assert space.unwrap(value) == sys.maxint + 1 # should obviously fail but doesnt
    
    def test_asulong(self, space, api):
        w_value = api.PyLong_FromLong((sys.maxint - 1) / 2)
        w_value = space.mul(w_value, space.wrap(4))
        value = api.PyLong_AsUnsignedLong(w_value)
        assert value == (sys.maxint - 1) * 2
    
    def test_type_check(self, space, api):
        w_l = space.wrap(sys.maxint + 1)
        assert api.PyLong_Check(w_l)
        assert api.PyLong_CheckExact(w_l)
        
        w_i = space.wrap(sys.maxint)
        assert not api.PyLong_Check(w_i)
        assert not api.PyLong_CheckExact(w_i)
        
        L = space.appexec([], """():
            class L(long):
                pass
            return L
        """)
        l = space.call_function(L)
        assert api.PyLong_Check(l)
        assert not api.PyLong_CheckExact(l)
