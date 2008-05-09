"""
PyBoy GameBoy (TM) Emulator
 
GameBoy Scheduler and Memory Mapper

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
        self.create_drivers()
        self.create_gamboy_elements()

    def create_drivers(self):
        self.clock = Clock()
        self.joypad_driver = JoypadDriver()
        self.video_driver  = VideoDriver()
        self.sound_driver  = SoundDriver()
        
    def create_gamboy_elements(self): 
        self.ram    = RAM()
        self.cartridge_manager = CartridgeManager(self.clock)
        self.interrupt = Interrupt()
        self.cpu    = CPU(self.interrupt, self)
        self.serial = Serial(self.interrupt)
        self.timer  = Timer(self.interrupt)
        self.joypad = Joypad(self.joypad_driver, self.interrupt)
        self.video  = Video(self.video_driver, self.interrupt, self)
        self.sound  = Sound(self.sound_driver)  

    def get_cartridge_manager(self):
        return self.cartridge_manager
    
    def load_cartridge(self, cartridge):
        self.cartridge_manager.load(cartridge)
        self.cpu.set_rom(self.cartridge_manager.get_rom())
        
    def load_cartridge_file(self, path):
        self.load_cartridge(Cartridge(path))

    def get_frame_skip(self):
        return self.video.get_frame_skip()

    def set_frame_skip(self, frameSkip):
        self.video.set_frame_skip(frameSkip)

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
        self.cpu.set_rom(self.cartridge_manager.get_rom())
        self.drawLogo()

    def get_cycles(self):
        return min( self.video.get_cycles(), self.serial.get_cycles(),
                    self.timer.get_cycles(), self.sound.get_cycles(),
                    self.joypad.get_cycles())

    def emulate(self, ticks):
        while ticks > 0:
            count = self.get_cycles()
            self.cpu.emulate(count)
            self.serial.emulate(count)
            self.timer.emulate(count)
            self.video.emulate(count)
            self.sound.emulate(count)
            self.joypad.emulate(count)
            ticks -= count

    def write(self, address, data):
        receiver = self.get_receiver(address)
        if receiver==None:
            raise Exception("invalid read address given")
        receiver.write(address, data)

    def read(self, address):
        receiver = self.get_receiver(address)
        if receiver==None:
            raise Exception("invalid read address given")
        return receiver.read(address)

    def get_receiver(self, address):
        if 0x0000 <= address <= 0x7FFF:
            return self.cartridge_manager.get_memory_bank()
        elif 0x8000 <= address <= 0x9FFF:
            return self.video
        elif 0xA000 <= address <= 0xBFFF:
            return self.cartridge_manager.get_memory_bank()
        elif 0xC000 <= address <= 0xFDFF:
            return self.ram
        elif 0xFE00 <= address <= 0xFEFF:
            return self.video
        elif 0xFF00 <= address <= 0xFF00:
            return self.joypad
        elif 0xFF01 <= address <= 0xFF02:
            return self.serial
        elif 0xFF04 <= address <= 0xFF07:
            return self.timer
        elif 0xFF0F <= address <= 0xFF0F:
            return self.interrupt
        elif 0xFF10 <= address <= 0xFF3F:
            return self.sound
        elif 0xFF40 <= address <= 0xFF4B:
            return self.video
        elif 0xFF80 <= address <= 0xFFFE:
            return self.ram
        elif 0xFFFF <= address <= 0xFFFF:
            return self.interrupt

    def draw_logo(self):
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
