from pypy.jit.codewriter.jitcode import JitCode


def test_num_regs():
    j = JitCode("test")
    j.setup(num_regs_i=12, num_regs_r=34, num_regs_f=56)
    assert j.num_regs_i() == 12
    assert j.num_regs_r() == 34
    assert j.num_regs_f() == 56
    j.setup(num_regs_i=0, num_regs_r=0, num_regs_f=0)
    assert j.num_regs_i() == 0
    assert j.num_regs_r() == 0
    assert j.num_regs_f() == 0
    j.setup(num_regs_i=255, num_regs_r=255, num_regs_f=255)
    assert j.num_regs_i() == 255
    assert j.num_regs_r() == 255
    assert j.num_regs_f() == 255

def test_liveness():
    j = JitCode("test")
    j.setup(liveness={5: (" A", "b", "CD")})
    assert j.has_liveness_info(5)
    assert not j.has_liveness_info(4)
    #
    seen = []
    def callback(arg, value, index):
        assert arg == "foo"
        seen.append((value, index))
    #
    total = j.enumerate_live_vars(5, callback, "foo",
                                  {ord(" "): "i10", ord("A"): "i20"},
                                  {ord("b"): "r30"},
                                  {ord("C"): "f40", ord("D"): "f50"})
    assert total == 5
    assert seen == [("i10", 0), ("i20", 1), ("r30", 2), ("f40", 3), ("f50", 4)]
