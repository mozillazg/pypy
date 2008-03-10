# CATRIGE TYPES
# ___________________________________________________________________________


TYPE_ROM_ONLY = 0x00

TYPE_MBC1 = 0x01
TYPE_MBC1_RAM = 0x02
TYPE_MBC1_RAM_BATTERY = 0x03

TYPE_MBC2 = 0x05
TYPE_MBC2_BATTERY = 0x06

TYPE_MBC3_RTC_BATTERY = 0x0F
TYPE_MBC3_RTC_RAM_BATTERY = 0x10
TYPE_MBC3 = 0x11
TYPE_MBC3_RAM = 0x12
TYPE_MBC3_RAM_BATTERY = 0x13

TYPE_MBC5 = 0x19
TYPE_MBC5_RAM = 0x1A
TYPE_MBC5_RAM_BATTERY = 0x1B

TYPE_MBC5_RUMBLE = 0x1C
TYPE_MBC5_RUMBLE_RAM = 0x1D
TYPE_MBC5_RUMBLE_RAM_BATTERY = 0x1E

TYPE_HUC3_RTC_RAM = 0xFE
TYPE_HUC1_RAM_BATTERY = 0xFF

CATRIDGE_TYPE_MAPPING = {
						TYPE_ROM_ONLY: MBC1,
						TYPE_MBC1:  MBC1,
						TYPE_MBC1_RAM: MBC1,
						TYPE_MBC1_RAM_BATTERY: MBC1,
						TYPE_MBC2: MBC2,
						TYPE_MBC2_BATTERY: MBC2,
						TYPE_MBC3_RTC_BATTERY: MBC3,
						TYPE_MBC3_RTC_RAM_BATTERY: MBC3,
						TYPE_MBC3: MBC3,
						TYPE_MBC3_RAM: MBC3,
						TYPE_MBC3_RAM_BATTERY: MBC3,
						TYPE_MBC5: MBC5,
						TYPE_MBC5_RAM: MBC5,
						TYPE_MBC5_RAM_BATTERY: MBC5,
						TYPE_MBC5_RUMBLE: MBC5,
						TYPE_MBC5_RUMBLE_RAM: MBC5,
						TYPE_MBC5_RUMBLE_RAM_BATTERY: MBC5,
						TYPE_HUC3_RTC_RAM: HuC3,
						TYPE_HUC1_RAM_BATTERY: HuC1
						};



def hasCartridgeBattery(self, cartridgeType):	
	return (cartridgeType == TYPE_MBC1_RAM_BATTERY \
				or cartridgeType == TYPE_MBC2_BATTERY \
				or cartridgeType == TYPE_MBC3_RTC_BATTERY \
				or cartridgeType == TYPE_MBC3_RTC_RAM_BATTERY \
				or cartridgeType == TYPE_MBC3_RAM_BATTERY \
				or cartridgeType == TYPE_MBC5_RAM_BATTERY \
				or cartridgeType == TYPE_MBC5_RUMBLE_RAM_BATTERY \
				or cartridgeType == TYPE_HUC1_RAM_BATTERY);


def hasCartridgeType(self, catridgeType):
	return CATRIDGE_TYPE_MAPPING.has_key(cartridgeType);	


def createBankController(self, cartridgeType, rom, ram, clock):
		if hasCartridgeType(cartridgeType):
			return CATRIDGE_TYPE_MAPPING[cartridgeType](rom, ram, clock);
		else:
			raise InvalidMemoryBankTypeError("Unsupported memory bank controller (0x"+hex(cartridgeType)+")")


class InvalidMemoryBankTypeError(Exception):
	pass



# ______________________________________________________________________________
# CARTRIDGE

class Cartridge(object):
	
	CARTRIDGE_TYPE_ADDRESS = 0x0147
	ROM_SIZE_ADDRESS = 0x0148
	RAM_SIZE_ADDRESS = 0x0149
	RAM_SIZE_MAPPING = {0x00:0, 0x01:8192, 0x02:8192, 0x03:32768}
	DESTINATION_CODE_ADDRESS = 0x014A
	LICENSEE_ADDRESS = 0x014B
	ROM_VERSION_ADDRESS = 0x014C
	HEADER_CHECKSUM_ADDRESS = 0x014D
	CHECKSUM_A_ADDRESS = 0x014E
	CHECKSUM_B_ADDRESS = 0x014F

	def __init__(self, storeDriver, clockDriver):
		self.store = storeDriver
		self.clock = clockDriver
	
	def initialize(self):
	 	pass
	
	def getTitle(self):
		pass
		
	def getCartridgeType(self):
		return self.rom[CARTRIDGE_TYPE_ADDRESS] & 0xFF
		
	def getRom(self):
		return self.rom
		
	def getROMSize(self):
		romSize = self.rom[CARTRIDGE_SIZE_ADDRESS] & 0xFF
		if romSize>=0x00 and romSize<=0x07:
			return 32768 << romSize
		return -1
	
		
	def getRAMSize(self):
		return RAM_SIZE_MAPPING[self.rom[RAM_SIZE_ADDRESS]]
		
	def getDestinationCode(self):
		return self.rom[DESTINATION_CODE_ADDRESS] & 0xFF;

	def getLicenseeCode():
		return self.rom[LICENSEE_ADDRESS] & 0xFF;

	def getROMVersion(self):
		return self.rom[ROM_VERSION_ADDRESS] & 0xFF;

	def getHeaderChecksum(self):
		return self.rom[HEADER_CHECKSUM_ADDRESS] & 0xFF;

	def getChecksum(self):
		return ((rom[CHECKSUM_A_ADDRESS] & 0xFF) << 8) + (rom[CHECKSUM_B_ADDRESS] & 0xFF);

	def hasBattery(self):
		return hasCartridgeBattery(self.getCartridgeType())

	def reset(self):
		if not self.hasBattery():
			self.ram[0:len(self.ram):1] = 0xFF;
		self.mbc.reset();

	def read(self, address):
		return self.mbc.read(address);

	def write(self, address, data):
		self.mbc.write(address, data);

	def load(self, cartridgeName):
		romSize = self.store.getCartridgeSize(cartridgeName);
		self.rom = []
		self.rom[0:romSize:1] = 0
		self.store.readCartridge(cartridgeName, self.rom)
		
		if not self.verifyHeader():
			raise Exeption("Cartridge header is corrupted")
		if romSize < self.getROMSize():
			raise Exeption("Cartridge is truncated")
		
		ramSize = self.getRAMSize()
		if (getCartridgeType() >= CartridgeFactory.TYPE_MBC2
				and getCartridgeType() <= CartridgeFactory.TYPE_MBC2_BATTERY):
			ramSize = 512;
		self.ram = []
		self.ram[0:ramSize:1] = 0xFF
		if self.store.hasBattery(cartridgeName):
			self.store.readBattery(cartridgeName, ram)
		self.mbc = createBankController(self.getCartridgeType(), rom, ram, clock)

	def save(self, cartridgeName):
		if self.hasBattery():
			self.store.writeBattery(cartridgeName, self.ram)

	def verify(self):
		checksum = 0;
		for address in range(len(self.rom)):
			if address is not 0x014E and address is not 0x014F:
				checksum = (checksum + (self.rom[address] & 0xFF)) & 0xFFFF
		return (checksum == self.getChecksum());

	def verifyHeader(self):
		if self.rom.length < 0x0150:
			return false;
		checksum = 0xE7;
		for address in range(0x0134,0x014C):
			checksum = (checksum - (rom[address] & 0xFF)) & 0xFF;
		return (checksum == self.getHeaderChecksum())

		
