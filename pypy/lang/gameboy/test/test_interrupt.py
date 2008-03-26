
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
    
def test_lower():
    interrupt = get_interrupt()
    
def test_write():
    interrupt = get_interrupt()
    
def test_read():
    interrupt = get_interrupt()
    
def test_interrupt_enable():
    interrupt = get_interrupt()
    
    
def test_interrupt_flag():
    interrupt = get_interrupt()
    