"""
PyBoy GameBoy (TM) Emulator
 
Gameboy Scheduler and Memory Mapper

"""
from pypy.lang.gameboy import constants
from pypy.lang.gameboy.cpu import *
from pypy.lang.gameboy.cartridge import *
from pypy.lang.gameboy.interrupt import *
from pypy.lang.gameboy.joypad import *
from pypy.lang.gameboy.ram import *
from pypy.lang.gameboy.serial import *
from pypy.lang.gameboy.sound import *
from pypy.lang.gameboy.timer import *
from pypy.lang.gameboy.video import *
from pypy.lang.gameboy.cartridge import *


class GameBoy(object):

    def __init__(self):
        self.createDrivers()
        self.createGamboyElements()

    def createDrivers(self):
        self.clock = Clock()
        self.joypadDriver = JoypadDriver()
        self.videoDriver = VideoDriver()
        self.soundDriver = SoundDriver()
        
    def createGamboyElements(self): 
        self.ram = RAM()
        self.cartridgeManager = CartridgeManager(self.clock)
        self.interrupt = Interrupt()
        self.cpu = CPU(self.interrupt, self)
        self.serial = Serial(self.interrupt)
        self.timer = Timer(self.interrupt)
        self.joypad = Joypad(self.joypadDriver, self.interrupt)
        self.video = Video(self.videoDriver, self.interrupt, self)
        self.sound = Sound(self.soundDriver)  

    def getCartridgeManager(self):
        return self.cartridgeManager
    
    def loadCartridge(self, cartridge):
        self.cartridgeManager.load(cartridge)

    def getFrameSkip(self):
        return self.video.getFrameSkip()

    def setFrameSkip(self, frameSkip):
        self.video.setFrameSkip(frameSkip)

    def load(self, cartridgeName):
        self.cartridge.load(cartridgeName)

    def save(self, cartridgeName):
        self.cartridge.save(cartridgeName)

    def start(self):
        self.sound.start()

    def stop(self):
        self.sound.stop()

    def reset(self):
        self.ram.reset()
        self.cartridge.reset()
        self.interrupt.reset()
        self.cpu.reset()
        self.serial.reset()
        self.timer.reset()
        self.joypad.reset()
        self.video.reset()
        self.sound.reset()
        self.cpu.setROM(self.cartridge.getROM())
        self.drawLogo()

    def cycles(self):
        return min( self.video.cycles(), self.serial.cycles(),
                    self.timer.cycles(), self.sound.cycles(),
                    self.joypad.cycles())

    def emulate(self, ticks):
        while (ticks > 0):
            count = self.cycles()
            self.cpu.emulate(count)
            self.serial.emulate(count)
            self.timer.emulate(count)
            self.video.emulate(count)
            self.sound.emulate(count)
            self.joypad.emulate(count)
            ticks -= count

    def write(self, address, data):
        self.getreceiver(address).write(address, data)

    def read(self, address):
        self.getreceiver(address).read(address)

    def getreceiver(self, address):
        if 0x0000 <= address <= 0x7FFF:
            return Gameboy.cartridge
        elif 0x8000 <= address <= 0x9FFF:
            return Gameboy.video
        elif 0xA000 <= address <= 0xBFFF:
            return Gameboy.cartridge
        elif 0xC000 <= address <= 0xFDFF:
            return Gameboy.ram
        elif 0xFE00 <= address <= 0xFEFF:
            return Gameboy.video
        elif 0xFF00 <= address <= 0xFF00:
            return Gameboy.joypad
        elif 0xFF01 <= address <= 0xFF02:
            return Gameboy.serial
        elif 0xFF04 <= address <= 0xFF07:
            return Gameboy.timer
        elif 0xFF0F <= address <= 0xFF0F:
            return Gameboy.interrupt
        elif 0xFF10 <= address <= 0xFF3F:
            return Gameboy.sound
        elif 0xFF40 <= address <= 0xFF4B:
            return Gameboy.video
        elif 0xFF80 <= address <= 0xFFFE:
            return Gameboy.ram
        elif 0xFFFF <= address <= 0xFFFF:
            return Gameboy.interrupt

    def drawLogo(self):
        for index in range(0, 48):
            bits = self.cartridge.read(0x0104 + index)
            pattern0 = ((bits >> 0) & 0x80) + ((bits >> 1) & 0x60)\
                     + ((bits >> 2) & 0x18) + ((bits >> 3) & 0x06)\
                     + ((bits >> 4) & 0x01)

            pattern1 = ((bits << 4) & 0x80) + ((bits << 3) & 0x60)\
                     + ((bits << 2) & 0x18) + ((bits << 1) & 0x06)\
                     + ((bits << 0) & 0x01)

            self.video.write(0x8010 + (index << 3), pattern0)
            self.video.write(0x8012 + (index << 3), pattern0)

            self.video.write(0x8014 + (index << 3), pattern1)
            self.video.write(0x8016 + (index << 3), pattern1)

        for index in range(0, 8):
            self.video.write(0x8190 + (index << 1), constants.REGISTERED_BITMAP[index])

        for tile in range(0, 12):
            self.video.write(0x9904 + tile, tile + 1)
            self.video.write(0x9924 + tile, tile + 13)

        self.video.write(0x9905 + 12, 25)
