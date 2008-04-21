
import py
from pypy.lang.gameboy import constants
from pypy.lang.gameboy.cartridge import *

# ------------------------------------------------------------------------------

def mapToByte(value):
        return ord(value) & 0xFF

ROM_PATH = str(py.magic.autopath().dirpath().dirpath())+"/rom"
CONTENT = "abcdefghijklmnopqrstuvwxyz1234567890"
MAPPED_CONTENT = map(mapToByte, CONTENT)

# ------------------------------------------------------------------------------

def get_cartridge_managers():
    pass

def get_cartridge():
    ctrg = Cartridge()
    return ctrg

class File(object):
    def __init__(self, data):
        self.data = data
        
    def read(self, size=0):
        if size == 0:
            return self.data
        
    def write(self, data):
        self.data = data
        
    def seek(self, value):
        pass

# ------------------------------------------------------------------------------


# STORE MANAGER TEST -----------------------------------------------------------

def test_cartridge_init(): 
    cartridge = get_cartridge()
    
    assert cartridge.cartridgeName == ""
    assert cartridge.cartridgeFilePath == ""
    assert cartridge.cartridgeFile == None
    
    assert cartridge.batteryName == ""
    assert cartridge.batteryFilePath == ""
    assert cartridge.batteryFile == None
    

def rest_cartridge_load():
    cartridge = get_cartridge()
    romName = "rom1.raw"
    romFilePath = ROM_PATH+"/rom1/"+romName
    
    cartridge.load(romFilePath)
    assert cartridge.cartridgeName == romName
    assert cartridge.cartridgeFilePath == romFilePath
    assert cartridge.cartridgeFile != None
    
    assert cartridge.batteryName == romFile+constants.BATTERY_FILE_EXTENSION
    assert cartridge.batteryFilePath ==  romFilePath+constants.BATTERY_FILE_EXTENSION
    assert cartridge.hasBattery() == False
    assert cartridge.batteryFile == None
    
    
def test_cartridge_hasBattery():
    cartridge = get_cartridge()
    
    romName = "rom1.raw"
    romFilePath = ROM_PATH+"/rom1/"+romName
    
    cartridge.load(romFilePath)
    assert cartridge.hasBattery() == False
    
    
def test_cartridge_read():
    cartridge = get_cartridge()
    cartridge.cartridgeFile = File(CONTENT)
    
    assert cartridge.read() == MAPPED_CONTENT
    
    
def test_cartridge_remove_write_read_Battery():
    cartridge = get_cartridge()
    
    romName = "rom1.raw"
    romFilePath = ROM_PATH + "/rom1/"+romName
    
    cartridge.load(romFilePath)
    cartridge.removeBattery()
    assert cartridge.hasBattery() == False
    
    cartridge.writeBattery(MAPPED_CONTENT)
    assert cartridge.hasBattery() == True
    print cartridge.batteryFile
    assert cartridge.batteryFile.read() == CONTENT
    assert cartridge.readBattery() == MAPPED_CONTENT
    
    cartridge.removeBattery()
    assert cartridge.hasBattery() == False
    
    
    
    