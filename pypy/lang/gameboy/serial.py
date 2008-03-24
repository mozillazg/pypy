"""
PyBoy GameBoy (TM) Emulator
Serial Link Controller
 """
from pypy.lang.gameboy import constants

class Serial(object):

     # Registers
    sb = 0
    sc = 0
    cycles = 0

     # Interrupt Controller #Interrupt
    interrupt = None

    def __init__(self, interrupt):
        self.interrupt = interrupt
        self.reset()

    def reset(self):
        self.cycles = constants.SERIAL_CLOCK
        self.sb = 0x00
        self.sc = 0x00

    def cycles(self):
        return self.cycles

    def emulate(self, ticks):
        if ((self.sc & 0x81) == 0x81):
            self.cycles -= ticks

            if (self.cycles <= 0):
                self.sb = 0xFF
                self.sc &= 0x7F
                self.cycles = constants.SERIAL_IDLE_CLOCK

                self.interrupt.raiseInterrupt(constants.SERIAL)


    def setSerialData(self, data):
        self.sb = data

    def setSerialControl(self, data):
        self.sc = data

        # HACK: delay the serial interrupt (Shin Nihon Pro Wrestling)
        self.cycles = constants.SERIAL_IDLE_CLOCK + constants.SERIAL_CLOCK

    def getSerialData(self):
        return self.sb

    def getSerialControl(self):
        return self.sc

