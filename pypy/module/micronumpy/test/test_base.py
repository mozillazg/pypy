from pypy.conftest import gettestobjspace
from pypy.module.micronumpy.interp_numarray import create_sdarray, FloatWrapper, ScalarWrapper
from pypy.module.micronumpy.interp_dtype import Float64_dtype

class BaseNumpyAppTest(object):
    def setup_class(cls):
        cls.space = gettestobjspace(usemodules=('micronumpy',))

class TestSignature(object):
    def test_binop_signature(self, space):
        ar = create_sdarray(10, Float64_dtype)
        v1 = ar.descr_add(space, ar)
        v2 = ar.descr_add(space, FloatWrapper(2.0))
        assert v1.signature is not v2.signature
        v3 = ar.descr_add(space, FloatWrapper(1.0))
        assert v2.signature is v3.signature
        v4 = ar.descr_add(space, ar)
        assert v1.signature is v4.signature

    def test_slice_signature(self, space):
        ar = create_sdarray(10, Float64_dtype)
        v1 = ar.descr_getitem(space, space.wrap(slice(1, 5, 1)))
        v2 = ar.descr_getitem(space, space.wrap(slice(4, 6, 1)))
        assert v1.signature is v2.signature

        v3 = ar.descr_add(space, v1)
        v4 = ar.descr_add(space, v2)
        assert v3.signature is v4.signature
