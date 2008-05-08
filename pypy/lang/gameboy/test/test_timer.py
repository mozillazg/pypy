import py
from pypy.lang.gameboy.timer import *
from pypy.lang.gameboy.interrupt import *
from pypy.lang.gameboy import constants


def get_timer():
    return Timer(Interrupt())

    
# ------------------------------------------------------------------------------


def test_reset(timer=None):
    if timer == None:
        timer = get_timer()
    assert timer.div == 0
    assert timer.dividerCycles == constants.DIV_CLOCK
    assert timer.tima == 0
    assert timer.tma == 0
    assert timer.tac == 0
    assert timer.timerCycles == constants.TIMER_CLOCK[0]
    assert timer.timerClock == constants.TIMER_CLOCK[0]
    
    
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
    assert timer.timerCycles == constants.TIMER_CLOCK[value & 0x03]
    assert timer.timerClock  == constants.TIMER_CLOCK[value & 0x03]
    timer.reset()
    timer.tac = value+1
    timer.timerClock = 0
    timer.timerCycles = 0
    timer.set_timer_control(value+1)
    assert timer.tac == value+1
    assert timer.timerClock == 0
    assert timer.timerClock == 0
    
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
    timer.dividerCycles = value
    assert timer.get_cycles() == timer.dividerCycles
    timer.tac = 0x04
    timer.timerCycles = value-1
    timer.timerCycles = value
    assert timer.get_cycles() == timer.timerCycles
    
def test_emulateDivider_normal():
    timer = get_timer()
    value = 2
    timer.timerCycles = 0
    timer.emulate_timer(value)
    
def test_test_emulateDivider_zero():
    timer = get_timer()
    value = 2
    timer.timerCycles = value
    timer.emulate_timer(value)
    assert timer.timerCycles == value
    
def test_emulate_timer_tac_return():
    timer = get_timer()
    timer.tac = 0
    timer.timerCycles = -10
    cycles = timer.timerCycles
    timer.emulate_timer(10)
    assert timer.timerCycles == cycles
    
def test_emulate_timer_timer_cycles_return():
    timer = get_timer()
    timer.tac = 0x04
    value = 10
    timer.timerCycles = value+1
    cycles = timer.timerCycles
    timer.emulate_timer(value)
    assert timer.timerCycles == 1
    
    timer = get_timer()
    timer.tac = 0x04
    
    
def test_emulate_timer_interrupt():
    timer = get_timer()
    ticks = 0
    timer.tac = 0x04
    timer.tima = -1
    # raise an interupt as we pass 0
    assert timer.interrupt.is_pending(constants.TIMER) == False
    timer.timerCycles = -timer.timerClock+1
    timer.emulate_timer(ticks)
    assert timer.timerCycles == 1
    assert timer.tima == timer.tma
    assert timer.interrupt.timer.is_pending()
    
    