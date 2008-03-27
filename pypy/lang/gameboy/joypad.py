
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
        self.joyp = 0xF
        self.buttons = 0xF
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
            self.joyp = (self.joyp & 0xC) + (data & 0x3)
            self.update()

    def read(self, address):
        if (address == constants.JOYP):
            return (self.joyp << 4) + self.buttons
        return 0xFF

    def update(self):
        oldButtons = self.buttons
        if self.joyp == 0x1:
            self.buttons = self.driver.getButtons()
        elif self.joyp == 0x2:
            self.buttons = self.driver.getDirections()
        else:
            self.buttons  = 0xF

        if oldButtons != self.buttons:
            self.interrupt.raiseInterrupt(constants.JOYPAD)



class JoypadDriver(object):
    """
    Maps the Input to the Button and Direction Codes
    """
    def __init__(self):
        self.raised = False
        self.buttons = 0xF
        self.directions = 0xF
        
    def getButtons(self):
        return self.buttons
    
    def getDirections(self):
        return self.directions
    
    def isRaised(self):
        return self.raised