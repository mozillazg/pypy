"""
PyBoy GameBoy (TM) Emulator

Work and High RAM
"""

from pypy.lang.gameboy import constants

class RAM(object):
    
    # Work RAM
    wram = []

    # High RAM
    hram = []

    def __init__(self):
        self.reset()

    def reset(self):
        self.wram =  [0x00]*8192
        self.hram =  [0x00]*128

    def write(self, address, data):
        if (address >= 0xC000 and address <= 0xFDFF):
            # C000-DFFF Work RAM (8KB)
            # E000-FDFF Echo RAM
            self.wram[address & 0x1FFF] = data
        elif (address >= 0xFF80 and address <= 0xFFFE):
            # FF80-FFFE High RAM
            self.hram[address & 0x7F] = data

    def read(self, address):
        if (address >= 0xC000 and address <= 0xFDFF):
            # C000-DFFF Work RAM
            # E000-FDFF Echo RAM
            return self.wram[address & 0x1FFF] & 0xFF
        elif (address >= 0xFF80 and address <= 0xFFFE):
            # FF80-FFFE High RAM
            return self.hram[address & 0x7F] & 0xFF
        return 0xFF
