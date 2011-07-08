import py
from pypy.rlib import register
from pypy.rpython.lltypesystem import lltype, llmemory, rffi


def test_register():
    #
    from pypy.jit.backend.detect_cpu import autodetect
    if autodetect() == 'x86_64':
        assert register.eci is not None
        assert register.register_number == 15        # r15
    else:
        assert register.eci is None
        assert register.register_number is None


class TestLoadStore(object):
    def setup_class(cls):
        if register.register_number is None:
            py.test.skip("rlib/register not supported on this platform")

    def test_direct(self):
        a = rffi.cast(llmemory.Address, 27)
        register.store_into_reg(a)
        b = register.load_from_reg()
        assert lltype.typeOf(b) == llmemory.Address
        assert rffi.cast(lltype.Signed, b) == 27

    def test_llinterp(self):
        from pypy.rpython.test.test_llinterp import interpret
        def f(n):
            a = rffi.cast(llmemory.Address, n)
            register.store_into_reg(a)
            b = register.load_from_reg()
            return rffi.cast(lltype.Signed, b)
        res = interpret(f, [41])
        assert res == 41

    def test_compiled(self):
        from pypy.translator.c.test.test_genc import compile
        def f(n):
            a = rffi.cast(llmemory.Address, n)
            register.store_into_reg(a)
            b = register.load_from_reg()
            return rffi.cast(lltype.Signed, b)
        cfn = compile(f, [int])
        res = cfn(43)
        assert res == 43
