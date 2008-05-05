import os
import py
from pypy.lang.gameboy import constants
from pypy.lang.gameboy.cpu import *
from pypy.lang.gameboy.cartridge import *
from pypy.lang.gameboy.gameboy import *


ROM_PATH = str(py.magic.autopath().dirpath().dirpath().dirpath())+"lang/gameboy/rom"
EMULATION_CYCLES = 64


# This loads the whole mini.image in advance.  At run-time,
# it executes the tinyBenchmark.  In this way we get an RPython
# "image" frozen into the executable, mmap'ed by the OS from
# there and loaded lazily when needed :-)


# XXX this only compiles if sys.recursionlimit is high enough!
# On non-Linux platforms I don't know if there is enough stack to
# compile...
#sys.setrecursionlimit(100000)


def entry_point(argv):
    gameBoy = GameBoy()
    gameBoy.loadCartridgeFile(ROM_PATH+"/rom4/rom4.gb")
    gameBoy.emulate(EMULATION_CYCLES)


# _____ Define and setup target ___

def target(*args):
    return entry_point, None
