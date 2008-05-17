import py
from pypy.rlib.rsdl import RSDL


def test_sdl_init():
    assert RSDL.Init(RSDL.INIT_VIDEO) >= 0
    RSDL.Quit()

def test_set_video_mode():
    assert RSDL.Init(RSDL.INIT_VIDEO) >= 0
    surface = RSDL.SetVideoMode(640, 480, 32, 0)
    assert surface
    RSDL.Quit()
