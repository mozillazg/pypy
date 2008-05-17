
import py
from pypy.lang.gameboy import constants
from pypy.lang.gameboy.cartridge import *

# ------------------------------------------------------------------------------

def mapToByte(value):
        return ord(value) & 0xFF

ROM_PATH = str(py.magic.autopath().dirpath().dirpath())+"/rom"
CONTENT = "abcdefghijklmnopqrstuvwxyz1234567890"

MAPPED_CONTENT = map_to_byte(CONTENT)

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
    
    assert cartridge.cartridge_name is ""
    assert cartridge.cartridge_stream is None
    assert cartridge.cartridge_file_contents is None
    
    assert cartridge.battery_name is ""
    assert cartridge.battery_stream is None
    assert cartridge.battery_file_contents is None
    

def rest_cartridge_load():
    cartridge = get_cartridge()
    romName = "rom1.raw"
    romFilePath = ROM_PATH+"/rom1/"+romName
    
    cartridge.load(romFilePath)
    #assert cartridge.cartridge_name == romName
    assert cartridge.cartridge_file_path == romFilePath
    
    assert cartridge.battery_name == romFile+constants.BATTERY_FILE_EXTENSION
    assert cartridge.battery_file_path ==  romFilePath+constants.BATTERY_FILE_EXTENSION
    assert cartridge.has_battery() == False
    
    
def test_cartridge_hasBattery():
    cartridge = get_cartridge()
    
    romName = "rom1.raw"
    romFilePath = ROM_PATH+"/rom1/"+romName
    
    cartridge.load(romFilePath)
    assert cartridge.has_battery() == False
    
    
def test_cartridge_read():
    cartridge = get_cartridge()
    assert cartridge.read() == None
    
    
def test_cartridge_remove_write_read_Battery():
    cartridge = get_cartridge()
    
    romName = "rom1.raw"
    romFilePath = ROM_PATH + "/rom1/"+romName
    
    cartridge.load(romFilePath)
    cartridge.remove_battery()
    assert cartridge.has_battery() == False
    
    cartridge.write_battery(MAPPED_CONTENT)
    assert cartridge.has_battery() == True
    assert cartridge.read_battery() == MAPPED_CONTENT
    
    cartridge.remove_battery()
    assert cartridge.has_battery() == False
    
    
    
    