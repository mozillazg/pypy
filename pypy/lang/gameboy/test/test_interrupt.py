
from pypy.lang.gameboy.interrupt import *
from pypy.lang.gameboy import constants

def get_interrupt():
    return Interrupt()



def test_reset():
    interrupt = get_interrupt()
    assert interrupt.enable == 0
    assert interrupt.get_interrupt_flag()  == 0xE0 | constants.VBLANK
    interrupt.enable = 1
    interrupt.flag = ~constants.VBLANK
    interrupt.reset()
    assert interrupt.enable == 0
    assert interrupt.get_interrupt_flag()  == 0xE0 | constants.VBLANK
    
    
def test_is_pending():
    interrupt = get_interrupt()
    assert interrupt.is_pending() == False
    assert interrupt.is_pending(0x00) == False
    interrupt.set_interrupt_enable(True)
    assert interrupt.is_pending()
    
    
def test_is_pending_common_masks():
    interrupt = get_interrupt()
    for flag in interrupt.interrupt_flags:
        interrupt.reset()
        interrupt.enable = True
        assert interrupt.v_blank.is_pending()
        flag.set_pending(True)
        assert interrupt.is_pending(flag.mask)
        
    
def test_raise_lower_interrupt():
    interrupt = get_interrupt()
    masks= [constants.LCD, constants.TIMER, 
            constants.JOYPAD, constants.SERIAL]
    interrupt.set_interrupt_enable(True)
    interrupt.v_blank.set_pending(True)
    for mask in masks:
        interrupt.raise_interrupt(mask)
        assert interrupt.mask_mapping[mask].is_pending() == True
        assert interrupt.is_pending(mask) == True
        interrupt.lower(mask)
        assert interrupt.is_pending(mask) == False
    
def test_read_write():
    interrupt = get_interrupt()
    value = 1
    interrupt.write(constants.IE, value)
    assert interrupt.enable == value
    assert interrupt.read(constants.IE) == value
    
    interrupt.reset()
    value = constants.LCD
    interrupt.write(constants.IF, value)
    assert interrupt.get_interrupt_flag() == 0xE0 | value
    assert interrupt.read(constants.IF) == 0xE0 | value
