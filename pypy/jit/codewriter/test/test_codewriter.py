from pypy.jit.codewriter.codewriter import CodeWriter


def test_loop():
    def f(a, b):
        while a > 0:
            b += a
            a -= 1
        return b
    cw = CodeWriter()
    jitcode = cw.transform_func_to_jitcode(f, [5, 6])
    assert jitcode._code() == ("\x00\x10\x00\x00\x00"
                               "\x01\x01\x00\x01"
                               "\x02\x00\x01\x00"
                               "\x03\x00\x00"
                               "\x04\x01")
    assert cw.assembler.insns == {'goto_if_not_int_gt/Lic': 0,
                                  'int_add/iii': 1,
                                  'int_sub/ici': 2,
                                  'goto/L': 3,
                                  'int_return/i': 4}

def test_integration():
    from pypy.jit.metainterp.blackhole import BlackholeInterpBuilder
    def f(a, b):
        while a > 2:
            b += a
            a -= 1
        return b
    cw = CodeWriter()
    jitcode = cw.transform_func_to_jitcode(f, [5, 6])
    blackholeinterpbuilder = BlackholeInterpBuilder(cw)
    blackholeinterp = blackholeinterpbuilder.acquire_interp()
    blackholeinterp.setarg_i(0, 6)
    blackholeinterp.setarg_i(1, 100)
    blackholeinterp.run(jitcode, 0)
    assert blackholeinterp.result_i == 100+6+5+4+3
