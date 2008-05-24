
from pypy.lang.gameboy.cartridge import *
from pypy.lang.gameboy.timer import Clock
from pypy.lang.gameboy import constants
import py
import pdb

def get_clock_driver():
    return Clock()

RAM_SIZE = 3
ROM_SIZE = 2

def get_ram(size=RAM_SIZE):
    return [0] * size * constants.RAM_BANK_SIZE

def get_rom(size=ROM_SIZE):
    return [0xFF] * size * constants.ROM_BANK_SIZE

def fail_ini_test(caller, ram_size, rom_size):
    try:
        caller(ram_size, rom_size)
        py.test.fail("invalid ram/rom bounds check")
    except:
        pass
 
 
 
def basic_read_write_test(mbc, lower, upper):
    write_bounds_test(mbc, lower, upper)
    read_bounds_test(mbc, lower, upper)
    
def write_bounds_test(mbc, lower, upper):
    value = 0
    try:
        mbc.write(lower-1, value)
        py.test.fail("lower bound check failed")
    except:
        pass
    for address in range(lower, upper):
        mbc.write(address, value % 0xFF)
        value += 1
    try:
        mbc.write(upper+1, value)
        py.test.fail("lower upper check failed")
    except:
        pass
    
def read_bounds_test(mbc, lower, upper):
    value = 0
    try:
        mbc.read(lower-1)
        py.test.fail("lower bound check failed")
    except:
        pass
    for address in range(lower, upper, 1):
        assert mbc.read(address) != None
    try:
        mbc.read(upper+1)
        py.test.fail("lower upper check failed")
    except:
        pass
    
def write_ram_enable_test(mbc):
    value = 0
    for address in range(0x1FFF+1):
        mbc.write(address, 0x0A)
        assert mbc.ram_enable == True
        mbc.write(address, 0x00)
        assert mbc.ram_enable == False
    

# -----------------------------------------------------------------------------

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
 
def test_mbc_basic_read_write_test(mbc=None):  
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

def test_default_mbc_read_write():
    py.test.skip("buggy implementation of DefaultMBC")
    mbc = get_default_mbc()
    for i in range(0xFFFF):
        mbc.write(i, i)
        assert mbc.read(i) == i

def test_default_mbc_write():
    py.test.skip("not yet implemented")
    mbc = get_default_mbc()
    
# -----------------------------------------------------------------------------

def get_mbc1(rom_size=128, ram_size=4):
    return MBC1(get_rom(rom_size), get_ram(ram_size), get_clock_driver())

def test_mbc1():
    mbc1 = get_mbc1()
    assert mbc1.rom_bank == constants.ROM_BANK_SIZE
    assert mbc1.memory_model == 0
    assert mbc1.ram_enable == False
    assert mbc1.ram_bank == 0
    fail_ini_test(get_mbc1, 128, 5)
    fail_ini_test(get_mbc1, 128, -1)
    fail_ini_test(get_mbc1, 1, 4)
    fail_ini_test(get_mbc1, 129, 4)
    
    basic_read_write_test(mbc1, 0, 0x7FFF)
    
def test_mbc1_write_ram_enable():
    write_ram_enable_test(get_mbc1())
        
def test_mbc_write_rom_bank_test1():
    mbc= get_mbc1()
    value = 1   
    for address in range(0x2000, 0x3FFF+1):
        mbc.memory_model = 0
        rom_bank = mbc.rom_bank
        mbc.write(address, value)
        assert mbc.rom_bank == ((rom_bank & 0x180000) + \
                                ((value & 0x1F) << 14)) & mbc.rom_size
        mbc.memory_model = 10
        mbc.write(address, value)
        assert mbc.rom_bank == ((value & 0x1F) << 14) & mbc.rom_size
        value = (value+1) % (0x1F-1) +1
        
def test_mbc1_write_rom_bank_test2():
    mbc = get_mbc1()        
    value = 1   
    for address in range(0x4000, 0x5FFF+1):
        mbc.memory_model = 0
        rom_bank = mbc.rom_bank
        mbc.write(address, value)
        assert mbc.rom_bank == ((mbc.rom_bank & 0x07FFFF) + \
                                ((value & 0x03) << 19))  & mbc.rom_size;
        mbc.memory_model = 10
        mbc.write(address, value)
        assert mbc.ram_bank == ((value & 0x03) << 13) & mbc.ram_size
        value += 1
        value %= 0xFF 
        
def test_mbc1_read_memory_model():
    mbc = get_mbc1()       
    value = 1   
    for address in range(0x6000, 0x7FFF+1):
        mbc.write(address, value)
        assert mbc.memory_model == (value & 0x01)
        value += 1
        value %= 0xFF
        
def test_mbc1_read_write_ram():
    mbc = get_mbc1()        
    value = 1
    mbc.ram_enable = True
    for address in range(0xA000, 0xBFFF+1):
        mbc.write(address, value)
        #pdb.runcall(mbc.write, address, value)
        assert mbc.ram[mbc.ram_bank + (address & 0x1FFF)] == value
        assert mbc.read(address) == value;
        value += 1
        value %= 0xFF 

# -----------------------------------------------------------------------------

def get_mbc2(rom_size=16, ram_size=1):
    return MBC2(get_rom(rom_size), get_ram(ram_size), get_clock_driver())

def test_mbc2_create():
    mbc2 = get_mbc2()
    fail_ini_test(mbc2, 2, 0)
    fail_ini_test(mbc2, 2, 2)
    fail_ini_test(mbc2, 1, 1)
    fail_ini_test(mbc2, 17, 1)
    # only to the upper border of mbc
    basic_read_write_test(mbc2, 0, 0x7FFF)
    
    
def test_mbc2_write_ram_enable():
    mbc = get_mbc2()
    value = 0
    for address in range(0x1FFF+1):
        mbc.ram_enable = -1
        mbc.write(address, 0x0A)
        if (address & 0x0100) == 0: 
            assert mbc.ram_enable == True
            mbc.write(address, 0x00)
            assert mbc.ram_enable == False
        else:
            assert mbc.ram_enable == -1
        
def test_mbc2_write_rom_bank_test1():
    mbc = get_mbc2()
    value = 1   
    for address in range(0x2000, 0x3FFF+1):
        mbc.rom_bank = -1
        mbc.write(address, value)
        if (address & 0x0100) != 0:
            assert mbc.rom_bank == ((value & 0x0F) << 14) & mbc.rom_size
        else:
            assert mbc.rom_bank == -1
        value = (value + 1) % (0x0F-1) + 1 
        
def test_mbc2_read_write_ram():
    mbc = get_mbc2()        
    value = 1
    mbc.ram_enable = True
    for address in range(0xA000, 0xA1FF+1):
        mbc.write(address, value)
        assert mbc.ram[(address & 0x01FF)] == value & 0x0F
        assert mbc.read(address) == value;
        value += 1
        value %= 0x0F 
    
# -----------------------------------------------------------------------------
    
def get_mbc3(rom_size=128, ram_size=4):
    return MBC3(get_rom(rom_size), get_ram(ram_size), get_clock_driver())

def test_mbc3_create():
    mbc3 = get_mbc3()
    fail_ini_test(mbc3, 128, -1)
    fail_ini_test(mbc3, 128, 5)
    fail_ini_test(mbc3, 1, 4)
    fail_ini_test(mbc3, 129, 4)
    basic_read_write_test(mbc3, 0, 0x7FFF)
    
def test_mbc3_write_ram_enable():
    write_ram_enable_test(get_mbc3())
        
def test_mbc3_write_rom_bank():
    mbc= get_mbc3()
    value = 1   
    for address in range(0x2000, 0x3FFF+1):
        mbc.memory_model = 0
        rom_bank = mbc.rom_bank
        mbc.write(address, value)
        if value == 0:
            assert mbc.rom_bank == ((1 & 0x7F) << 14) & mbc.rom_size
        else:
            assert mbc.rom_bank == ((value & 0x7F) << 14) & mbc.rom_size
        value += 1
        value %= 0xFF
        
def test_mbc3_write_ram_bank():
    mbc = get_mbc3()        
    value = 1   
    for address in range(0x4000, 0x5FFF+1):
        mbc.memory_model = 0
        mbc.write(address, value)
        if value >= 0 and value <= 0x03:
            assert mbc.ram_bank == (value << 13) & mbc.ram_size
        else:
           assert mbc.ram_bank == -1;
           assert mbc.clock_register == value
        value += 1
        value %= 0xFF 
        
def test_mbc3_write_clock_latch():
    mbc = get_mbc3()       
    value = 1   
    for address in range(0x6000, 0x7FFF+1):
        mbc.write(address, value)
        if value == 0 or value == 1:    
            assert mbc.clock_latch == value
        if value == 1:
            # clock update check...
            pass
        value += 1
        value %= 0xFF
        
def test_mbc3_read_write_ram():
    mbc = get_mbc3()        
    value = 1
    mbc.ram_enable = True
    for address in range(0xA000, 0xBFFF+1):
        mbc.write(address, value)
        #pdb.runcall(mbc.write, address, value)
        assert mbc.ram[mbc.ram_bank + (address & 0x1FFF)] == value
        assert mbc.read(address) == value;
        value += 1
        value %= 0xFF
        
def test_mbc3_read_write_clock():
    mbc = get_mbc3()        
    value = 1
    mbc.ram_enable = True
    mbc.ram_bank = -1
    old_clock_value = -2
    for address in range(0xA000, 0xBFFF+1):
        mbc.clock_register = 0x08
        mbc.write(address, value)
        assert mbc.clock_seconds == value
        
        mbc.clock_register = 0x09
        mbc.write(address, value)
        assert mbc.clock_minutes == value
        
        mbc.clock_register = 0x0A
        mbc.write(address, value)
        assert mbc.clock_hours == value
        
        mbc.clock_register = 0x0B
        mbc.write(address, value)
        assert mbc.clock_days == value
        
        mbc.clock_register = 0x0C
        clock_control = mbc.clock_control
        mbc.write(address, value)
        assert mbc.clock_control == ((clock_control & 0x80) | value)
        
        value += 1
        value %= 0xFF

def test_mbc3_update_clock():
    py.test.skip("not yet implemented")
    mbc = get_mbc3()
    
    
def test_mbc3_latch_clock():
    py.test.skip("not yet implemented")
    mbc = get_mbc3()
    
    
# -----------------------------------------------------------------------------

def get_mbc5(rom_size=512, ram_size=16):
    return MBC5(get_rom(rom_size), get_ram(ram_size), get_clock_driver())

def test_mbc5_create():
    get_mbc5()
    fail_ini_test(get_mbc5, 512, -1)
    fail_ini_test(get_mbc5, 512, 17)
    fail_ini_test(get_mbc5, 1, 16)
    fail_ini_test(get_mbc5, 513, 16)
    
def test_mbc5_read():
    py.test.skip("not yet implemented")
    mbc5 = get_mbc5()

def test_mbc5_write():
    py.test.skip("not yet implemented")
    mbc5 = get_mbc5()

# -----------------------------------------------------------------------------

def get_huc1(rom_size=128, ram_size=4):
    return HuC1(get_rom(rom_size), get_ram(ram_size), get_clock_driver())

def test_huc1_create():
    get_huc1()
    fail_ini_test(get_huc1, 128, 5)
    fail_ini_test(get_huc1, 128, -1)
    fail_ini_test(get_huc1, 1, 4)
    fail_ini_test(get_huc1, 129, 4)
    
def test_huc1_read():
    py.test.skip("not yet implemented")
    huc1 = get_huc1()

def test_huc1_write():
    py.test.skip("not yet implemented")
    huc1 = get_huc1()    

# -----------------------------------------------------------------------------

def get_huc3(rom_size=128, ram_size=4):
    return HuC3(get_rom(rom_size), get_ram(ram_size), get_clock_driver())

def test_huc1_create():
    get_huc3()
    fail_ini_test(get_huc3, 128, 5)
    fail_ini_test(get_huc3, 128, -1)
    fail_ini_test(get_huc3, 1, 4)
    fail_ini_test(get_huc3, 129, 4)

def test_huc3_read():
    py.test.skip("not yet implemented")
    huc3 = get_huc3()

def test_huc3_write():
    py.test.skip("not yet implemented")
    huc3 = get_huc3()

# -----------------------------------------------------------------------------

