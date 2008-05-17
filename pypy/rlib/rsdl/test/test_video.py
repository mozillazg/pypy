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
        self.is_interactive = sys.stdout.isatty()

    def check(self, msg):
        if self.is_interactive:
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

    def test_keypresses(self):
        if not self.is_interactive:
            py.test.skip("interactive test only")
        RSDL.EnableUNICODE(1)
        print
        print "Keys pressed in the Pygame window should be printed below."
        print "Use Escape to quit."
        while True:
            event = lltype.malloc(RSDL.Event, flavor='raw')
            try:
                ok = RSDL.WaitEvent(event)
                assert rffi.cast(lltype.Signed, ok) == 1
                c_type = rffi.getintfield(event, 'c_type')
                if c_type == RSDL.KEYDOWN:
                    p = rffi.cast(RSDL.KeyboardEventPtr, event)
                    if rffi.getintfield(p.c_keysym, 'c_sym') == RSDL.K_ESCAPE:
                        print 'Escape key'
                        break
                    char = rffi.getintfield(p.c_keysym, 'c_unicode')
                    if char != 0:
                        print 'Key:', unichr(char).encode('utf-8')
                    else:
                        print 'Some special key'
                else:
                    print '(event of type %d)' % c_type
            finally:
                lltype.free(event, flavor='raw')

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

