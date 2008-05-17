import py
from pypy.rlib.rsdl import RSDL


def test_sdl_init():
    assert RSDL.Init(RSDL.INIT_VIDEO) >= 0
    RSDL.Quit()
