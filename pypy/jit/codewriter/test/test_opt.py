from pypy.jit.codewriter.opt import optimize_ssarepr
from pypy.jit.codewriter.format import assert_format, unformat_assembler


def test_opt_noop():
    test = """
        int_add %i0, %i1 -> %i2
        int_return %i2
    """
    ssarepr = unformat_assembler(test)
    optimize_ssarepr(ssarepr)
    assert_format(ssarepr, """
        int_add %i0, %i1 -> %i2
        int_return %i2
    """)

def test_goto_1():
    test = """
        goto L2
        ---
        L3:
        int_return %i0
        ---
        L2:
        goto L3
    """
    ssarepr = unformat_assembler(test)
    optimize_ssarepr(ssarepr)
    assert_format(ssarepr, """
        goto L1
        ---
        L1:
        int_return %i0
    """)

def test_goto_1bis():
    test = """
        goto L2
        ---
        L2:
        goto L3
        ---
        L3:
        int_return %i0
    """
    ssarepr = unformat_assembler(test)
    optimize_ssarepr(ssarepr)
    assert_format(ssarepr, """
        goto L1
        ---
        ---
        L1:
        int_return %i0
    """)

def test_goto_2():
    test = """
        goto L2
        ---
        L3:
        foobar
        L2:
        goto L3
    """
    ssarepr = unformat_assembler(test)
    optimize_ssarepr(ssarepr)
    assert_format(ssarepr, """
        goto L1
        ---
        L1:
        L2:
        foobar
        goto L2
    """)

def test_goto_3():
    test = """
        foobar
        L1:
        goto L1
    """
    ssarepr = unformat_assembler(test)
    optimize_ssarepr(ssarepr)
    assert_format(ssarepr, """
        foobar
        L1:
        goto L1
    """)

def test_goto_4():
    test = """
        foobar
        L1:
        goto L2
        ---
        L2:
        goto L1
    """
    ssarepr = unformat_assembler(test)
    optimize_ssarepr(ssarepr)
    assert_format(ssarepr, """
        foobar
        goto L1
        ---
        L1:
        L2:
        goto L2
    """)

def test_goto_5():
    test = """
        goto_if_some_condition L2
        foobar
        L2:
        goto L3
        ---
        L3:
        int_return %i0
    """
    ssarepr = unformat_assembler(test)
    optimize_ssarepr(ssarepr)
    assert_format(ssarepr, """
        goto_if_some_condition L1
        foobar
        goto L2
        ---
        L1:
        L2:
        int_return %i0
    """)
