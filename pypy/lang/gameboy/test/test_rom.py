
import py
from pypy.lang.gameboy import constants
from pypy.lang.gameboy.cpu import *
from pypy.lang.gameboy.cartridge import *
from pypy.lang.gameboy.gameboy import *


ROM_PATH = str(py.magic.autopath().dirpath().dirpath())+"/rom"



def test_rom1():
    gameBoy = GameBoy()
    try:
        gameBoy.loadCartridgeFile(ROM_PATH+"/rom1/rom1.raw")
        py.test.fail()
    except:
        pass
    
    
def test_rom2():
    gameBoy = GameBoy()
    try:
        gameBoy.loadCartridgeFile(ROM_PATH+"/rom2/rom2.raw")
        py.test.fail()
    except:
        pass
    

def test_rom3():
    gameBoy = GameBoy()
    gameBoy.loadCartridgeFile(ROM_PATH+"/rom3/rom3.gb")
    
    
def test_rom4():
    gameBoy = GameBoy()
    gameBoy.loadCartridgeFile(ROM_PATH+"/rom4/rom4.gb")
    
    
def test_rom5():
    gameBoy = GameBoy()
    gameBoy.loadCartridgeFile(ROM_PATH+"/rom5/rom5.gb")
    
    
def test_rom6():
    gameBoy = GameBoy()
    gameBoy.loadCartridgeFile(ROM_PATH+"/rom6/rom6.gb")
    
    
def test_rom7():
    gameBoy = GameBoy()
    gameBoy.loadCartridgeFile(ROM_PATH+"/rom7/rom7.gb")
    
    
def test_rom8():
    gameBoy = GameBoy()
    gameBoy.loadCartridgeFile(ROM_PATH+"/rom8/rom8.gb")
    
    
def test_rom9():
    gameBoy = GameBoy()
    gameBoy.loadCartridgeFile(ROM_PATH+"/rom9/rom9.gb")