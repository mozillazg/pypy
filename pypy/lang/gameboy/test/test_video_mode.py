from pypy.lang.gameboy import constants
from pypy.lang.gameboy.video_sprite import Sprite
from pypy.lang.gameboy.video import Video
from pypy.lang.gameboy.test.test_video import get_video
import py

# ------------------------------------------------------------------------------

def get_mode0():
    return Mode0(get_video())

def get_mode1():
    return Mode1(get_video())

def get_mode2():
    return Mode2(get_video())

def get_mode3():
    return Mode3(get_video())


# ------------------------------------------------------------------------------