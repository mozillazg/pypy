import py
from pypy.jit.backend.x86.test.test_basic import Jit386Mixin
from pypy.jit.metainterp.test import test_outofline

class TestOutOfLine(Jit386Mixin, test_outofline.OutOfLineTests):
    # for the individual tests see
    # ====> ../../../metainterp/test/test_outofline.py
    pass

