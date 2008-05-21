import py, sys
from pypy.rlib.rsdl import RSDL, RSDL_helper
from pypy.rlib.rarithmetic import r_uint
from pypy.rpython.lltypesystem import lltype, rffi

class TestSurface:

    def setup_method(self, meth):
        self.large_surface = RSDL.CreateRGBSurface(0, 300, 300, 32,
                                        r_uint(0x000000FF),
                                        r_uint(0x0000FF00),
                                        r_uint(0x00FF0000),
                                        r_uint(0x00000000))
        self.small_surface = RSDL.CreateRGBSurface(0, 50, 50, 32,
                                        r_uint(0x000000FF),
                                        r_uint(0x0000FF00),
                                        r_uint(0x00FF0000),
                                        r_uint(0x00000000))
        fmt = self.small_surface.c_format
        color = RSDL.MapRGB(fmt, 255, 0, 0)
        RSDL.FillRect(self.small_surface, lltype.nullptr(RSDL.Rect), color)

    def test_simple(self):
        pass   # only checks that creating the surfaces works

    def test_set_alpha(self):
        assert RSDL.SetAlpha(self.small_surface, RSDL.SRCALPHA, 128) == 0
        RSDL_helper.blit_complete_surface(
            self.small_surface,
            self.large_surface,
            10, 10)
        RSDL_helper.blit_complete_surface(
            self.small_surface,
            self.large_surface,
            20, 20)
        for position, color in (
                (( 0, 0), (  0,0,0)), # no rect
                ((10,10), (127,0,0)), # one rect
                ((20,20), (191,0,0))  # two overlapping rects
            ):
            fetched_color = RSDL_helper.get_pixel(self.large_surface, position[0], position[1])
            assert RSDL_helper.get_rgb(fetched_color, self.large_surface.c_format) == color 

    def teardown_method(self, meth):
        RSDL.FreeSurface(self.small_surface)
        RSDL.FreeSurface(self.large_surface)
        RSDL.Quit()

