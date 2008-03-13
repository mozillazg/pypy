"""
Mario GameBoy (TM) Emulator
 
Gameboy Scheduler and Memory Mapper

"""
from pypy.lang.gameboy import constants

class GameBoy(object):

	# RAM
	ram = None;
	cartridge = None;
	interrupt = None;
	cpu = None;
	serial = None;
	timer = None;
	joypad = None;
	video = None;
	sound = None;

	def __init__(self, videoDriver, soundDriver, joypadDriver, storeDriver, clockDriver):
		self.ram = RAM();
		self.cartridge = Cartridge(storeDriver, clockDriver);
		self.interrupt = Interrupt();
		self.cpu = CPU(self.interrupt, this);
		self.serial = Serial(self.interrupt);
		self.timer = Timer(self.interrupt);
		self.joypad = Joypad(joypadDriver, self.interrupt);
		self.video = Video(videoDriver, self.interrupt, this);
		self.sound = Sound(soundDriver);


	def getCartridge(self):
		return self.cartridge;


	def getFrameSkip(self):
		return self.video.getFrameSkip();


	def setFrameSkip(self, frameSkip):
		self.video.setFrameSkip(frameSkip);


	def load(self, cartridgeName):
		self.cartridge.load(cartridgeName);


	def save(self, cartridgeName):
		self.cartridge.save(cartridgeName);


	def start(self):
		self.sound.start();


	def stop(self):
		self.sound.stop();


	def reset(self):
		self.ram.reset();
		self.cartridge.reset();
		self.interrupt.reset();
		self.cpu.reset();
		self.serial.reset();
		self.timer.reset();
		self.joypad.reset();
		self.video.reset();
		self.sound.reset();
		self.cpu.setROM(self.cartridge.getROM());
		self.drawLogo();


	def cycles(self):
		return min(self.video.cycles(), self.serial.cycles(),
					self.timer.cycles(), self.sound.cycles(),
					self.joypad.cycles());


	def emulate(self, ticks):
		while (ticks > 0):
			count = self.cycles();

			self.cpu.emulate(count);
			self.serial.emulate(count);
			self.timer.emulate(count);
			self.video.emulate(count);
			self.sound.emulate(count);
			self.joypad.emulate(count);

			ticks -= count;
	


	def write(self, address, data):
	(0x0000, 0x7FFF,Gameboy.cartridge),
	(0x8000, 0x9FFF, Gameboy.video),
	(0xA000, 0xBFFF, Gameboy.cartridge),
	(0xC000, 0xFDFF, Gameboy.ram),
	(0xFE00, 0xFEFF, Gameboy.video),
	(0xFF00, 0xFF00, Gameboy.joypad),
	(0xFF01, 0xFF02, Gameboy.serial),
	(0xFF04, 0xFF07, Gameboy.timer),
	(0xFF0F, 0xFF0F, Gameboy.interrupt),
	(0xFF10, 0xFF3F, Gameboy.sound),
	(0xFF40, 0xFF4B, Gameboy.video),
	(0xFF80, 0xFFFE, Gameboy.ram),
	(0xFFFF, 0xFFFF, Gameboy.interrupt)
]
	


	def read(self, address):
		if (address <= 0x7FFF):
			# 0000-7FFF ROM Bank
			return self.cartridge.read(address);
		elif (address <= 0x9FFF):
			# 8000-9FFF Video RAM
			return self.video.read(address);
		elif (address <= 0xBFFF):
			# A000-BFFF External RAM
			return self.cartridge.read(address);
		elif (address <= 0xFDFF):
			# C000-FDFF Work RAM
			return self.ram.read(address);
		elif (address <= 0xFEFF):
			# FE00-FEFF OAM
			return self.video.read(address);
		elif (address == 0xFF00):
			# FF00-FF00 Joypad
			return self.joypad.read(address);
		elif (address >= 0xFF01 and address <= 0xFF02):
			# FF01-FF02 Serial
			return self.serial.read(address);
		elif (address >= 0xFF04 and address <= 0xFF07):
			# FF04-FF07 Timer
			return self.timer.read(address);
		elif (address == 0xFF0F):
			# FF0F-FF0F Interrupt
			return self.interrupt.read(address);
		elif (address >= 0xFF10 and address <= 0xFF3F):
			# FF10-FF3F Sound
			return self.sound.read(address);
		elif (address >= 0xFF40 and address <= 0xFF4B):
			# FF40-FF4B Video
			return self.video.read(address);
		elif (address >= 0xFF80 and address <= 0xFFFE):
			# FF80-FFFE High RAM
			return self.ram.read(address);
		elif (address == 0xFFFF):
			# FFFF-FFFF Interrupt
			return self.interrupt.read(address);
		else:
			return 0xFF;


	def drawLogo(self):
		for index in range(0, 48):
			bits = self.cartridge.read(0x0104 + index);
			pattern0 = ((bits >> 0) & 0x80) + ((bits >> 1) & 0x60)\
					+ ((bits >> 2) & 0x18) + ((bits >> 3) & 0x06)\
					+ ((bits >> 4) & 0x01);

			pattern1 = ((bits << 4) & 0x80) + ((bits << 3) & 0x60)\
					+ ((bits << 2) & 0x18) + ((bits << 1) & 0x06)\
					+ ((bits << 0) & 0x01);

			self.video.write(0x8010 + (index << 3), pattern0);
			self.video.write(0x8012 + (index << 3), pattern0);

			self.video.write(0x8014 + (index << 3), pattern1);
			self.video.write(0x8016 + (index << 3), pattern1);

		for index in range(0, 8):
			self.video.write(0x8190 + (index << 1), constants.REGISTERED_BITMAP[index]);

		for tile in range(0, 12):
			self.video.write(0x9904 + tile, tile + 1);
			self.video.write(0x9924 + tile, tile + 13);

		self.video.write(0x9905 + 12, 25);


	(0x0000, 0x7FFF, Gameboy.cartridge),
	(0x8000, 0x9FFF, Gameboy.video),
	(0xA000, 0xBFFF, Gameboy.cartridge),
	(0xC000, 0xFDFF, Gameboy.ram),
	(0xFE00, 0xFEFF, Gameboy.video),
	(0xFF00, 0xFF00, Gameboy.joypad),
	(0xFF01, 0xFF02, Gameboy.serial),
	(0xFF04, 0xFF07, Gameboy.timer),
	(0xFF0F, 0xFF0F, Gameboy.interrupt),
	(0xFF10, 0xFF3F, Gameboy.sound),
	(0xFF40, 0xFF4B, Gameboy.video),
	(0xFF80, 0xFFFE, Gameboy.ram),
	(0xFFFF, 0xFFFF, Gameboy.interrupt)
]
