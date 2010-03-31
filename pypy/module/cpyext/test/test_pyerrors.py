from pypy.module.cpyext.state import State
from pypy.module.cpyext.test.test_api import BaseApiTest
from pypy.module.cpyext.test.test_cpyext import AppTestCpythonExtensionBase
from pypy.rpython.lltypesystem import rffi

class TestExceptions(BaseApiTest):
    def test_GivenExceptionMatches(self, space, api):
        old_style_exception = space.appexec([], """():
            class OldStyle:
                pass
            return OldStyle
        """)
        exc_matches = api.PyErr_GivenExceptionMatches

        string_exception = space.wrap('exception')
        instance = space.call_function(space.w_ValueError)
        old_style_instance = space.call_function(old_style_exception)
        assert exc_matches(string_exception, string_exception)
        assert exc_matches(old_style_exception, old_style_exception)
        assert not exc_matches(old_style_exception, space.w_Exception)
        assert exc_matches(instance, space.w_ValueError)
        assert exc_matches(old_style_instance, old_style_exception)
        assert exc_matches(space.w_ValueError, space.w_ValueError)
        assert exc_matches(space.w_IndexError, space.w_LookupError)
        assert not exc_matches(space.w_ValueError, space.w_LookupError)

        exceptions = space.newtuple([space.w_LookupError, space.w_ValueError])
        assert exc_matches(space.w_ValueError, exceptions)

    def test_Occurred(self, space, api):
        assert not api.PyErr_Occurred()
        string = rffi.str2charp("spam and eggs")
        api.PyErr_SetString(space.w_ValueError, string)
        rffi.free_charp(string)
        assert api.PyErr_Occurred() is space.w_ValueError

        api.PyErr_Clear()

    def test_SetObject(self, space, api):
        api.PyErr_SetObject(space.w_ValueError, space.wrap("a value"))
        assert api.PyErr_Occurred() is space.w_ValueError
        state = space.fromcache(State)
        assert space.eq_w(state.exc_value, space.wrap("a value"))

        api.PyErr_Clear()

class AppTestFetch(AppTestCpythonExtensionBase):
    def test_occurred(self):
        module = self.import_extension('foo', [
            ("check_error", "METH_NOARGS",
             '''
             PyErr_SetString(PyExc_TypeError, "message");
             PyErr_Occurred();
             PyErr_Clear();
             Py_RETURN_TRUE;
             '''
             ),
            ])
        module.check_error()
