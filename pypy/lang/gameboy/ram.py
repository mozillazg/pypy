"""
Mario GameBoy (TM) Emulator

Work and High RAM
"""
class RAM(object):
	
	WRAM_SIZE = 8192
	HIGH_SIZE = 128
	
	# Work RAM
	wram = []

	# High RAM
	hram = []

	def __init__(self):
		self.reset();

	def reset(self):
		self.wram = range(0, WRAM_SIZE)
		for index in range(0, WRAM_SIZE):
			#TODO convert to byte
			self.wram[index] =  0x00;

		self.hram = range(0, HIGH_SIZE)
		for index in range(0, HIGH_SIZE):
			#TODO convert to byte
			self.hram[index] =  0x00;

	def write(self, address, data):
		if (address >= 0xC000 and address <= 0xFDFF):
			# C000-DFFF Work RAM (8KB)
			# E000-FDFF Echo RAM
			#TODO convert to byte
			self.wram[address & 0x1FFF] = data;
		elif (address >= 0xFF80 and address <= 0xFFFE):
			# FF80-FFFE High RAM
			#TODO convert to byte
			self.hram[address & 0x7F] = data;

	def read(self, address):
		if (address >= 0xC000 and address <= 0xFDFF):
			# C000-DFFF Work RAM
			# E000-FDFF Echo RAM
			return self.wram[address & 0x1FFF] & 0xFF;
		elif (address >= 0xFF80 and address <= 0xFFFE):
			# FF80-FFFE High RAM
			return self.hram[address & 0x7F] & 0xFF;
		return 0xFF;
