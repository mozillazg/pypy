
import sys

from pypy.objspace.std.intobject import W_IntObject
from pypy.objspace.std.longobject import W_LongObject
from pypy.module.cpyext.test.test_api import BaseApiTest
from pypy.module.cpyext.test.test_cpyext import AppTestCpythonExtensionBase


class TestLongObject(BaseApiTest):
    def test_FromLong(self, space, api):
        value = api.PyLong_FromLong(3)
        assert isinstance(value, W_LongObject)
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

    def test_as_longlong(self, space, api):
        assert api.PyLong_AsLongLong(space.wrap(1<<62)) == 1<<62
        assert api.PyLong_AsLongLong(space.wrap(1<<63)) == -1
        api.PyErr_Clear()

        assert api.PyLong_AsUnsignedLongLong(space.wrap(1<<63)) == 1<<63
        assert api.PyLong_AsUnsignedLongLong(space.wrap(1<<64)) == (1<<64) - 1
        assert api.PyErr_Occurred()
        api.PyErr_Clear()

class AppTestLongObject(AppTestCpythonExtensionBase):
    def test_fromlonglong(self):
        module = self.import_extension('foo', [
            ("from_longlong", "METH_NOARGS",
             """
                 return PyLong_FromLongLong((long long)-1);
             """),
            ("from_unsignedlonglong", "METH_NOARGS",
             """
                 return PyLong_FromUnsignedLongLong((unsigned long long)-1);
             """)])
        assert module.from_longlong() == -1
        assert module.from_unsignedlonglong() == (1<<64) - 1
