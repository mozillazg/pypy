from pypy.lang.gameboy.joypad import *
from pypy.lang.gameboy.interrupt import *
from pypy.lang.gameboy import constants


def get_joypad():
    return Joypad(get_driver(), Interrupt())

def get_driver():
    return JoypadDriver()


# ------------------------------------------------------------------------------

def test_reset(joypad=None):
    if joypad == None:
        joypad = get_joypad()
    assert joypad.joyp == 0xF
    assert joypad.cycles == constants.JOYPAD_CLOCK
        
def test_emulate():
    joypad = get_joypad()
    ticks = 2
    cycles = joypad.cycles
    joypad.emulate(ticks)
    assert cycles - joypad.cycles == ticks

def test_emulate_zero_ticks():
    joypad = get_joypad()
    joypad.cycles = 2
    ticks = 2
    joypad.emulate(ticks)
    assert joypad.cycles == constants.JOYPAD_CLOCK
    
def test_emulate_zero_ticks_update():   
    joypad = get_joypad() 
    value = 0x1
    valueButtons = 0x4
    joypad.joyp = value
    joypad.driver.buttons = valueButtons
    joypad.driver.raised = True
    joypad.cycles = 2
    ticks = 2
    joypad.emulate(ticks)
    assert joypad.cycles == constants.JOYPAD_CLOCK
    assert joypad.joyp == value
    assert joypad.buttons == valueButtons
    
def test_read_write():
    joypad = get_joypad()
    value = 0x2
    joypad.write(constants.JOYP, value)
    joyp = 0xC + (value & 0x3)
    assert joypad.joyp == joyp
    joyp = (joyp << 4) + 0xF
    assert joypad.read(constants.JOYP) == joyp
    assert joypad.read(constants.JOYP+1) == 0xFF
    # no change on writing the wrong address
    joypad.write(constants.JOYP+1, value+1)
    assert joypad.read(constants.JOYP) == joyp
    
    
def test_update():
    joypad = get_joypad()
    joypad.driver.buttons = 0x1
    assert joypad.driver.getButtons() == 0x1
    joypad.driver.directions = 0x2
    assert joypad.driver.getDirections() == 0x2
    assert joypad.buttons == 0xF
    joypad.joyp = 0x1
    joypad.update()
    assert joypad.buttons == joypad.driver.buttons
    
    joypad.joyp = 0x2
    joypad.update()
    assert joypad.buttons == joypad.driver.directions
    
    joypad.joyp = 0x3
    joypad.update()
    assert joypad.buttons == 0xF
    