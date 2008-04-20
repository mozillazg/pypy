
import py
from pypy.lang.gameboy.cartridge import *


ROM_PATH = py.magic.autopath().dirpath().dirpath()+"/rom"


# ------------------------------------------------------------------------------

def get_cartridge_managers():
    pass

def get_cartridge():
    return Cartridge()



# ------------------------------------------------------------------------------


# STORE MANAGER TEST -----------------------------------------------------------
def test_store_manager_init(): 
    cartridge = get_cartridge_managers()
