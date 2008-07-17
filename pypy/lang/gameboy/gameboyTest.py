from pypy.lang.gameboy.gameboy_implementation import *
import sys

from AppKit import NSApplication
NSApplication.sharedApplication()

ROM_PATH = str(py.magic.autopath().dirpath())+"/rom"

filename = ""
if len(sys.argv) > 1:
    print sys.argv
    filename = sys.argv[1]
else:
    pos = str(9)
    filename = ROM_PATH+"/rom"+pos+"/rom"+pos+".gb"
print "loading rom: ", str(filename)
gameBoy = GameBoyImplementation()
try:
    gameBoy.load_cartridge_file(str(filename))
except:
    gameBoy.load_cartridge_file(str(filename), verify=False)
    print "Cartridge is Corrupted!"
gameBoy.mainLoop()
#pdb.runcall(gameBoy.mainLoop)
