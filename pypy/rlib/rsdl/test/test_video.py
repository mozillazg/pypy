import py, sys
from pypy.rlib.rsdl import RSDL
from pypy.rlib.rarithmetic import r_uint
from pypy.rpython.lltypesystem import lltype, rffi
from pypy import conftest


class TestVideo:

    def setup_method(self, meth):
        if not conftest.option.view:
            py.test.skip("'--view' not specified, "
                         "skipping tests that open a window")
        assert RSDL.Init(RSDL.INIT_VIDEO) >= 0
        self.surface = RSDL.SetVideoMode(640, 480, 32, 0)
        assert self.surface

    def check(self, msg):
        if sys.stdout.isatty():
            print
            answer = raw_input('Interactive test: %s - ok? [Y] ' % msg)
            if answer and not answer.upper().startswith('Y'):
                py.test.fail(msg)
        else:
            print msg

    def test_simple(self):
        pass   # only checks that opening and closing the window works

    def test_fillrect_full(self):
        fmt = self.surface.c_format
        for colorname, r, g, b in [('dark red', 128, 0, 0),
                                   ('yellow', 255, 255, 0),
                                   ('blue', 0, 0, 255)]:
            color = RSDL.MapRGB(fmt, r, g, b)
            RSDL.FillRect(self.surface, lltype.nullptr(RSDL.Rect), color)
            RSDL.Flip(self.surface)
            self.check("Screen filled with %s" % colorname)

    def teardown_method(self, meth):
        RSDL.Quit()
