from pypy.lang.gameboy import constants


class InterruptFlag(object):
    
    def __init__(self, _reset, mask, callCode):
        self._reset = _reset
        self.mask = mask
        self.callCode = callCode
        self.reset()
        
    def reset(self):
        self.isPending = self._reset
        
    def is_pending(self):
        return self.isPending
    
    def set_pending(self, isPending=True):
        self.isPending = isPending
    

class Interrupt(object):
    """
    PyBoy GameBoy (TM) Emulator
    
    Interrupt Controller
    """
    
    def __init__(self):
        self.create_interrupt_flags()
        self.createvflag_list()
        self.create_flag_mask_mapping()
        self.reset()
        
    def create_interrupt_flags(self):
        self.vBlank = InterruptFlag(True, constants.VBLANK, 0x40)
        self.lcd = InterruptFlag(False, constants.LCD, 0x48)
        self.timer = InterruptFlag(False, constants.TIMER, 0x50)
        self.serial = InterruptFlag(False, constants.SERIAL, 0x58)
        self.joypad = InterruptFlag(False, constants.JOYPAD, 0x60)
        
    def createvflag_list(self):
        self.interruptFlags = [
            self.vBlank, self.lcd, 
            self.timer, self.serial,
            self.joypad
        ]

    def create_flag_mask_mapping(self):
        self.maskMapping = {}
        for flag in self.interruptFlags:
            self.maskMapping[flag.mask] = flag
        
    def reset(self):
        self.enable = False
        for flag in self.interruptFlags:
            flag.reset()

    def is_pending(self, mask=None):
        if not self.enable:
            return False
        if mask==None:
            return self.vBlank.is_pending()
        elif self.vBlank.is_pending():
            return self.maskMapping[mask].is_pending()
        else:
            return False

    def raise_interrupt(self, mask):
        self.maskMapping[mask].set_pending(True)

    def lower(self, mask):
        self.maskMapping[mask].set_pending(False)

    def write(self, address, data):
        if  address == constants.IE:
            self.set_interrupt_enable(data)
        elif address == constants.IF:
            self.set_fnterrupt_flag(data)

    def read(self, address):
        if  address == constants.IE:
            return self.get_interrupt_enable()
        elif address == constants.IF:
            return self.get_interrupt_flag()
        return 0xFF

    def get_interrupt_enable(self):
        return int(self.enable)

    def set_interrupt_enable(self, isEnabled=True):
        self.enable = bool(isEnabled)
        
    def get_interrupt_flag(self):
        flag = 0x00
        for interruptFlag in self.interruptFlags:
            if interruptFlag.is_pending():
                flag |= interruptFlag.mask
        return 0xE0 | flag

    def set_fnterrupt_flag(self, data):
        for flag in self.interruptFlags:
            if (data & flag.mask) != 0:
                flag.set_pending(True)
            else:
                flag.set_pending(False)
