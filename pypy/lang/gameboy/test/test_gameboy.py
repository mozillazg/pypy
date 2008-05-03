
import py
from pypy.lang.gameboy.gameboy import *



def get_gameboy():
    gameboy = GameBoy()
    return gameboy



def test_init():
    gameboy = get_gameboy()