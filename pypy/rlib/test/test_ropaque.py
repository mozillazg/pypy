
from pypy.rlib.ropaque import cast_obj_to_ropaque, cast_ropaque_to_obj
from pypy.rpython.lltypesystem import lltype
from pypy.rpython.test.test_llinterp import interpret

class TestROpaque(object):
    def test_base_cast(self):
        class A(object):
            pass

        a = A()
        lla = cast_obj_to_ropaque(a)
        assert isinstance(lltype.typeOf(lla), lltype.LowLevelType)
        assert cast_ropaque_to_obj(A, lla) is a

    def test_cast_translated(self):
        class A(object):
            pass

        def g(lla):
            return cast_ropaque_to_obj(A, lla)
        
        def f():
            a = A()
            assert a is g(cast_obj_to_ropaque(a))

        interpret(f, [])
