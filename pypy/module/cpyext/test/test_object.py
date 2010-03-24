from pypy.module.cpyext.test.test_cpyext import BaseApiTest

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
