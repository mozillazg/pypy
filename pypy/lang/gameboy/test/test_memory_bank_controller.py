
from pypy.lang.gameboy.cartridge import *
from pypy.lang.gameboy.timer import Clock
from pypy.lang.gameboy.constants import *
import py

def get_clock_driver():
    return Clock()

RAM_SIZE = 3
ROM_SIZE = 2

def get_ram():
    return [0] * RAM_SIZE * constants.RAM_BANK_SIZE

def get_rom():
    return [0xFF] * ROM_SIZE * constants.ROM_BANK_SIZE


def test_mbc_init():
    try:
        MBC(get_ram(), get_rom(), get_clock_driver())
        py.test.fail("")
    except:
        pass

    try:
        MBC(get_ram(), get_rom(), get_clock_driver(), 0, ROM_SIZE-1, 0,
            RAM_SIZE-1)
        py.test.fail("")
    except:
        pass
    
    try:
        MBC(get_ram(), get_rom(), get_clock_driver(), ROM_SIZE+1, ROM_SIZE+1, 
            RAM_SIZE+1, RAM_SIZE+1)
        py.test.fail("")
    except:
        pass

def test_mbc():
    py.test.skip()
    mbc = MBC(get_ram(), get_rom(), get_clock_driver(),1, 0xF3, 2, 0xF1)
    assert mbc.min_rom_bank_size == 1
    assert mbc.max_rom_bank_size == 0xF3
    assert mbc.min_ram_bank_size == 2
    assert mbc.max_ram_bank_size == 0xF1
    assert mbc.rom_bank == constants.ROM_BANK_SIZE
    assert mbc.ram_bank == 0
    assert mbc.ram_enable == False
    assert mbc.rom_size == ROM_SIZE * constants.ROM_BANK_SIZE - 1
    assert mbc.ram_size == RAM_SIZE * constants.ROM_BANK_SIZE - 1
    assert len(mbc.rom) == ROM_SIZE
    assert len(mbc.ram) == RAM_SIZE
    

def test_mbc_read_write():
    mbc = MBC([0]*0xFFFF,[0]*0xFFFF, get_clock_driver(),1, 0xFFFF, 2, 0xFFFF)
    try:
        mbc.write(0, 0)
        py.test.fail(" MBC has an abstract write")
    except:
        pass
    
    try:
        mbc.read(0x1FFFF+1)
        py.test.fail(" write address to high")
    except:
        pass
 
def test_mbc_read_write_test(mbc=None):  
    if mbc==None:
        mbc = MBC([0]*0xFFFF,[0]*0xFFFF, get_clock_driver(),1, 0xFFFF, 2, 0xFFFF)

    value = 0x12
    mbc.rom[0x3FFF] = value
    assert mbc.read(0x3FFF) == value
    
    mbc.rom[mbc.rom_bank] = value
    assert mbc.read(0x4000) == value
    
    
    mbc.ram[mbc.ram_bank] = value
    mbc.ram_enable = False
    try:
        mbc.read(0xA000)
        py.test.fail("ram is not enabled")
    except:
        pass
    mbc.ram_enable = True
    assert mbc.read(0xA000) == value

# -----------------------------------------------------------------------------

def get_default_mbc():
    return DefaultMBC([0]*0xFFFF, [0]*0xFFFF, get_clock_driver()) 

def test_default_mbc_read():
    py.test.skip("not yet implemented")
    mbc = get_default_mbc()

def test_default_mbc_write():
    py.test.skip("not yet implemented")
    mbc = get_default_mbc()
    
# -----------------------------------------------------------------------------

def get_mbc1():
    return MBC1([0]*0x5FFF,[0]*0xBFFF, get_clock_driver())

def test_mbc1_write():  
    py.test.skip("buggy implementation of MBC1++")
    mbc1 = get_mbc1()
    test_mbc_read_write_test(mbc1)
    
def test_mbc1_read():
    py.test.skip("not yet implemented")
    mbc1 = get_mbc1()
    # the same as in mbc
    pass

# -----------------------------------------------------------------------------

def get_mbc2():
    return MBC2([0]*0x5FFF,[0]*0xBFFF, get_clock_driver())

def test_mbc2_read_write():
    py.test.skip("not yet implemented")
    mbc2 = get_mbc2()
    

def test_mbc2_write():
    py.test.skip("not yet implemented")
    mbc2 = get_mbc2()
    
# -----------------------------------------------------------------------------

def get_mbc3():
    return MBC3([0]*0x5FFF,[0]*0xBFFF, get_clock_driver())

def test_mbc3_read():
    py.test.skip("not yet implemented")
    mbc3 = get_mbc3()

def test_mbc3_write():
    py.test.skip("not yet implemented")
    mbc3 = get_mbc3()
    
# -----------------------------------------------------------------------------

def get_mbc5():
    return MBC5([0]*0x5FFF,[0]*0xBFFF, get_clock_driver())
    
def test_mbc5_read():
    py.test.skip("not yet implemented")
    mbc5 = get_mbc5()

def test_mbc5_write():
    py.test.skip("not yet implemented")
    mbc5 = get_mbc5()

# -----------------------------------------------------------------------------

def get_huc1():
    return HuC1([0]*0x5FFF,[0]*0xBFFF, get_clock_driver())
    
def test_huc1_read():
    py.test.skip("not yet implemented")
    huc1 = get_huc1()

def test_huc1_write():
    py.test.skip("not yet implemented")
    huc1 = get_huc1()    

# -----------------------------------------------------------------------------

def get_huc3():
    return HuC3([0]*0x5FFF,[0]*0xBFFF, get_clock_driver())

def test_huc3_read():
    py.test.skip("not yet implemented")
    huc3 = get_huc3()

def test_huc3_write():
    py.test.skip("not yet implemented")
    huc3 = get_huc3()

# -----------------------------------------------------------------------------

