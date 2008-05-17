import py, sys
from pypy.rlib.rsdl import RSDL
from pypy.rlib.rarithmetic import r_uint
from pypy.rpython.lltypesystem import lltype, rffi
from pypy import conftest

#
#  This test file is skipped unless run with "py.test --view".
#  If it is run as "py.test --view -s", then it interactively asks
#  for confirmation that the window looks as expected.
#


class TestVideo:

    def setup_method(self, meth):
        if not conftest.option.view:
            py.test.skip("'--view' not specified, "
                         "skipping tests that open a window")
        assert RSDL.Init(RSDL.INIT_VIDEO) >= 0
        self.screen = RSDL.SetVideoMode(640, 480, 32, 0)
        assert self.screen

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
        fmt = self.screen.c_format
        for colorname, r, g, b in [('dark red', 128, 0, 0),
                                   ('yellow', 255, 255, 0),
                                   ('blue', 0, 0, 255)]:
            color = RSDL.MapRGB(fmt, r, g, b)
            RSDL.FillRect(self.screen, lltype.nullptr(RSDL.Rect), color)
            RSDL.Flip(self.screen)
            self.check("Screen filled with %s" % colorname)

    def test_caption(self):
        RSDL.WM_SetCaption("Hello World!", "Hello World!")
        self.check('The window caption is "Hello World!"')

    def test_blit_rect(self):
        surface = RSDL.CreateRGBSurface(0, 150, 50, 32,
                                        r_uint(0x000000FF),
                                        r_uint(0x0000FF00),
                                        r_uint(0x00FF0000),
                                        r_uint(0xFF000000))
        fmt = surface.c_format
        color = RSDL.MapRGB(fmt, 255, 0, 0)
        RSDL.FillRect(surface, lltype.nullptr(RSDL.Rect), color)
        dstrect = lltype.malloc(RSDL.Rect, flavor='raw')
        try:
            rffi.setintfield(dstrect, 'c_x',  10)
            rffi.setintfield(dstrect, 'c_y',  10)
            rffi.setintfield(dstrect, 'c_w', 150)
            rffi.setintfield(dstrect, 'c_h',  50)
            RSDL.BlitSurface(surface, lltype.nullptr(RSDL.Rect), self.screen, dstrect)
            RSDL.Flip(self.screen)
        finally:
            lltype.free(dstrect, flavor='raw')
        RSDL.FreeSurface(surface)
        self.check("Red rectangle(150px * 50px) at the top left, 10 pixels from the border")

    def teardown_method(self, meth):
        RSDL.Quit()

