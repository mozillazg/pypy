from pypy.lang.gameboy import constants
from pypy.lang.gameboy.ram import iMemory


class InterruptFlag(object):
    
    def __init__(self, _reset, mask, call_code):
        self._reset    = _reset
        self.mask      = mask
        self.call_code = call_code
        self.reset()
        
    def reset(self):
        self._is_pending = self._reset
        self.enabled     = False
        
    def is_pending(self):
        return self._is_pending
    
    def set_pending(self, _is_pending=True):
        self._is_pending = _is_pending
        
    def is_enabled(self):
        return self.enabled

    def set_enabled(self, enabled):
        self.enabled = enabled
    
# --------------------------------------------------------------------

class Interrupt(iMemory):
    """
    PyGirl GameBoy (TM) Emulator
    Interrupt Controller
    """
    
    def __init__(self):
        self.create_interrupt_flags()
        self.create_flag_list()
        self.create_flag_mask_mapping()
        self.reset()
        
    def create_interrupt_flags(self):
        self.vblank  = InterruptFlag(True,  constants.VBLANK, 0x40)
        self.lcd     = InterruptFlag(False, constants.LCD,    0x48)
        self.timer   = InterruptFlag(False, constants.TIMER,  0x50)
        self.serial  = InterruptFlag(False, constants.SERIAL, 0x58)
        self.joypad  = InterruptFlag(False, constants.JOYPAD, 0x60)
        
    def create_flag_list(self):
        self.interrupt_flags = [ self.vblank, self.lcd, self.timer, self.serial,
                                 self.joypad]

    def create_flag_mask_mapping(self):
        self.mask_mapping = {}
        for flag in self.interrupt_flags:
            self.mask_mapping[flag.mask] = flag
        
    def reset(self):
        self.set_enable_mask(0x0)
        for flag in self.interrupt_flags:
            flag.reset()
    
    
    def write(self, address, data):
        if  address == constants.IE:
            self.set_enable_mask(data)
        elif address == constants.IF:
            self.set_fnterrupt_flag(data)

    def read(self, address):
        if  address == constants.IE:
            return self.get_enable_mask()
        elif address == constants.IF:
            return self.get_interrupt_flag()
        return 0xFF
    
    
    def is_pending(self, mask=0xFF):
        return (self.get_enable_mask() & self.get_interrupt_flag() & mask) != 0
    
    def raise_interrupt(self, mask):
        self.mask_mapping[mask].set_pending(True)

    def lower(self, mask):
        self.mask_mapping[mask].set_pending(False)

    def get_enable_mask(self):
        enabled = 0x00
        for interrupt_flag in self.interrupt_flags:
            if interrupt_flag.is_enabled():
                enabled |= interrupt_flag.mask
        return enabled | self.enable_rest_data;

    def set_enable_mask(self, enable_mask):
        for flag in self.interrupt_flags:
            flag.set_enabled((enable_mask & flag.mask) != 0)
        self.enable_rest_data = enable_mask & 0xE0;
        
    
    def get_interrupt_flag(self):
        flag = 0x00
        for interrupt_flag in self.interrupt_flags:
            if interrupt_flag.is_pending():
                flag |= interrupt_flag.mask
        return flag | 0xE0

    def set_fnterrupt_flag(self, data):
        for flag in self.interrupt_flags:
            flag.set_pending((data & flag.mask) != 0)
