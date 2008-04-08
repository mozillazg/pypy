from pypy.lang.gameboy import constants


class InterruptFlag(object):
    
    def __init__(self, _reset, mask, callCode):
        self._reset = _reset
        self.mask = mask
        self.callCode = callCode
        self.reset()
        
    def reset(self):
        self._isPending = self._reset
        
    def isPending(self):
        return self._isPending
    
    def setPending(self, _isPending=True):
        self._isPending = _isPending
    

class Interrupt(object):
    """
    PyBoy GameBoy (TM) Emulator
    
    Interrupt Controller
    """
    
    def __init__(self):
        self.createInterruptFlags()
        self.createFlagList()
        self.createFlagMaskMapping()
        self.reset()
        
    def createInterruptFlags(self):
        self.vBlank = InterruptFlag(True, constants.VBLANK, 0x40)
        self.lcd = InterruptFlag(False, constants.LCD, 0x48)
        self.timer = InterruptFlag(False, constants.TIMER, 0x50)
        self.serial = InterruptFlag(False, constants.SERIAL, 0x58)
        self.joypad = InterruptFlag(False, constants.JOYPAD, 0x60)
        
    def createFlagList(self):
        self.interruptFlags = [
            self.vBlank, self.lcd, 
            self.timer, self.serial,
            self.joypad
        ]

    def createFlagMaskMapping(self):
        self.maskMapping = {}
        for flag in self.interruptFlags:
            self.maskMapping[flag.mask] = flag
        
    def reset(self):
        self.enable = False
        for flag in self.interruptFlags:
            flag.reset()

    def isPending(self, mask=None):
        if not self.enable:
            return False
        if mask==None:
            return self.vBlank.isPending()
        elif self.vBlank.isPending():
            return self.maskMapping[mask].isPending()
        else:
            return False

    def raiseInterrupt(self, mask):
        self.maskMapping[mask].setPending(True)

    def lower(self, mask):
        self.maskMapping[mask].setPending(False)

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
        return int(self.enable)

    def setInterruptEnable(self, isEnabled=True):
        self.enable = bool(isEnabled)
        
    def getInterruptFlag(self):
        flag = 0x00
        for interruptFlag in self.interruptFlags:
            if interruptFlag.isPending():
                flag |= interruptFlag.mask
        return 0xE0 | flag

    def setInterruptFlag(self, data):
        for flag in self.interruptFlags:
            if (data & flag.mask) != 0:
                flag.setPending(True)
            else:
                flag.setPending(False)
