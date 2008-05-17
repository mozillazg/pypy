import py
from pypy.rlib.rsdl import RSDL
from pypy.rlib.rarithmetic import r_uint
from pypy.rpython.lltypesystem import rffi
from pypy import conftest


def test_sdl_init():
    assert RSDL.Init(RSDL.INIT_VIDEO) >= 0
    RSDL.Quit()

def test_surface_basic():
    assert RSDL.Init(RSDL.INIT_VIDEO) >= 0
    surface = RSDL.CreateRGBSurface(0, 150, 50, 32,
                                    r_uint(0x000000FF),
                                    r_uint(0x0000FF00),
                                    r_uint(0x00FF0000),
                                    r_uint(0xFF000000))
    assert surface
    assert rffi.getintfield(surface, 'c_w') == 150
    assert rffi.getintfield(surface, 'c_h') == 50
    RSDL.FreeSurface(surface)
    RSDL.Quit()


class TestVideo:

    def setup_method(self, meth):
        if not conftest.option.view:
            py.test.skip("'--view' not specified, "
                         "skipping tests that open a window")
        assert RSDL.Init(RSDL.INIT_VIDEO) >= 0
        self.surface = RSDL.SetVideoMode(640, 480, 32, 0)
        assert self.surface

    def test_simple(self):
        pass   # only checks that opening and closing the window works

    def teardown_method(self, meth):
        RSDL.Quit()
