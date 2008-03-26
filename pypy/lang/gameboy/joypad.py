
from pypy.lang.gameboy import constants

class Joypad(object):
    """
    PyBoy GameBoy (TM) Emulator
     
    Joypad Input
    """

    def __init__(self, joypadDriver, interrupt):
        self.driver = joypadDriver
        self.interrupt = interrupt
        self.reset()

    def reset(self):
        self.joyp = 0xFF
        self.cycles = constants.JOYPAD_CLOCK

    def cycles(self):
        return self.cycles

    def emulate(self, ticks):
        self.cycles -= ticks
        if (self.cycles <= 0):
            if (self.driver.isRaised()):
                self.update()
            self.cycles = constants.JOYPAD_CLOCK

    def write(self, address, data):
        if (address == constants.JOYP):
            self.joyp = (self.joyp & 0xCF) + (data & 0x30)
            self.update()

    def read(self, address):
        if (address == constants.JOYP):
            return self.joyp
        return 0xFF

    def update(self):
        data = self.joyp & 0xF0

        switch = (data & 0x30)
        if switch==0x10:
            data |= self.driver.getButtons()
        elif switch==0x20:
            data |= self.driver.getDirections()
        elif switch==0x30:
            data |= 0x0F

        if ((self.joyp & ~data & 0x0F) != 0):
            self.interrupt.raiseInterrupt(constants.JOYPAD)

        self.joyp = data



class Driver(object):
    
    def getButtons(self):
        pass
    
    def getDirections(self):
        pass