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
    assert value not in ram.wram
    assert value not in ram.hram
    
    address = 0xC000
    ram.write(address, value)
    assert ram.read(address) == value
    assert value in  ram.wram
    assert value not in  ram.hram
    
    address = 0xFDFF
    value += 1
    ram.write(address, value)
    assert ram.read(address) == value
    assert value in  ram.wram
    assert value not in  ram.hram
    
    
    address = 0xFF80
    value += 1
    ram.write(address, value)
    assert ram.read(address) == value
    assert value in  ram.hram
    assert value not in  ram.wram
    
    address = 0xFFFE
    value += 1
    ram.write(address, value)
    assert ram.read(address) == value
    assert value in  ram.hram
    assert value not in  ram.wram
    
    address += 1
    value += 1
    ram.write(address, value)
    assert ram.read(address) == 0xFF
    assert value not in  ram.hram
    assert value not in  ram.wram