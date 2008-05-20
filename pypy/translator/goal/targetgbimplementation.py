import os
import py
from pypy.lang.gameboy.gameboyImplementation import GameBoyImplementation


ROM_PATH = str(py.magic.autopath().dirpath().dirpath().dirpath())+"/lang/gameboy/rom"
EMULATION_CYCLES = 64


# This loads the whole mini.image in advance.  At run-time,
# it executes the tinyBenchmark.  In this way we get an RPython
# "image" frozen into the executable, mmap'ed by the OS from
# there and loaded lazily when needed :-)


# XXX this only compiles if sys.recursionlimit is high enough!
# On non-Linux platforms I don't know if there is enough stack to
# compile...
#sys.setrecursionlimit(100000)


def entry_point(argv=None):
    if len(argv) > 1:
        filename = argv[1]
    else:
        filename = ROM_PATH+"/rom9/rom9.gb"
    gameBoy = GameBoyImplementation()
    #gameBoy.load_cartridge_file(ROM_PATH+"/rom4/rom4.gb")#filename)
    gameBoy.emulate(EMULATION_CYCLES)
#    #gameBoy.load_cartridge_file(str(filename))
    
    return 0
    

# _____ Define and setup target ___

def target(*args):
    return entry_point, None

def test_target():
    entry_point(["boe", ROM_PATH+"/rom4/rom4.gb"])
