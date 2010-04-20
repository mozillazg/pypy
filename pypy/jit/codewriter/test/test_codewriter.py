from pypy.jit.codewriter.codewriter import CodeWriter


def test_loop():
    def f(a, b):
        while a > 0:
            b += a
            a -= 1
        return b
    cw = CodeWriter()
    jitcode = cw.transform_func_to_jitcode(f, [5, 6])
    assert jitcode.code == ("\x00\x00\x00\x02"
                            "\x01\x13\x00\x02"
                            "\x02\x01\x00\x01"
                            "\x03\x00\x01\x00"
                            "\x04\x00\x00"
                            "\x05\x01")
    assert cw.assembler.insns == {'int_gt/ici': 0,
                                  'goto_if_not/Li': 1,
                                  'int_add/iii': 2,
                                  'int_sub/ici': 3,
                                  'goto/L': 4,
                                  'int_return/i': 5}
