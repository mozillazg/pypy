
from pypy.lang.gameboy.interrupt import *
from pypy.lang.gameboy import constants

def get_interrupt():
    return Interrupt()



def test_rest():
    interrupt = get_interrupt()
    assert interrupt.enable == 0
    assert interrupt.flag  == constants.VBLANK
    interrupt.enable = 1
    interrupt.flag = ~constants.VBLANK
    interrupt.reset()
    assert interrupt.enable == 0
    assert interrupt.flag  == constants.VBLANK
    
    
def test_is_pending():
    interrupt = get_interrupt()
    assert interrupt.isPending() == False
    assert interrupt.isPending(0x00) == False
    interrupt.setInterruptEnable(True)
    assert interrupt.isPending() == True
    
    
def test_raise_interrupt():
    interrupt = get_interrupt()
    value = 0x12
    mask = 0xAA
    interrupt.flag = value
    assert interrupt.flag == value
    interrupt.raiseInterrupt(mask)
    assert interrupt.flag == value|mask
    
def test_lower():
    interrupt = get_interrupt()
    value = 0x12
    mask = 0xAA
    interrupt.flag = value
    assert interrupt.flag == value
    interrupt.lower(mask)
    assert interrupt.flag == value & (~mask)
    
def test_read_write():
    interrupt = get_interrupt()
    value = 0x12
    interrupt.write(constants.IE, value)
    assert interrupt.enable == value
    assert interrupt.read(constants.IE) == value
    value+=1
    interrupt.write(constants.IF, value)
    assert interrupt.flag == value
    assert interrupt.read(constants.IF) == 0xE0 | value
