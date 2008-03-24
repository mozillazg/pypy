import py
from pypy.lang.gameboy.timer import *
from pypy.lang.gameboy.interrupt import *
from pypy.lang.gameboy import constants


def get_timer():
    return Timer(get_timer_interrupt())

def get_timer_interrupt():
    return Interrupt()
    

    
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
    assert timer.getDivider() == 0
    assert timer.read(constants.DIV) == 0
    
    timer.reset()
    timer.write(constants.TIMA, value)
    assert timer.getTimerCounter() == value
    assert timer.read(constants.TIMA) == value
    timer.reset()
    
    timer.write(constants.TMA, value)
    assert timer.getTimerModulo() == value
    assert timer.read(constants.TMA) == value
    timer.reset()
    
    
    
    
def test_setTimerControl():
    py.test.skip("need to use more information about the timer")
    timer = get_timer()
    value = 0x12
    timer.write(constants.TAC, value)
    assert timer.getTimerControl() == value
    assert timer.read(constants.TAC) == value
    
    
def test_cycles():
    timer = get_timer()
    

def test_emulateDivider():
    timer = get_timer()
    

def test_emulateTimer():
    timer = get_timer()