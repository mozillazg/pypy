from pypy.lang.gameboy import constants
from pypy.lang.gameboy.ram import iMemory


class InterruptFlag(object):
    
    def __init__(self, _reset, mask, call_code):
        self._reset = _reset
        self.mask = mask
        self.call_code = call_code
        self.reset()
        
    def reset(self):
        self._is_pending = self._reset
        
    def is_pending(self):
        return self._is_pending
    
    def set_pending(self, _is_pending=True):
        self._is_pending = _is_pending
    

class Interrupt(iMemory):
    """
    PyBoy GameBoy (TM) Emulator
    
    Interrupt Controller
    """
    
    def __init__(self):
        self.create_interrupt_flags()
        self.create_flag_list()
        self.create_flag_mask_mapping()
        self.reset()
        
    def create_interrupt_flags(self):
        self.v_blank = InterruptFlag(True, constants.VBLANK, 0x40)
        self.lcd = InterruptFlag(False, constants.LCD, 0x48)
        self.timer = InterruptFlag(False, constants.TIMER, 0x50)
        self.serial = InterruptFlag(False, constants.SERIAL, 0x58)
        self.joypad = InterruptFlag(False, constants.JOYPAD, 0x60)
        
    def create_flag_list(self):
        self.interrupt_flags = [
            self.v_blank, self.lcd, 
            self.timer, self.serial,
            self.joypad
        ]

    def create_flag_mask_mapping(self):
        self.mask_mapping = {}
        for flag in self.interrupt_flags:
            self.mask_mapping[flag.mask] = flag
        
    def reset(self):
        self.enable = False
        for flag in self.interrupt_flags:
            flag.reset()

    def is_pending(self, mask=None):
        if not self.enable:
            return False
        if mask==None:
            return self.v_blank.is_pending()
        elif self.v_blank.is_pending():
            return self.mask_mapping[mask].is_pending()
        else:
            return False

    def raise_interrupt(self, mask):
        self.mask_mapping[mask].set_pending(True)

    def lower(self, mask):
        self.mask_mapping[mask].set_pending(False)

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
        for interrupt_flag in self.interrupt_flags:
            if interrupt_flag.is_pending():
                flag |= interrupt_flag.mask
        return 0xE0 | flag

    def set_fnterrupt_flag(self, data):
        for flag in self.interrupt_flags:
            if (data & flag.mask) != 0:
                flag.set_pending(True)
            else:
                flag.set_pending(False)
