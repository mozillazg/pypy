from pypy.module.cpyext.test.test_cpyext import BaseApiTest

class TestFloatObject(BaseApiTest):
    def test_floatobject(self, space, api):
        assert space.unwrap(api.PyFloat_FromDouble(3.14)) == 3.14
        assert api.PyFloat_AsDouble(space.wrap(23.45)) == 23.45

        assert api.PyFloat_AsDouble(space.w_None) == -1
        api.PyErr_Clear()
