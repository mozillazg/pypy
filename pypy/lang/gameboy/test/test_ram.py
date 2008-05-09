from pypy.lang.gameboy import constants
from pypy.lang.gameboy.ram import RAM


def get_ram():
    return RAM()


def test_ram_read_write():
    ram = get_ram()
    address = 0x00
    value = 0x12
    ram.write(address, value)
    assert ram.read(address) == 0xFF
    assert value not in ram.w_ram
    assert value not in ram.h_ram
    
    address = 0xC000
    ram.write(address, value)
    assert ram.read(address) == value
    assert value in  ram.w_ram
    assert value not in  ram.h_ram
    
    address = 0xFDFF
    value += 1
    ram.write(address, value)
    assert ram.read(address) == value
    assert value in  ram.w_ram
    assert value not in  ram.h_ram
    
    
    address = 0xFF80
    value += 1
    ram.write(address, value)
    assert ram.read(address) == value
    assert value in  ram.h_ram
    assert value not in  ram.w_ram
    
    address = 0xFFFE
    value += 1
    ram.write(address, value)
    assert ram.read(address) == value
    assert value in  ram.h_ram
    assert value not in  ram.w_ram
    
    address += 1
    value += 1
    ram.write(address, value)
    assert ram.read(address) == 0xFF
    assert value not in  ram.h_ram
    assert value not in  ram.w_ram