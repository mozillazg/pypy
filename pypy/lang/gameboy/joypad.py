"""
Mario GameBoy (TM) Emulator
 
Joypad Input
"""

class Joypad(object):
	# Joypad Registers
	JOYP = 0xFF00; # P1 */

	# Gameboy Clock Speed (1048576 Hz)
	GAMEBOY_CLOCK = 1 << 20;

	# Joypad Poll Speed (64 Hz)
	JOYPAD_CLOCK = GAMEBOY_CLOCK >> 6;

	# Registers
	joyp = 0;
	cycles = 0;

	# Interrupt Controller
	interrupt = None;

	# Driver JoypadDriver
	driver = None;

	def __init__(self, joypadDriver, interrupt):
		self.driver = joypadDriver;
		self.interrupt = interrupt;
		self.reset();

	def  reset(self):
		self.joyp = 0xFF;
		self.cycles = JOYPAD_CLOCK;

	def cycles(self):
		return self.cycles;

	def  emulate(self, ticks):
		self.cycles -= ticks;
		if (self.cycles <= 0):
			if (self.driver.isRaised()):
				self.update();

			self.cycles = JOYPAD_CLOCK;

	def  write(self, address, data):
		if (address == JOYP):
			self.joyp = (self.joyp & 0xCF) + (data & 0x30);
			self.update();

	def read(self, address):
		if (address == JOYP):
			return self.joyp;
		return 0xFF;

	def update(self):
		data = self.joyp & 0xF0;

		switch = (data & 0x30)
		if switch==0x10:
			data |= self.driver.getButtons();
		elif switch==0x20:
			data |= self.driver.getDirections();
		elif switch==0x30:
			data |= 0x0F;

		if ((self.joyp & ~data & 0x0F) != 0):
			self.interrupt.raiseInterrupt(Interrupt.JOYPAD);

		self.joyp = data;

