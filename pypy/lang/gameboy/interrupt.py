from pypy.lang.gameboy import constants

class Interrupt(object):
    """
    PyBoy GameBoy (TM) Emulator
    
    Interrupt Controller
    """
    
    def __init__(self):
        self.reset()

    def reset(self):
        self.enable = 0
        self.flag = constants.VBLANK

    def isPending(self, mask=None):
        if mask==None:
            return (self.enable & self.flag) != 0
        else:
            return (self.enable & self.flag & mask) != 0

    def raiseInterrupt(self, mask):
        self.flag |= mask

    def lower(self, mask):
        self.flag &= ~mask

    def write(self, address, data):
        if  address == constants.IE:
            self.setInterruptEnable(data)
        elif address == constants.IF:
            self.setInterruptFlag(data)

    def read(self, address):
        if  address == constants.IE:
            return self.getInterruptEnable()
        elif address == constants.IF:
            return self.getInterruptFlag()
        return 0xFF

    def getInterruptEnable(self):
        return self.enable

    def getInterruptFlag(self):
        return 0xE0 | self.flag

    def setInterruptEnable(self, data):
        self.enable = data

    def setInterruptFlag(self, data):
        self.flag = data
