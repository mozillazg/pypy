"""
Mario GameBoy (TM) Emulator

Interrupt Controller
"""

class Interrupt(object):

	 # Interrupt Registers
	IE = 0xFFFF # Interrupt Enable */
	IF = 0xFF0F # Interrupt Flag */

	 # Interrupt Flags
	VBLANK = 0x01 # V-Blank Interrupt (INT 40h) */
	LCD = 0x02 # LCD STAT Interrupt (INT 48h) */
	TIMER = 0x04 # Timer Interrupt (INT 50h) */
	SERIAL = 0x08 # Serial Interrupt (INT 58h) */
	JOYPAD = 0x10 # Joypad Interrupt (INT 60h) */

	 # Registers
	enable = 0;
	flag = 0;

	def __init__(self):
		self.reset();


	def reset(self):
		self.enable = 0;
		self.flag = VBLANK;


	def isPending(self):
		return (self.enable & self.flag) != 0;


	def isPending(self, mask):
		return (self.enable & self.flag & mask) != 0;


	def raiseInterrupt(self, mask):
		self.flag |= mask;


	def lower(self, mask):
		self.flag &= ~mask;


	def write(self, address, data):
		if  address == IE:
			self.setInterruptEnable(data);
		elif address==IF:
			self.setInterruptFlag(data);


	def read(self, address):
		if  address==IE:
			return self.getInterruptEnable();
		elif address== IF:
			return self.getInterruptFlag();
		return 0xFF;


	def getInterruptEnable(self):
		return self.enable;


	def getInterruptFlag(self):
		return 0xE0 | self.flag;


	def setInterruptEnable(self, data):
		self.enable = data;


	def setInterruptFlag(self, data):
		self.flag = data;
