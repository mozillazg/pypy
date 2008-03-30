"""
PyBoy GameBoy (TM) Emulator
 
Timer and Divider
"""
from pypy.lang.gameboy import constants

class Timer(object):

    def __init__(self, interrupt):
        self.interrupt = interrupt
        self.reset()

    def reset(self):
        self.div = 0
        self.dividerCycles = constants.DIV_CLOCK
        self.tima = self.tma = self.tac = 0x00
        self.timerCycles = self.timerClock = constants.TIMER_CLOCK[self.tac & 0x03]

    def write(self,  address, data):
        if address==constants.DIV:
            self.setDivider(data)
        elif address==constants.TIMA:
            self.setTimerCounter(data)
        elif address==constants.TMA:
            self.setTimerModulo(data)
        elif address==constants.TAC:
            self.setTimerControl(data)
    
    def read(self,  address):
        if address==constants.DIV:
            return self.getDivider()
        elif address==constants.TIMA:
            return self.getTimerCounter()
        elif address==constants.TMA:
            return self.getTimerModulo()
        elif address==constants.TAC:
            return self.getTimerControl()
        return 0xFF

    def getDivider(self):
        return self.div
    
    def setDivider(self,  data): #DIV register resets on write
        self.div = 0

    def getTimerCounter(self):
        return self.tima
    
    def setTimerCounter(self,  data):
        self.tima = data

    def getTimerModulo(self):
        return self.tma
    
    def setTimerModulo(self,  data):
        self.tma = data

    def getTimerControl(self):
        return 0xF8 | self.tac

    def setTimerControl(self,  data):
        if ((self.tac & 0x03) != (data & 0x03)):
            self.timerCycles = self.timerClock = constants.TIMER_CLOCK[data & 0x03]
        self.tac = data

    def cycles(self):
        if ((self.tac & 0x04) != 0 and self.timerCycles < self.dividerCycles):
                return self.timerCycles
        return self.dividerCycles

    def emulate(self,  ticks):
        self.emulateDivider(ticks)
        self.emulateTimer(ticks)

    def emulateDivider(self,  ticks):
        self.dividerCycles -= ticks
        while (self.dividerCycles <= 0):
            self.div = (self.div + 1) & 0xFF
            self.dividerCycles += constants.DIV_CLOCK
    
    def emulateTimer(self,  ticks):
        if ((self.tac & 0x04) != 0):
            self.timerCycles -= ticks
            while (self.timerCycles <= 0):
                self.tima = (self.tima + 1) & 0xFF
                self.timerCycles += self.timerClock
                if (self.tima == 0x00):
                    self.tima = self.tma
                    self.interrupt.raiseInterrupt(constants.TIMER)
    
# CLOCK DRIVER -----------------------------------------------------------------

class ClockDriver(object):
    
    def __init__(self):
        pass
    
    def getTime(self):
        return System.currentTimeMillis() / 1000
        
