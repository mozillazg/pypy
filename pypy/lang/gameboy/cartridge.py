# constants.CATRIGE constants.TYPES
# ___________________________________________________________________________

from pypy.lang.gameboy import constants
from pypy.lang.gameboy.timer import *
from pypy.rlib.streamio import open_file_as_stream

from pypy.lang.gameboy.ram import iMemory

#from pypy.rlib.rstr import str_replace

import os

def has_cartridge_battery(self, cartridge_type):    
    return (cartridge_type == constants.TYPE_MBC1_RAM_BATTERY \
                or cartridge_type == constants.TYPE_MBC2_BATTERY \
                or cartridge_type == constants.TYPE_MBC3_RTC_BATTERY \
                or cartridge_type == constants.TYPE_MBC3_RTC_RAM_BATTERY \
                or cartridge_type == constants.TYPE_MBC3_RAM_BATTERY \
                or cartridge_type == constants.TYPE_MBC5_RAM_BATTERY \
                or cartridge_type == constants.TYPE_MBC5_RUMBLE_RAM_BATTERY \
                or cartridge_type == constants.TYPE_HUC1_RAM_BATTERY)


def create_bank_controller(self, cartridge_type, rom, ram, clock):
        if constants.CATRIDGE_TYPE_MAPPING.has_key(cartridge_type) :
            return constants.CATRIDGE_TYPE_MAPPING[cartridge_type](rom, ram, clock)
        else:
            raise InvalidMemoryBankTypeError("Unsupported memory bank controller (0x"+hex(cartridge_type)+")")

class InvalidMemoryBankTypeError(Exception):
    pass

def map_to_byte( string):
    mapped = [0]*len(string)
    for i in range(len(string)):
        mapped[i]  = ord(string[i]) & 0xFF
    return mapped

def map_to_string(int_array):
    mapped = [0]*len(int_array)
    for i in range(len(int_array)):
        mapped[i]  = chr(int_array[i])
    return ("").join(mapped)
        
# ==============================================================================
# CARTRIDGE

class CartridgeManager(object):
    
    def __init__(self, clock):
        assert isinstance(clock, Clock)
        self.clock = clock
        self.cartridge = None
        self.mbc = None
        
    def reset(self):
        if not self.has_battery():
            self.ram[0:len(self.ram):1] = 0xFF
        self.mbc.reset()

    def read(self, address):
        return self.mbc.read(address)
    
    def write(self, address, data):
        self.mbc.write(address, data)
    
    def load(self, cartridge):
        assert isinstance(cartridge, Cartridge)
        self.cartridge = cartridge
        self.rom  = self.cartridge.read()
        self.check_rom()
        self.create_ram()
        self.load_battery()
        self.mbc = self.create_bank_controller(self.get_memory_bank_type(), \
                                               self.rom, self.ram, self.clock)
        
    def check_rom(self):
        if not self.verify_header():
            raise Exception("Cartridge header is corrupted")
        if self.cartridge.get_size() < self.get_rom_size():
            raise Exception("Cartridge is truncated")
        
    def create_ram(self):
        ram_size = self.get_ram_size()
        if self.get_memory_bank_type() >= constants.TYPE_MBC2 \
                and self.get_memory_bank_type() <= constants.TYPE_MBC2_BATTERY:
            ram_size = 512
        self.ram = [0xFF]*ram_size
        
    def load_battery(self):
        if self.cartridge.has_battery():
            self.ram = self.cartridge.read_battery()

    def save(self, cartridge_name):
        if self.cartridge.has_battery():
            self.cartridge.write_battery(self.ram)
            
    def get_memory_bank_type(self):
        return self.rom[constants.CARTRIDGE_TYPE_ADDRESS] & 0xFF
    
    def get_memory_bank(self):
        return self.mbc

    def get_rom(self):
        return self.rom
        
    def get_rom_size(self):
        rom_size = self.rom[constants.CARTRIDGE_ROM_SIZE_ADDRESS] & 0xFF
        if rom_size>=0x00 and rom_size<=0x07:
            return 32768 << rom_size
        return -1
        
    def get_ram_size(self):
        return constants.CARTRIDGE_RAM_SIZE_MAPPING[self.rom[constants.CARTRIDGE_RAM_SIZE_ADDRESS]]
    
    def get_destination_code(self):
        return self.rom[constants.DESTINATION_CODE_ADDRESS] & 0xFF
    
    def get_licensee_code():
        return self.rom[constants.LICENSEE_ADDRESS] & 0xFF

    def get_rom_version(self):
        return self.rom[constants.CARTRIDGE_ROM_VERSION_ADDRESS] & 0xFF
    
    def get_header_checksum(self):
        return self.rom[constants.HEADER_CHECKSUM_ADDRESS] & 0xFF
    
    def get_checksum(self):
        return ((self.rom[constants.CHECKSUM_A_ADDRESS] & 0xFF) << 8) \
                + (self.rom[constants.CHECKSUM_B_ADDRESS] & 0xFF)
    
    def has_battery(self):
        return has_cartridge_battery(self.get_memory_bank_type())
    
    def verify(self):
        checksum = 0
        for address in range(len(self.rom)):
            if address is not 0x014E and address is not 0x014F:
                checksum = (checksum + (self.rom[address] & 0xFF)) & 0xFFFF
        return (checksum == self.get_checksum())
    
    def verify_header(self):
        if len(self.rom) < 0x0150:
            return False
        checksum = 0xE7
        for address in range(0x0134, 0x014C):
            checksum = (checksum - (self.rom[address] & 0xFF)) & 0xFF
        return (checksum == self.get_header_checksum())
    
    def create_bank_controller(self, type, rom, ram, clock_driver):
        return MEMORY_BANK_MAPPING[type](rom, ram, clock_driver)


# ------------------------------------------------------------------------------

    
class Cartridge(object):
    """
        File mapping. Holds the file contents
    """
    def __init__(self, file=None):
        self.reset()
        if file is not None:
            self.load(file)
        
    def reset(self):
        self.cartridge_name = ""
        self.cartridge_file_path = ""
        self.cartridge_stream = None
        self.cartridge_file_contents = None
        self.battery_name = ""
        self.battery_file_path = ""
        self.battery_stream = None
        self.battery_file_contents = None
        
        
    def load(self, cartridge_path):
        if cartridge_path is None:
            raise Exception("cartridge_path cannot be None!")
        cartridge_path = str(cartridge_path)
        self.cartridge_file_path = cartridge_path
        self.cartridge_stream = open_file_as_stream(cartridge_path)
        self.cartridge_file_contents = map_to_byte( \
                                                self.cartridge_stream.readall())
        self.load_battery(cartridge_path)
        
    def load_battery(self, cartridge_file_path):
        self.battery_file_path = self.create_battery_file_path(cartridge_file_path)
        if self.has_battery():
            self.battery_stream = open_file_as_stream(self.battery_file_path)
            self.battery_file_contents = map_to_byte( \
                                             self.battery_stream.readall())
    
    def create_battery_file_path(self, cartridge_file_path):
        if cartridge_file_path.endswith(constants.CARTRIDGE_FILE_EXTENSION):
            return cartridge_file_path.replace(
                                        constants.CARTRIDGE_FILE_EXTENSION,
                                        constants.BATTERY_FILE_EXTENSION)
        elif cartridge_file_path.endswith(
                                constants.CARTRIDGE_COLOR_FILE_EXTENSION):
            return cartridge_file_pat.replace(
                                    constants.CARTRIDGE_COLOR_FILE_EXTENSION,
                                    constants.BATTERY_FILE_EXTENSION)
        else:
            return cartridge_file_path + constants.BATTERY_FILE_EXTENSION
    
    def has_battery(self):
        if self.battery_file_path is None:
            return False
        return os.path.exists(self.battery_file_path)
    
    def read(self):
        return self.cartridge_file_contents
    
    def read_battery(self):
        return  self.battery_file_contents
    
    def write_battery(self, ram):
        output_stream = open_file_as_stream(self.battery_file_path, "w")
        output_stream.write(map_to_string(ram))
        output_stream.flush()
        self.battery_file_contents = ram
        
    def remove_battery(self):
        if self.has_battery() and self.battery_file_path is not None:
            os.remove(self.battery_file_path)
            
    def get_size(self):
        if self.cartridge_file_path is None:
            return -1
        return os.path.getsize(self.cartridge_file_path)
        
    def get_battery_size(self):
        if self.battery_file_path is None:
            return -1
        return os.path.getsize(self.battery_file_path)
        
# ==============================================================================
# CARTRIDGE TYPES

class MBC(iMemory):
    
    def __init__(self, rom, ram, clock_driver,
                    min_rom_bank_size=0, max_rom_bank_size=0,
                    min_ram_bank_size=0, max_ram_bank_size=0):
        self.clock = clock_driver
        self.min_rom_bank_size = min_rom_bank_size
        self.max_rom_bank_size = max_rom_bank_size
        self.min_ram_bank_size = min_ram_bank_size
        self.max_ram_bank_size = max_ram_bank_size
        self.reset()
        self.set_rom(rom)
        self.set_ram(ram)

    def reset(self):
        self.rom_bank = constants.ROM_BANK_SIZE
        self.ram_bank = 0
        self.ram_enable = False
        self.rom = []
        self.ram = []
        self.rom_size = 0
        self.ram_size = 0
    
    def set_rom(self, buffer):
        banks = len(buffer) / constants.ROM_BANK_SIZE
        if banks < self.min_rom_bank_size or banks > self.max_rom_bank_size:
            raise Exception("Invalid constants.ROM size")
        self.rom = buffer
        self.rom_size = constants.ROM_BANK_SIZE*banks - 1


    def set_ram(self, buffer):
        banks = len(buffer) / constants.RAM_BANK_SIZE
        if banks < self.min_ram_bank_size or banks > self.max_ram_bank_size:
            raise Exception("Invalid constants.RAM size")
        self.ram = buffer
        self.ram_size = constants.RAM_BANK_SIZE*banks - 1
        
        
    def read(self, address):    
        if address <= 0x3FFF: # 0000-3FFF
            return self.rom[address] & 0xFF
        elif address <= 0x7FFF:# 4000-7FFF
            return self.rom[self.rom_bank + (address & 0x3FFF)] & 0xFF
        elif address >= 0xA000 and address <= 0xBFFF and self.ram_enable: # A000-BFFF
            return self.ram[self.ram_bank + (address & 0x1FFF)] & 0xFF
        raise Exception("MBC: Invalid address, out of range")
    
    def write(self, address, data):
        pass
  

#-------------------------------------------------------------------------------

  
class DefaultMBC(MBC):
    
    def __init__(self, rom, ram, clock_driver):
        MBC.__init__(self, rom, ram, clock_driver, 
                        min_rom_bank_size=0,
                        max_rom_bank_size=0xFFFFFF,
                        min_ram_bank_size=0,
                        max_ram_bank_size=0xFFFFFF)
    

#-------------------------------------------------------------------------------
  

class MBC1(MBC):
    """
    PyBoy GameBoy (TM) Emulator
    
    Memory Bank Controller 1 (2MB constants.ROM, 32KB constants.RAM)
     
    0000-3FFF    ROM Bank 0 (16KB)
    4000-7FFF    ROM Bank 1-127 (16KB)
    A000-BFFF    RAM Bank 0-3 (8KB)
     """
    def __init__(self, rom, ram, clock_driver):
        MBC.__init__(self, rom, ram, clock_driver, 
                        min_ram_bank_size=0,
                        max_ram_bank_size=4,
                        min_rom_bank_size=2,    
                        max_rom_bank_size=128)
        
    def reset(self):
        MBC.reset(self)
        self.memory_model = 0

    def write(self, address, data):
        if address <= 0x1FFF:  # 0000-1FFF
            self.write_ram_enable(address, data)
        elif address <= 0x3FFF: # 2000-3FFF
            self.write_rom_bank_1(address, data)
        elif address <= 0x5FFF: # 4000-5FFF
            self.write_rom_bank_2(address, data)
        elif address <= 0x7FFF: # 6000-7FFF
            self.memory_model = data & 0x01
        elif address >= 0xA000 and address <= 0xBFFF and self.ram_enable: # A000-BFFF
            self.ram[self.ram_bank + (address & 0x1FFF)] = data

    def write_ram_enable(self, address, data):
        if self.ram_size > 0:
            self.ram_enable = ((data & 0x0A) == 0x0A)
    
    def write_rom_bank_1(self, address, data):
        if (data & 0x1F) == 0:
            data = 1
        if self.memory_model == 0:
            self.rom_bank = ((self.rom_bank & 0x180000) + ((data & 0x1F) << 14)) & self.rom_size
        else:
            self.rom_bank = ((data & 0x1F) << 14) & self.rom_size
        
    def write_rom_bank_2(self, address, data):
        if self.memory_model == 0:
            self.rom_bank = ((self.rom_bank & 0x07FFFF) + ((data & 0x03) << 19)) & self.rom_size
        else:
            self.ram_bank = ((data & 0x03) << 13) & self.ram_size
  

#-------------------------------------------------------------------------------

      
class MBC2(MBC):
    """
    PyBoy GameBoy (TM) Emulator
    
    Memory Bank Controller 2 (256KB constants.ROM, 512x4bit constants.RAM)
    
    0000-3FFF    ROM Bank 0 (16KB)
    4000-7FFF    ROM Bank 1-15 (16KB)
    A000-A1FF    RAM Bank (512x4bit)
     """
     
    RAM_BANK_SIZE = 512

    def __init__(self, rom, ram, clock_driver):
        MBC.__init__(self, rom, ram, clock_driver,
                    min_ram_bank_size=constants.RAM_BANK_SIZE,
                    max_ram_bank_size=constants.RAM_BANK_SIZE,
                    min_rom_bank_size=2,   
                    max_rom_bank_size=16)
        

    def read(self, address):
        if address > 0xA1FF:
            return 0xFF
        else:
            return MBC.read(self, address)
        
    def write(self, address, data):
        if address <= 0x1FFF:  # 0000-1FFF
            self.write_ram_enable(address, data)
        elif address <= 0x3FFF: # 2000-3FFF
            self.write_rom_bank(address, data)
        elif address >= 0xA000 and address <= 0xA1FF: # A000-A1FF
            self.write_ram(address, data)
            
    def write_ram_enable(self, address, data):
        if (address & 0x0100) == 0:
            self.ram_enable = ((data & 0x0A) == 0x0A)
            
    def write_rom_bank(self, address, data):
        if (address & 0x0100) == 0:
            return
        if (data & 0x0F) == 0:
            data = 1
        self.rom_bank = ((data & 0x0F) << 14) & self.rom_size
        
    def write_ram(self, address, data):
        if self.ram_enable:
            self.ram[address & 0x01FF] = data & 0x0F


#-------------------------------------------------------------------------------


class MBC3(MBC):
    """
    PyBoy GameBoy (TM) Emulator
    
    Memory Bank Controller 3 (2MB constants.ROM, 32KB constants.RAM, Real Time Clock)
    
    0000-3FFF    ROM Bank 0 (16KB)
    4000-7FFF    ROM Bank 1-127 (16KB)
    A000-BFFF    RAM Bank 0-3 (8KB)
    """
    def __init__(self, rom, ram, clock_driver):
        MBC.__init__(self, rom, ram, clock_driver,
                        min_ram_bank_size=0,
                        max_ram_bank_size=4,
                        min_rom_bank_size=2,  
                        max_rom_bank_size=128)


    def reset(self):
        MBC.reset(self)
        self.clockLDaysclockLControl = None
        self.clock_time     = self.clock.get_time()
        self.clock_latch     = 0
        self.clock_register = 0
        self.clockSeconds   = 0
        self.clockMinutes   = 0
        self.clockHours     = 0
        self.clockDays      = 0
        self.clockControl   = 0
        self.clockLSeconds  = 0
        self.clockLMinutes  = 0
        self.clockLHours    = 0
        self.clockLDays     = 0
        self.clockLControl  = 0


    def read(self, address):
        if address >= 0xA000 and address <= 0xBFFF:  # A000-BFFF
            if self.ram_bank >= 0:
                return self.ram[self.ram_bank + (address & 0x1FFF)] & 0xFF
            else:
                return self.read_clock_data(address)
        else:
            return MBC.read(self, address)
        
    def read_clock_data(self, address):
        if self.clock_register == 0x08:
            return self.clockLSeconds
        if self.clock_register == 0x09:
            return self.clockLMinutes
        if self.clock_register == 0x0A:
            return self.clockLHours
        if self.clock_register == 0x0B:
            return self.clockLDays
        if self.clock_register == 0x0C:
            return self.clockLControl
        raise Exception("MBC*.read_clock_data invalid address %i")
    
    def write(self, address, data):
        if address <= 0x1FFF: # 0000-1FFF
            self.write_ram_enable(address, data)
        elif address <= 0x3FFF: # 2000-3FFF
            self.write_rom_bank(address, data)
        elif address <= 0x5FFF:  # 4000-5FFF
            self.write_ram_bank(address, data)
        elif address <= 0x7FFF: # 6000-7FFF
            self.write_clock_latch(address, data)
        elif address >= 0xA000 and address <= 0xBFFF and self.ram_enable: # A000-BFFF
            self.write_clock_data(address, data)
    
    def write_ram_enable(self, address, data):
        if self.ram_size > 0:
            self.ram_enable = ((data & 0x0A) == 0x0A)
             
    def write_rom_bank(self, address, data):
        if data == 0:
            data = 1
        self.rom_bank = ((data & 0x7F) << 14) & self.rom_size
            
    def write_ram_bank(self, address, data):
        if data >= 0x00 and data <= 0x03:
            self.ram_bank = (data << 13) & self.ram_size
        else:
            self.ram_bank = -1
            self.clock_register = data
                
    def write_clock_latch(self, address, data):
        if self.clock_latch == 0 and data == 1:
            self.latch_clock()
        if data == 0 or data == 1:
            self.clock_latch = data
            
    def write_clock_data(self, address, data):
        if self.ram_bank >= 0:
            self.ram[self.ram_bank + (address & 0x1FFF)] = data
        else:
            self.update_clock()
            if self.clock_register == 0x08:
                self.clockSeconds = data
            if self.clock_register == 0x09:
                self.clockMinutes = data
            if self.clock_register == 0x0A:
                self.clockHours = data
            if self.clock_register == 0x0B:
                self.clockDays = data
            if self.clock_register == 0x0C:
                self.clockControl = (self.clockControl & 0x80) | data
        

    def latch_clock(self):
        self.update_clock()
        self.clockLSeconds = self.clockSeconds
        self.clockLMinutes = self.clockMinutes
        self.clockLHours   = self.clockHours
        self.clockLDays    = self.clockDays & 0xFF
        self.clockLControl = (self.clockControl & 0xFE) | ((self.clockDays >> 8) & 0x01)


    def update_clock(self):
        now = self.clock.get_time()
        if (self.clockControl & 0x40) == 0:
            elapsed = now - self.clock_time
            while elapsed >= 246060:
                elapsed -= 246060
                self.clockDays+=1
            while elapsed >= 6060:
                elapsed -= 6060
                self.clockHours+=1
            while elapsed >= 60:
                elapsed -= 60
                self.clockMinutes+=1
            self.clockSeconds += elapsed
            while self.clockSeconds >= 60:
                self.clockSeconds -= 60
                self.clockMinutes+=1
            while self.clockMinutes >= 60:
                self.clockMinutes -= 60
                self.clockHours+=1
            while self.clockHours >= 24:
                self.clockHours -= 24
                self.clockDays+=1
            while self.clockDays >= 512:
                self.clockDays -= 512
                self.clockControl |= 0x80
        self.clock_time = now


#-------------------------------------------------------------------------------


class MBC5(MBC):
    """
    PyBoy GameBoy (TM) Emulator
    
    Memory Bank Controller 5 (8MB constants.ROM, 128KB constants.RAM)
     *
    0000-3FFF    ROM Bank 0 (16KB)
    4000-7FFF    ROM Bank 1-511 (16KB)
    A000-BFFF    RAM Bank 0-15 (8KB)
    """
    def __init__(self, rom, ram, clock_driver):
        MBC.__init__(self, rom, ram, clock_driver, 
                        min_ram_bank_size=0,
                        max_ram_bank_size=16,
                        min_rom_bank_size=2,    
                        max_rom_bank_size=512)

    def reset(self):
        MBC.reset(self)
        self.rumble = True
        

    def write(self, address, data):
        address = int(address)
        if address <= self.ram_enable:  # 0000-1FFF
            self.write_ram_enable(address, data)
        elif address <= 0x2FFF:  # 2000-2FFF
            self.rom_bank = ((self.rom_bank & (0x01 << 22)) + \
                             ((data & 0xFF) << 14)) & self.rom_size
        elif address <= 0x3FFF: # 3000-3FFF
            self.rom_bank = ((self.rom_bank & (0xFF << 14)) + \
                             ((data & 0x01) << 22)) & self.rom_size
        elif address <= 0x4FFF:  # 4000-4FFF
            self.write_ram_bank(address, data)
        elif address >= 0xA000 and address <= 0xBFFF and self.ram_enable:  # A000-BFFF
            self.ram[self.ram_bank + (address & 0x1FFF)] = data

    def write_ram_enable(self, address, data):
        if self.ram_size > 0:
            self.ram_enable = ((data & 0x0A) == 0x0A)
            
    def write_ram_bank(self, address, data):
        if self.rumble:
            self.ram_bank = ((data & 0x07) << 13) & self.ram_size
        else:
            self.ram_bank = ((data & 0x0F) << 13) & self.ram_size


#-------------------------------------------------------------------------------


class HuC1(MBC):
    def __init__(self, ram, rom, clock_driver):
        self.reset()
        MBC.__init__(self, rom, ram, clock_driver)



#-------------------------------------------------------------------------------



class HuC3(MBC):
    """
    PyBoy GameBoy (TM) Emulator
    
    Hudson Memory Bank Controller 3 (2MB constants.ROM, 128KB constants.RAM, constants.RTC)
    
    0000-3FFF    ROM Bank 0 (16KB)
    4000-7FFF    ROM Bank 1-127 (16KB)
    A000-BFFF    RAM Bank 0-15 (8KB)
    """
    def __init__(self, rom, ram, clock_driver):
        MBC.__init__(self, rom, ram, clock_driver, 
                        min_ram_bank_size=0,
                        max_ram_bank_size=4,
                        min_rom_bank_size=2,    
                        max_rom_bank_size=128)


    def reset(self):
        MBC.reset(self)
        self.ram_flag = 0
        self.ram_value = 0
        self.clock_register = 0
        self.clock_shift = 0
        self.clock_time = self.clock.get_time()


    def read(self, address):
        address = int(address)
        if address >= 0xA000 and address <= 0xBFFF:# A000-BFFF
            if self.ram_flag == 0x0C:
                return self.ram_value
            elif self.ram_flag == 0x0D:
                return 0x01
            elif self.ram_flag == 0x0A or self.ram_flag == 0x00:
                if self.ram_size > 0:
                    return self.ram[self.ram_bank + (address & 0x1FFF)] & 0xFF
            raise Exception("Huc3 read error")
        else:
            return MBC.read(self, address)
    
    def write(self, address, data):
        address = int(address)
        if address <= 0x1FFF: # 0000-1FFF
            self.ram_flag = data
        elif address <= 0x3FFF:# 2000-3FFF
            self.write_rom_bank(address, data)
        elif address <= 0x5FFF: # 4000-5FFF
            self.ram_bank = ((data & 0x0F) << 13) & self.ram_size
        elif address >= 0xA000 and address <= 0xBFFF: # A000-BFFF
            self.write_ram_flag(address, data)
         
    def write_rom_bank(self, address, data):
        if (data & 0x7F) == 0:
            data = 1
        self.rom_bank = ((data & 0x7F) << 14) & self.rom_size
        
    def write_ram_flag(self, address, data):
        if self.ram_flag == 0x0B:
            self.write_with_ram_flag_0x0B(address, data)
        elif self.ram_flag >= 0x0C and self.ram_flag <= 0x0E:
            pass
        elif self.ram_flag == 0x0A and self.ram_size > 0:
            self.ram[self.ram_bank + (address & 0x1FFF)] = data
                        
    def write_with_ram_flag_0x0B(self, address, data):
        if (data & 0xF0) == 0x10:
            self.write_ram_value_clock_shift(address, data)
        elif (data & 0xF0) == 0x30:
            self.write_clock_register_clock_shift(address, data)
        elif (data & 0xF0) == 0x40:
            self.write_clock_shift(address, data)
        elif (data & 0xF0) == 0x50:
            pass
        elif (data & 0xF0) == 0x60:
            self.ram_value = 0x01
         
    def write_ram_value_clock_shift(self, address, data):
        if self.clock_shift > 24:
            return
        self.ram_value = (self.clock_register >> self.clock_shift) & 0x0F
        self.clock_shift += 4
            
    def write_clock_register_clock_shift(self, address, data):
        if self.clock_shift > 24:
            return
        self.clock_register &= ~(0x0F << self.clock_shift)
        self.clock_register |= ((data & 0x0F) << self.clock_shift)
        self.clock_shift += 4
                    
    def write_clock_shift(self, address, data):
        switch = data & 0x0F
        self.update_clock()
        if switch == 0:
            self.clock_shift = 0
        elif switch == 3:
            self.clock_shift = 0
        elif switch == 7:
            self.clock_shift = 0
            
    def update_clock(self):
        now = self.clock.get_time()
        elapsed = now - self.clock_time
        # years (4 bits)
        while elapsed >= 365246060:
            self.clock_register += 1 << 24
            elapsed -= 365246060
        # days (12 bits)
        while elapsed >= 246060:
            self.clock_register += 1 << 12
            elapsed -= 246060
        # minutes (12 bits)
        while elapsed >= 60:
            self.clock_register += 1
            elapsed -= 60
        if (self.clock_register & 0x0000FFF) >= 2460:
            self.clock_register += (1 << 12) - 2460
        if (self.clock_register & 0x0FFF000) >= (365 << 12):
            self.clock_register += (1 << 24) - (365 << 12)
        self.clock_time = now - elapsed


# MEMORY BANK MAPPING ----------------------------------------------------------


MEMORY_BANK_TYPE_RANGES = [
    (constants.TYPE_MBC1,             constants.TYPE_MBC1_RAM_BATTERY,        MBC1),
    (constants.TYPE_MBC2,             constants.TYPE_MBC2_BATTERY,            MBC2),
    (constants.TYPE_MBC3_RTC_BATTERY, constants.TYPE_MBC3_RAM_BATTERY,        MBC3),
    (constants.TYPE_MBC5,             constants.TYPE_MBC5_RUMBLE_RAM_BATTERY, MBC5),
    (constants.TYPE_HUC3_RTC_RAM,     constants.TYPE_HUC3_RTC_RAM,            HuC3),
    (constants.TYPE_HUC1_RAM_BATTERY, constants.TYPE_HUC1_RAM_BATTERY,        HuC1)
]


def initialize_mapping_table():
    result = [DefaultMBC] * 256
    for entry in MEMORY_BANK_TYPE_RANGES:
        if len(entry) == 2:
            positions = [entry[0]]
        else:
            positions = range(entry[0], entry[1]+1)
        for pos in positions:
            result[pos] = entry[-1]
    return result

MEMORY_BANK_MAPPING = initialize_mapping_table()
