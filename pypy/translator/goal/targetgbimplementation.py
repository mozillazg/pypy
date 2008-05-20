import os
import py
from pypy.lang.gameboy.gameboyImplementation import GameBoyImplementation


ROM_PATH = str(py.magic.autopath().dirpath().dirpath().dirpath())+"/lang/gameboy/rom"
EMULATION_CYCLES = 64


def entry_point(argv=None):
    if len(argv) > 1:
        filename = argv[1]
    else:
        filename = ROM_PATH+"/rom9/rom9.gb"
    print "loading rom: ", str(filename)
    gameBoy = GameBoyImplementation()
    gameBoy.load_cartridge_file(str(filename))
    gameBoy.mainLoop()
    return 0
    

# _____ Define and setup target ___

def target(*args):
    return entry_point, None

def test_target():
    entry_point(["boe", ROM_PATH+"/rom4/rom4.gb"])
