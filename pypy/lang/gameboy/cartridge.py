# constants.CATRIGE constants.TYPES
# ___________________________________________________________________________

from pypy.lang.gameboy import constants


def hasCartridgeBattery(self, cartridgeType):    
    return (cartridgeType == constants.TYPE_MBC1_RAM_BATTERY \
                or cartridgeType == constants.TYPE_MBC2_BATTERY \
                or cartridgeType == constants.TYPE_MBC3_RTC_BATTERY \
                or cartridgeType == constants.TYPE_MBC3_RTC_RAM_BATTERY \
                or cartridgeType == constants.TYPE_MBC3_RAM_BATTERY \
                or cartridgeType == constants.TYPE_MBC5_RAM_BATTERY \
                or cartridgeType == constants.TYPE_MBC5_RUMBLE_RAM_BATTERY \
                or cartridgeType == constants.TYPE_HUC1_RAM_BATTERY)

def hasCartridgeType(self, catridgeType):
    return constants.CATRIDGE_TYPE_MAPPING.has_key(cartridgeType);    

def createBankController(self, cartridgeType, rom, ram, clock):
        if hasCartridgeType(cartridgeType):
            return constants.CATRIDGE_TYPE_MAPPING[cartridgeType](rom, ram, clock)
        else:
            raise InvalidMemoryBankTypeError("Unsupported memory bank controller (0x"+hex(cartridgeType)+")")

class InvalidMemoryBankTypeError(Exception):
    pass



# ==============================================================================
# CARTRIDGE

class CartridgeLoader(object):
    
    def __init__(self, storeDriver, clockDriver):
        self.store = storeDriver
        self.clock = clockDriver
    
    def getCartridgeType(self):
        return self.rom[constants.CARTRIDGE_TYPE_ADDRESS] & 0xFF
    
    def getRom(self):
        return self.rom
        
    def getROMSize(self):
        romSize = self.rom[constants.CARTRIDGE_SIZE_ADDRESS] & 0xFF
        if romSize>=0x00 and romSize<=0x07:
            return 32768 << romSize
        return -1
        
    def getRAMSize(self):
        return constants.RAM_SIZE_MAPPING[self.rom[constants.RAM_SIZE_ADDRESS]]
    
    def getDestinationCode(self):
        return self.rom[constants.DESTINATION_CODE_ADDRESS] & 0xFF
    
    def getLicenseeCode():
        return self.rom[constants.LICENSEE_ADDRESS] & 0xFF

    def getROMVersion(self):
        return self.rom[constants.ROM_VERSION_ADDRESS] & 0xFF
    
    def getHeaderChecksum(self):
        return self.rom[constants.HEADER_CHECKSUM_ADDRESS] & 0xFF
    
    def getChecksum(self):
        return ((rom[constants.CHECKSUM_A_ADDRESS] & 0xFF) << 8) + (rom[constants.CHECKSUM_B_ADDRESS] & 0xFF)
    
    def hasBattery(self):
        return hasCartridgeBattery(self.getCartridgeType())
    
    def reset(self):
        if not self.hasBattery():
            self.ram[0:len(self.ram):1] = 0xFF
        self.mbc.reset()

    def read(self, address):
        return self.mbc.read(address)
    
    def write(self, address, data):
        self.mbc.write(address, data)
    
    def load(self, cartridgeName):
        romSize = self.store.getCartridgeSize(cartridgeName)
        self.rom = [0]*romSize
        self.store.readCartridge(cartridgeName, self.rom)
        if not self.verifyHeader():
            raise Exeption("Cartridge header is corrupted")
        if romSize < self.getROMSize():
            raise Exeption("Cartridge is truncated")
        ramSize = self.getRAMSize()
        if (getCartridgeType() >= constants.TYPE_MBC2
                and getCartridgeType() <= constants.TYPE_MBC2_BATTERY):
            ramSize = 512
        self.ram = [0xFF]*ramSize
        if self.store.hasBattery(cartridgeName):
            self.store.readBattery(cartridgeName, ram)
        self.mbc = createBankController(self.getCartridgeType(), rom, ram, clock)
    
    def save(self, cartridgeName):
        if self.hasBattery():
            self.store.writeBattery(cartridgeName, self.ram)
    
    def verify(self):
        checksum = 0
        for address in range(len(self.rom)):
            if address is not 0x014E and address is not 0x014F:
                checksum = (checksum + (self.rom[address] & 0xFF)) & 0xFFFF
        return (checksum == self.getChecksum())
    
    def verifyHeader(self):
        if self.rom.length < 0x0150:
            return false
        checksum = 0xE7
        for address in range(0x0134, 0x014C):
            checksum = (checksum - (rom[address] & 0xFF)) & 0xFF
        return (checksum == self.getHeaderChecksum())


# ==============================================================================
# CARTRIDGE TYPES

class MBC(object):

    def reset(self):
        self.romBank = constants.ROM_BANK_SIZE
        self.ramBank = 0
        self.ramEnable = False
        self.rom = []
        self.ram = []
        self.romSize = 0
        self.ramSize = 0
        self.minRomBankSize = 0
        self.maxRomBankSize = 0
        self.minRamBankSize = 0
        self.maxRamBankSize = 0
    
    def setROM(self, buffer):
        banks = len(buffer) / constants.ROM_BANK_SIZE
        if (banks < minRomBankSize or banks > maxRomBankSize):
            raise Exception("Invalid constants.ROM size")
        self.rom = buffer
        self.romSize = constants.ROM_BANK_SIZE*banks - 1


    def setRAM(buffer):
        banks = len(buffer) / constants.RAM_BANK_SIZE
        if (banks < minRamBankSize or banks > maxRamBankSize):
            raise Exception("Invalid constants.RAM size")
        self.ram = buffer
        self.ramSize = constants.RAM_BANK_SIZE*banks - 1
        
        
    def read(self, address):    
        if address <= 0x3FFF: # 0000-3FFF
            return self.rom[address] & 0xFF
        elif (address <= 0x7FFF):# 4000-7FFF
            return self.rom[romBank + (address & 0x3FFF)] & 0xFF
        elif (address >= 0xA000 and address <= 0xBFFF and self.ramEnable): # A000-BFFF
                return self.ram[self.ramBank + (address & 0x1FFF)] & 0xFF
        return 0xFF
    
    def write(self, address, data):
        pass


class MBC1(MBC):
    """
    PyBoy GameBoy (TM) Emulator
    
    Memory Bank Controller 1 (2MB constants.ROM, 32KB constants.RAM)
     
    0000-3FFF    ROM Bank 0 (16KB)
    4000-7FFF    ROM Bank 1-127 (16KB)
    A000-BFFF    RAM Bank 0-3 (8KB)
     """
    def __init__(self, rom, ram):
        self.minRamBankSize = 0
        self.maxRamBankSize = 4
        self.minRomBankSize = 2    
        self.maxRomBankSize = 128
        self.setRom(rom)
        self.serRam(ram)
        
    def reset(self):
        super.reset()
        self.memoryModel = 0

    def write(self, address, data):
        if (address <= 0x1FFF):  # 0000-1FFF
            if (self.ramSize > 0):
                self.ramEnable = ((data & 0x0A) == 0x0A)
        elif (address <= 0x3FFF): # 2000-3FFF
            if ((data & 0x1F) == 0):
                data = 1
            if (self.memoryModel == 0):
                self.romBank = ((self.romBank & 0x180000) + ((data & 0x1F) << 14)) & self.romSize
            else:
                self.romBank = ((data & 0x1F) << 14) & self.romSize
        elif (address <= 0x5FFF): # 4000-5FFF
            if (self.memoryModel == 0):
                self.romBank = ((self.romBank & 0x07FFFF) + ((data & 0x03) << 19)) & self.romSize
            else:
                self.ramBank = ((data & 0x03) << 13) & self.ramSize
        elif (address <= 0x7FFF): # 6000-7FFF
            self.memoryModel = data & 0x01
        elif (address >= 0xA000 and address <= 0xBFFF and self.ramEnable): # A000-BFFF
            self.ram[self.ramBank + (address & 0x1FFF)] = data

        
        
        
class MBC2(MBC):
    """
    PyBoy GameBoy (TM) Emulator
    
    Memory Bank Controller 2 (256KB constants.ROM, 512x4bit constants.RAM)
    
    0000-3FFF    ROM Bank 0 (16KB)
    4000-7FFF    ROM Bank 1-15 (16KB)
    A000-A1FF    RAM Bank (512x4bit)
     """
     
    RAM_BANK_SIZE = 512

    def __init__(self, rom, ram):
        self.minRamBankSize = constants.RAM_BANK_SIZE
        self.maxRamBankSize = constants.RAM_BANK_SIZE
        self.minRomBankSize = 2    
        self.maxRomBankSize = 16
        
        self.setROM(rom)
        self.setRAM(ram)

    def read(self, address):
        if address > 0xA1FF:
            return 0xFF
        else:
            return super.read(address)

    def write(self, address, data):
        if (address <= 0x1FFF):  # 0000-1FFF
            if ((address & 0x0100) == 0):
                self.ramEnable = ((data & 0x0A) == 0x0A)
        elif (address <= 0x3FFF): # 2000-3FFF
            if ((address & 0x0100) != 0):
                if ((data & 0x0F) == 0):
                    data = 1
                self.romBank = ((data & 0x0F) << 14) & self.romSize
        elif (address >= 0xA000 and address <= 0xA1FF): # A000-A1FF
            if (self.ramEnable):
                self.ram[address & 0x01FF] = (byte) (data & 0x0F)


    def write(self, address, data):
        if (address <= 0x1FFF):  # 0000-1FFF
            if (self.ramSize > 0):
                self.ramEnable = ((data & 0x0A) == 0x0A)
        elif (address <= 0x3FFF): # 2000-3FFF
            if ((data & 0x1F) == 0):
                data = 1
            if (self.memoryModel == 0):
                self.romBank = ((self.romBank & 0x180000) + ((data & 0x1F) << 14)) & self.romSize
            else:
                self.romBank = ((data & 0x1F) << 14) & self.romSize
        elif (address <= 0x5FFF): # 4000-5FFF
            if (self.memoryModel == 0):
                self.romBank = ((self.romBank & 0x07FFFF) + ((data & 0x03) << 19)) & self.romSize
            else:
                self.ramBank = ((data & 0x03) << 13) & self.ramSize
        elif (address <= 0x7FFF): # 6000-7FFF
            self.memoryModel = data & 0x01
        elif (address >= 0xA000 and address <= 0xBFFF and self.ramEnable): # A000-BFFF
            self.ram[self.ramBank + (address & 0x1FFF)] = data



class MBC3(MBC):
    """
    PyBoy GameBoy (TM) Emulator
    
    Memory Bank Controller 3 (2MB constants.ROM, 32KB constants.RAM, Real Time Clock)
    
    0000-3FFF    ROM Bank 0 (16KB)
    4000-7FFF    ROM Bank 1-127 (16KB)
    A000-BFFF    RAM Bank 0-3 (8KB)
    """
    
    clockSeconds = 0
    clockMinutes = 0
    clockHours = 0
    clockDays = 0
    clockControl = None
    clockLSeconds  = 0
    clockLMinutes = 0
    clockLHours = 0
    clockLDaysclockLControl = None

    def __init__(self, rom, ram, clock):
        self.minRamBankSize = 0
        self.maxRamBankSize = 4
        self.minRomBankSize = 2    
        self.maxRomBankSize = 128
        
        self.clock = clock
        self.clockRegister = 0
        self.clockLatch = 0
        self.clockTime = 0

        self.setROM(rom)
        self.setRAM(ram)


    def reset():
        super.reset()
        self.clockTime = self.clock.getTime()
        self.clockLatch = self.clockRegister = 0
        self.clockSeconds = self.clockMinutes = self.clockHours = self.clockDays = self.clockControl = 0
        self.clockLSeconds = self.clockLMinutes = self.clockLHours = self.clockLDays = self.clockLControl = 0


    def read(self, address):
        if (address >= 0xA000 and address <= 0xBFFF):  # A000-BFFF
            if (self.ramBank >= 0):
                return self.ram[self.ramBank + (address & 0x1FFF)] & 0xFF
            else:
                if (self.clockRegister == 0x08):
                    return self.clockLSeconds
                if (self.clockRegister == 0x09):
                    return self.clockLMinutes
                if (self.clockRegister == 0x0A):
                    return self.clockLHours
                if (self.clockRegister == 0x0B):
                    return self.clockLDays
                if (self.clockRegister == 0x0C):
                    return self.clockLControl
        else:
            return super.read(address)

    
    def write(self, address, data):
        if (address <= 0x1FFF): # 0000-1FFF
            if (self.ramSize > 0):
                self.ramEnable = ((data & 0x0A) == 0x0A)
        elif (address <= 0x3FFF): # 2000-3FFF
            if (data == 0):
                data = 1
            self.romBank = ((data & 0x7F) << 14) & self.romSize
        elif (address <= 0x5FFF):  # 4000-5FFF
            if (data >= 0x00 and data <= 0x03):
                self.ramBank = (data << 13) & self.ramSize
            else:
                self.ramBank = -1
                self.clockRegister = data
        elif (address <= 0x7FFF): # 6000-7FFF
            if (self.clockLatch == 0 and data == 1):
                self.latchClock()
            if (data == 0 or data == 1):
                self.clockLatch = data
        elif (address >= 0xA000 and address <= 0xBFFF and self.ramEnable): # A000-BFFF
            if (self.ramBank >= 0):
                self.ram[self.ramBank + (address & 0x1FFF)] = data
            else:
                self.updateClock()
                if (self.clockRegister == 0x08):
                    self.clockSeconds = data
                if (self.clockRegister == 0x09):
                    self.clockMinutes = data
                if (self.clockRegister == 0x0A):
                    self.clockHours = data
                if (self.clockRegister == 0x0B):
                    self.clockDays = data
                if (self.clockRegister == 0x0C):
                    self.clockControl = (self.clockControl & 0x80) | data


    def latchClock(self):
        self.updateClock()
        self.clockLSeconds = self.clockSeconds
        self.clockLMinutes = self.clockMinutes
        self.clockLHours = self.clockHours
        self.clockLDays = self.clockDays & 0xFF
        self.clockLControl = (self.clockControl & 0xFE) | ((self.clockDays >> 8) & 0x01)


    def updateClock():
        now = self.clock.getTime()
        if ((self.clockControl & 0x40) == 0):
            elapsed = now - self.clockTime
            while (elapsed >= 246060):
                elapsed -= 246060
                self.clockDays+=1
            while (elapsed >= 6060):
                elapsed -= 6060
                self.clockHours+=1
            while (elapsed >= 60):
                elapsed -= 60
                self.clockMinutes+=1
            self.clockSeconds += elapsed
            while (self.clockSeconds >= 60):
                self.clockSeconds -= 60
                self.clockMinutes+=1
            while (self.clockMinutes >= 60):
                self.clockMinutes -= 60
                self.clockHours+=1
            while (self.clockHours >= 24):
                self.clockHours -= 24
                self.clockDays+=1
            while (self.clockDays >= 512):
                self.clockDays -= 512
                self.clockControl |= 0x80
        self.clockTime = now



class MBC5(MBC):
    """
    PyBoy GameBoy (TM) Emulator
    
    Memory Bank Controller 5 (8MB constants.ROM, 128KB constants.RAM)
     *
    0000-3FFF    ROM Bank 0 (16KB)
    4000-7FFF    ROM Bank 1-511 (16KB)
    A000-BFFF    RAM Bank 0-15 (8KB)
    """
    def __init__(self, rom, ram, rumble):
        self.minRamBankSize = 0
        self.maxRamBankSize = 16
        self.minRomBankSize = 2    
        self.maxRomBankSize = 512
        
        self.rumble = rumble
        self.setROM(rom)
        self.setRAM(ram)


    def write(self, address, data):
        if (address <= 0x1FFF):  # 0000-1FFF
            if (self.ramSize > 0):
                self.ramEnable = ((data & 0x0A) == 0x0A)
        elif (address <= 0x2FFF):  # 2000-2FFF
            self.romBank = ((self.romBank & (0x01 << 22)) + ((data & 0xFF) << 14)) & self.romSize
        elif (address <= 0x3FFF): # 3000-3FFF
            self.romBank = ((self.romBank & (0xFF << 14)) + ((data & 0x01) << 22)) & self.romSize
        elif (address <= 0x4FFF):  # 4000-4FFF
            if (self.rumble):
                self.ramBank = ((data & 0x07) << 13) & self.ramSize
            else:
                self.ramBank = ((data & 0x0F) << 13) & self.ramSize
        elif (address >= 0xA000 and address <= 0xBFFF and self.ramEnable):  # A000-BFFF
            self.ram[self.ramBank + (address & 0x1FFF)] = data




class HuC1(MBC):
    def __init__(self, ram, rom):
        super.__init__(self, ram, rom)


class HuC3(MBC):
    """
    PyBoy GameBoy (TM) Emulator
    
    Hudson Memory Bank Controller 3 (2MB constants.ROM, 128KB constants.RAM, constants.RTC)
    
    0000-3FFF    ROM Bank 0 (16KB)
    4000-7FFF    ROM Bank 1-127 (16KB)
    A000-BFFF    RAM Bank 0-15 (8KB)
    """
    def __init__(self, rom, ram, clock):
        self.minRamBankSize = 0
        self.maxRamBankSize = 4
        self.minRomBankSize = 2    
        self.maxRomBankSize = 128
        self.clock = clock
        self.clockRegister = 0
        self.clockShift = 0
        self.clockTime = 0
        
        self.setROM(rom)
        self.setRAM(ram)
        self.ramFlag = 0
        self.ramValue = 0


    def reset():
        super.reset()
        self.ramFlag = 0
        self.ramValue = 0
        self.clockRegister = 0
        self.clockShift = 0
        self.clockTime = self.clock.getTime()


    def read(self, address):
        if (address >= 0xA000 and address <= 0xBFFF):# A000-BFFF
            if (self.ramFlag == 0x0C):
                return self.ramValue
            elif (self.ramFlag == 0x0D):
                return 0x01
            elif (self.ramFlag == 0x0A or self.ramFlag == 0x00):
                if (self.ramSize > 0):
                    return self.ram[self.ramBank + (address & 0x1FFF)] & 0xFF
        else:
            super.read(address)
    
    def write(self, address, data):
        if (address <= 0x1FFF): # 0000-1FFF
            self.ramFlag = data
        elif (address <= 0x3FFF):# 2000-3FFF
            if ((data & 0x7F) == 0):
                data = 1
            self.romBank = ((data & 0x7F) << 14) & self.romSize
        elif (address <= 0x5FFF): # 4000-5FFF
            self.ramBank = ((data & 0x0F) << 13) & self.ramSize
        elif (address >= 0xA000 and address <= 0xBFFF): # A000-BFFF
            if (self.ramFlag == 0x0B):
                self.writeWithRamFlag0x0B(address, data)
            elif (self.ramFlag >= 0x0C and self.ramFlag <= 0x0E):
                pass
            elif (self.ramFlag == 0x0A and self.ramSize > 0):
                self.ram[self.ramBank + (address & 0x1FFF)] = data
         
                    
    def writeWithRamFlag0x0B(self, address, data):
        if ((data & 0xF0) == 0x10):
            if (self.clockShift <= 24):
                self.ramValue = (self.clockRegister >> self.clockShift) & 0x0F
                self.clockShift += 4
        elif ((data & 0xF0) == 0x30):
            if (self.clockShift <= 24):
                self.clockRegister &= ~(0x0F << self.clockShift)
                self.clockRegister |= ((data & 0x0F) << self.clockShift)
                self.clockShift += 4
        elif ((data & 0xF0) == 0x40):
            self.updateClock()
            if ((data & 0x0F) == 0x00):
                self.clockShift = 0
            elif ((data & 0x0F) == 0x03):
                self.clockShift = 0
            elif ((data & 0x0F) == 0x07):
                self.clockShift = 0
        elif ((data & 0xF0) == 0x50):
            pass
        elif ((data & 0xF0) == 0x60):
            self.ramValue = 0x01
         
                    
    def updateClock(self):
        now = self.clock.getTime()
        elapsed = now - self.clockTime
        # years (4 bits)
        while (elapsed >= 365246060):
            self.clockRegister += 1 << 24
            elapsed -= 365246060
        # days (12 bits)
        while (elapsed >= 246060):
            self.clockRegister += 1 << 12
            elapsed -= 246060
        # minutes (12 bits)
        while (elapsed >= 60):
            self.clockRegister += 1
            elapsed -= 60
        if ((self.clockRegister & 0x0000FFF) >= 2460):
            self.clockRegister += (1 << 12) - 2460
        if ((self.clockRegister & 0x0FFF000) >= (365 << 12)):
            self.clockRegister += (1 << 24) - (365 << 12)
        self.clockTime = now - elapsed



CATRIDGE_TYPE_RANGES = [
   (constants.TYPE_MBC1,             constants.TYPE_MBC1_RAM_BATTERY,        MBC1),
   (constants.TYPE_MBC2,             constants.TYPE_MBC2_BATTERY,            MBC2),
   (constants.TYPE_MBC3_RTC_BATTERY, constants.TYPE_MBC3_RAM_BATTERY,        MBC3),
   (constants.TYPE_MBC5,             constants.TYPE_MBC5_RUMBLE_RAM_BATTERY, MBC5),
   (constants.TYPE_HUC3_RTC_RAM,     constants.TYPE_HUC3_RTC_RAM,            HuC3),
   (constants.TYPE_HUC1_RAM_BATTERY, constants.TYPE_HUC1_RAM_BATTERY,        HuC1)
]


