import py
from pypy.lang.gameboy.timer import *
from pypy.lang.gameboy.interrupt import *
from pypy.lang.gameboy import constants


def get_timer():
    return Timer(Interrupt())

    
# ------------------------------------------------------------------------------


def test_reset(timer=None):
    if timer is None:
        timer = get_timer()
    assert timer.div == 0
    assert timer.divider_cycles == constants.DIV_CLOCK
    assert timer.tima == 0
    assert timer.tma == 0
    assert timer.tac == 0
    assert timer.timer_cycles == constants.TIMER_CLOCK[0]
    assert timer.timer_clock == constants.TIMER_CLOCK[0]
    
    
def test_read_write():
    timer = get_timer()
    timer.div = 10
    value = 0x11
    timer.write(constants.DIV, value)
    assert timer.get_divider() == 0
    assert timer.read(constants.DIV) == 0
    
    timer.reset()
    timer.write(constants.TIMA, value)
    assert timer.get_timer_counter() == value
    assert timer.read(constants.TIMA) == value
    timer.reset()
    
    timer.write(constants.TMA, value)
    assert timer.get_timer_modulo() == value
    assert timer.read(constants.TMA) == value
    timer.reset()
    
    
def test_get_timer_control():
    timer = get_timer()
    value = 0x12
    timer.write(constants.TAC, value)
    assert timer.get_timer_control() == 0xF8 | value 
    assert timer.read(constants.TAC) == 0xF8 |value

def test_set_timer_control():
    timer = get_timer()
    value = 0x12
    timer.set_timer_control(value)
    assert timer.tac == value
    assert timer.timer_cycles == constants.TIMER_CLOCK[value & 0x03]
    assert timer.timer_clock  == constants.TIMER_CLOCK[value & 0x03]
    timer.reset()
    timer.tac = value+1
    timer.timer_clock = 0
    timer.timer_cycles = 0
    timer.set_timer_control(value+1)
    assert timer.tac == value+1
    assert timer.timer_clock == 0
    assert timer.timer_clock == 0
    
def test_read_write_Divider():
    timer = get_timer()
    value = 0x12
    timer.div = value
    assert timer.get_divider() == timer.div
    # divider resets on write
    timer.set_divider(value)
    assert timer.get_divider() == 0
    
def test_cycles():
    timer = get_timer()
    value = 10
    timer.divider_cycles = value
    assert timer.get_cycles() == timer.divider_cycles
    timer.tac = 0x04
    timer.timer_cycles = value-1
    timer.timer_cycles = value
    assert timer.get_cycles() == timer.timer_cycles
    
def test_emulateDivider_normal():
    timer = get_timer()
    value = 2
    timer.timer_cycles = 0
    timer.emulate_timer(value)
    
def test_test_emulateDivider_zero():
    timer = get_timer()
    value = 2
    timer.timer_cycles = value
    timer.emulate_timer(value)
    assert timer.timer_cycles == value
    
def test_emulate_timer_tac_return():
    timer = get_timer()
    timer.tac = 0
    timer.timer_cycles = -10
    cycles = timer.timer_cycles
    timer.emulate_timer(10)
    assert timer.timer_cycles == cycles
    
def test_emulate_timer_timer_cycles_return():
    timer = get_timer()
    timer.tac = 0x04
    value = 10
    timer.timer_cycles = value+1
    cycles = timer.timer_cycles
    timer.emulate_timer(value)
    assert timer.timer_cycles == 1
    
    timer = get_timer()
    timer.tac = 0x04
    
    
def test_emulate_timer_interrupt():
    timer = get_timer()
    ticks = 0
    timer.tac = 0x04
    timer.tima = -1
    # raise an interupt as we pass 0
    assert timer.interrupt.is_pending(constants.TIMER) == False
    assert timer.interrupt.timer.is_pending() == False
    timer.timer_cycles = -timer.timer_clock+1
    timer.emulate_timer(ticks)
    assert timer.timer_cycles == 1
    assert timer.tima == timer.tma
    assert timer.interrupt.timer.is_pending()
    
    