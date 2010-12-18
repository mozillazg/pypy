from pypy.module.cpyext.test.test_api import BaseApiTest
from pypy.rpython.lltypesystem import lltype, rffi
from pypy.module.cpyext.api import PyObject

class TestFloatObject(BaseApiTest):
    def test_floatobject(self, space, api):
        assert space.unwrap(api.PyFloat_FromDouble(3.14)) == 3.14
        assert api.PyFloat_AsDouble(space.wrap(23.45)) == 23.45
        assert api.PyFloat_AS_DOUBLE(space.wrap(23.45)) == 23.45

        assert api.PyFloat_AsDouble(space.w_None) == -1
        api.PyErr_Clear()

    def test_coerce(self, space, api):
        assert space.type(api.PyNumber_Float(space.wrap(3))) is space.w_float

        class Coerce(object):
            def __float__(self):
                return 42.5
        assert space.eq_w(api.PyNumber_Float(space.wrap(Coerce())),
                          space.wrap(42.5))

    def test_from_string(self, space, api):
        def test_number(n, expectfail=False):
            np = lltype.nullptr(rffi.CCHARPP.TO)
            n_str = rffi.str2charp(str(n))
            f = api.PyFloat_FromString(n_str, np)
            rffi.free_charp(n_str)
            if expectfail:
                assert f == None
            else:
                assert space.eq_w(f, space.wrap(n))

        test_number(0.0)
        test_number(42.0)
        test_number("abcd", True)
