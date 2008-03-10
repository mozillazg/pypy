"""
Mario GameBoy (TM) Emulator
Serial Link Controller
 """
class Serial(object):
	 # Gameboy Clock Speed (1048576 Hz)
	GAMEBOY_CLOCK = 1 << 20;

	 # Serial Clock Speed (8 x 1024 bits/sec)
	SERIAL_CLOCK = GAMEBOY_CLOCK >> 16;

	 # Serial Idle Speed (128 Hz)
	SERIAL_IDLE_CLOCK = GAMEBOY_CLOCK >> 7;

	 # Serial Register Addresses

	SB = 0xFF01; #Serial Transfer Data */
	SC = 0xFF02; # Serial Transfer Control */

	 # Registers
	sb;
	sc;
	cycles;

	 # Interrupt Controller #Interrupt
	interrupt;

	def __init__(self, interrupt):
		self.interrupt = interrupt;
		self.reset();

	def reset(self):
		self.cycles = SERIAL_CLOCK;
		self.sb = 0x00;
		self.sc = 0x00;

	def cycles(self):
		return self.cycles;

	def emulate(self, ticks):
		if ((self.sc & 0x81) == 0x81):
			self.cycles -= ticks;

			if (self.cycles <= 0):
				self.sb = 0xFF;
				self.sc &= 0x7F;
				self.cycles = SERIAL_IDLE_CLOCK;

				self.interrupt.raise(Interrupt.SERIAL);


	def setSerialData(self, data):
		self.sb = data;

	def setSerialControl(self, data):
		self.sc = data;

		# HACK: delay the serial interrupt (Shin Nihon Pro Wrestling)
		self.cycles = SERIAL_IDLE_CLOCK + SERIAL_CLOCK;

	def getSerialData(self):
		return self.sb;

	def getSerialControl(self):
		return self.sc;
