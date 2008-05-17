"""
PyBoy GameBoy (TM) Emulator

Work and High RAM
"""

from pypy.lang.gameboy import constants


class iMemory(object):
     def write(self, address, data):
         pass
     
     def read(self, address):
         return 0xFF

class RAM(iMemory):

    def __init__(self):
        # Work RAM
        self.w_ram =  [0x00]*8192
        # High RAM
        self.h_ram =  [0x00]*128
        self.reset()

    def reset(self):
        # Work RAM
        self.w_ram =  [0x00]*8192
        # High RAM
        self.h_ram =  [0x00]*128

    def write(self, address, data):
        if (address >= 0xC000 and address <= 0xFDFF):
            # C000-DFFF Work RAM (8KB)
            # E000-FDFF Echo RAM
            self.w_ram[address & 0x1FFF] = data
        elif (address >= 0xFF80 and address <= 0xFFFE):
            # FF80-FFFE High RAM
            self.h_ram[address & 0x7F] = data

    def read(self, address):
        if (address >= 0xC000 and address <= 0xFDFF):
            # C000-DFFF Work RAM
            # E000-FDFF Echo RAM
            return self.w_ram[address & 0x1FFF] & 0xFF
        elif (address >= 0xFF80 and address <= 0xFFFE):
            # FF80-FFFE High RAM
            return self.h_ram[address & 0x7F] & 0xFF
        return 0xFF
