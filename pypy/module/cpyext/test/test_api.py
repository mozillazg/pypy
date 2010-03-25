from pypy.conftest import gettestobjspace
from pypy.rpython.lltypesystem import rffi, lltype
from pypy.interpreter.baseobjspace import W_Root
from pypy.module.cpyext.state import State
from pypy.module.cpyext import api
PyObject = api.PyObject

@api.cpython_api([PyObject], lltype.Void)
def PyPy_GetWrapped(space, w_arg):
    assert isinstance(w_arg, W_Root)
@api.cpython_api([PyObject], lltype.Void)
def PyPy_GetReference(space, arg):
    assert lltype.typeOf(arg) is  PyObject

class BaseApiTest:
    def setup_class(cls):
        cls.space = gettestobjspace(usemodules=['cpyext'])
        class CAPI:
            def __getattr__(self, name):
                return getattr(cls.space, name)
        cls.api = CAPI()
        CAPI.__dict__.update(api.INTERPLEVEL_API)

    def teardown_method(self, func):
        state = self.space.fromcache(State)
        assert state.exc_value is None

class TestConversion(BaseApiTest):
    def test_conversions(self, space, api):
        api.PyPy_GetWrapped(space.w_None)
        api.PyPy_GetReference(space.w_None)

