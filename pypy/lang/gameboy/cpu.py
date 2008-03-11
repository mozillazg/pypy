"""
Mario GameBoy (TM) EmulatOR

Central Unit ProcessOR (Sharp LR35902 CPU)
"""

class CPU(object):
	 # Flags
	Z_FLAG = 0x80
	N_FLAG = 0x40
	H_FLAG = 0x20
	C_FLAG = 0x10

	# Registers
	a = 0
	b = 0
	c = 0
	d = 0
	f = 0
	d = 0
	l = 0
	sp = 0;
	pc = 0;

	# Interrupt Flags
	ime = False;
	halted  = False;
	cycles  = 0;

	# Interrupt Controller
	#Interrupt 
	interrupt = None;

	 # memory Access
	#memory
	memory = None;


	# ROM Access
	rom = [];

	def __init__(self, interrupt, memory):
		self.interrupt = interrupt;
		self.memory = memory;
		self.reset();


	def getBC():
		return (self.b << 8) + self.c;


	def getDE():
		return (self.d << 8) + self.e;


	def getHL():
		return (self.h << 8) + self.l;


	def getSP():
		return self.sp;


	def getPC():
		return self.pc;


	def getAF():
		return (self.a << 8) + self.f;


	def getIF():
		val = 0x00
		#if (self.ime ? 0x01 : 0x00) + (self.halted ? 0x80 : 0x00);
		if self.ime:
			val = 0x01
		if self.halted:
			val += 0x80
		return val
			

	def setROM(self, banks):
		self.rom = banks;


	def reset():
		self.a = 0x01;
		self.f = 0x80;
		self.b = 0x00;
		self.c = 0x13;
		self.d = 0x00;
		self.e = 0xD8;
		self.h = 0x01;
		self.l = 0x4D;
		self.sp = 0xFFFE;
		self.pc = 0x0100;

		self.ime = false;
		self.halted = false;

		self.cycles = 0;


	def emulate(self, ticks):
		self.cycles += ticks;

		self.interrupt();

		while (self.cycles > 0):
			self.execute();


	 # Interrupts
	def interrupt():
		if (self.halted):
			if (self.interrupt.isPending()):
				self.halted = false;
				# Zerd no Densetsu
				self.cycles -= 4;
			elif (self.cycles > 0):
				self.cycles = 0;
		if (self.ime):
			if (self.interrupt.isPending()):
				if (self.interrupt.isPending(Interrupt.VBLANK)):
					self.interrupt(0x40);
					self.interrupt.lower(Interrupt.VBLANK);
				elif (self.interrupt.isPending(Interrupt.LCD)):
					self.interrupt(0x48);
					self.interrupt.lower(Interrupt.LCD);
				elif (self.interrupt.isPending(Interrupt.TIMER)):
					self.interrupt(0x50);
					self.interrupt.lower(Interrupt.TIMER);
				elif (self.interrupt.isPending(Interrupt.SERIAL)):
					self.interrupt(0x58);
					self.interrupt.lower(Interrupt.SERIAL);
				elif (self.interrupt.isPending(Interrupt.JOYPAD)):
					self.interrupt(0x60);
					self.interrupt.lower(Interrupt.JOYPAD);
			

	def interrupt(self, address):
		self.ime = false;
		self.call(address);


	 # Execution
	def execute():
		self.execute(self.fetch());


	def execute(self, opcode):
		result = { 0x00:self.nop(),
			# LD (nnnn),SP
			0x08:self.load_mem_SP(),
	
			# STOP
			0x10:self.stop(),
	
			# JR nn
			0x18:self.jr_nn(),
	
			# JR cc,nn
			0x20:self.jr_NZ_nn(),
			0x28:self.jr_Z_nn(),
			0x30:self.jr_NC_nn(),
			0x38:self.jr_C_nn(),
	
			# LD rr,nnnn
			0x01:self.ld_BC_nnnn(),
			0x11:self.ld_DE_nnnn(),
			0x21:self.ld_HL_nnnn(),
			0x31:self.ld_SP_nnnn(),
	
			# ADD HL,rr
			0x09:self.add_HL_BC(),
			0x19:self.add_HL_DE(),
			0x29:self.add_HL_HL(),
			0x39:self.add_HL_SP(),
	
			# LD (BC),A
			0x02:self.ld_BCi_A(),
	
			# LD A,(BC)
			0x0A:self.ld_A_BCi(),
	
			# LD (DE),A
			0x12:self.ld_DEi_A(),
	
			# LD A,(DE)
			0x1A:self.load_A_DEi(),
	
			# LDI (HL),A
			0x22:self.ldi_HLi_A(),
	
			# LDI A,(HL)
			0x2A:self.ldi_A_HLi(),
	
			# LDD (HL),A
			0x32:self.ldd_HLi_A(),
	
			# LDD A,(HL)
			0x3A:self.ldd_A_HLi(),
	
			# INC rr
			0x03:self.inc_BC(),
			0x13:self.inc_DE(),
			0x23:self.inc_HL(),
			0x33:self.inc_SP(),
	
			# DEC rr
			0x0B:self.dec_BC(),
			0x1B:self.dec_DE(),
			0x2B:self.dec_HL(),
			0x3B:self.dec_SP(),
	
			# INC r
			0x04:self.inc_B(),
			0x0C:self.inc_C(),
			0x14:self.inc_D(),
			0x1C:self.inc_E(),
			0x24:self.inc_H(),
			0x2C:self.inc_L(),
			0x34:self.inc_HLi(),
			0x3C:self.inc_A(),
	
			# DEC r
			0x05:self.dec_B(),
			0x0D:self.dec_C(),
			0x15:self.dec_D(),
			0x1D:self.dec_E(),
			0x25:self.dec_H(),
			0x2D:self.dec_L(),
			0x35:self.dec_HLi(),
			0x3D:self.dec_A(),
	
			# LD r,nn
			0x06:self.ld_B_nn(),
			0x0E:self.ld_C_nn(),
			0x16:self.ld_D_nn(),
			0x1E:self.ld_E_nn(),
			0x26:self.ld_H_nn(),
			0x2E:self.ld_L_nn(),
			0x36:self.ld_HLi_nn(),
			0x3E:self.ld_A_nn(),
	
			# RLCA
			0x07:self.rlca(),
	
			# RRCA
			0x0F:self.rrca(),
	
			# RLA
			0x17:self.rla(),
	
			# RRA
			0x1F:self.rra(),
	
			# DAA
			0x27:self.daa(),
	
			# CPL
			0x2F:self.cpl(),
	
			# SCF
			0x37:self.scf(),
	
			# CCF
			0x3F:self.ccf(),
	
			# HALT
			0x76:self.halt(),
	
			# LD r,s
			0x40:self.ld_B_B(),
			0x41:self.ld_B_C(),
			0x42:self.ld_B_D(),
			0x43:self.ld_B_E(),
			0x44:self.ld_B_H(),
			0x45:self.ld_B_L(),
			0x46:self.ld_B_HLi(),
			0x47:self.ld_B_A(),
	
			0x48:self.ld_C_B(),
			0x49:self.ld_C_C(),
			0x4A:self.ld_C_D(),
			0x4B:self.ld_C_E(),
			0x4C:self.ld_C_H(),
			0x4D:self.ld_C_L(),
			0x4E:self.ld_C_HLi(),
			0x4F:self.ld_C_A(),
	
			0x50:self.ld_D_B(),
			0x51:self.ld_D_C(),
			0x52:self.ld_D_D(),
			0x53:self.ld_D_E(),
			0x54:self.ld_D_H(),
			0x55:self.ld_D_L(),
			0x56:self.ld_D_HLi(),
			0x57:self.ld_D_A(),
	
			0x58:self.ld_E_B(),
			0x59:self.ld_E_C(),
			0x5A:self.ld_E_D(),
			0x5B:self.ld_E_E(),
			0x5C:self.ld_E_H(),
			0x5D:self.ld_E_L(),
			0x5E:self.ld_E_HLi(),
			0x5F:self.ld_E_A(),
	
			0x60:self.ld_H_B(),
			0x61:self.ld_H_C(),
			0x62:self.ld_H_D(),
			0x63:self.ld_H_E(),
			0x64:self.ld_H_H(),
			0x65:self.ld_H_L(),
			0x66:self.ld_H_HLi(),
			0x67:self.ld_H_A(),
	
			0x68:self.ld_L_B(),
			0x69:self.ld_L_C(),
			0x6A:self.ld_L_D(),
			0x6B:self.ld_L_E(),
			0x6C:self.ld_L_H(),
			0x6D:self.ld_L_L(),
			0x6E:self.ld_L_HLi(),
			0x6F:self.ld_L_A(),
	
			0x70:self.ld_HLi_B(),
			0x71:self.ld_HLi_C(),
			0x72:self.ld_HLi_D(),
			0x73:self.ld_HLi_E(),
			0x74:self.ld_HLi_H(),
			0x75:self.ld_HLi_L(),
			0x77:self.ld_HLi_A(),
	
			0x78:self.ld_A_B(),
			0x79:self.ld_A_C(),
			0x7A:self.ld_A_D(),
			0x7B:self.ld_A_E(),
			0x7C:self.ld_A_H(),
			0x7D:self.ld_A_L(),
			0x7E:self.ld_A_HLi(),
			0x7F:self.ld_A_A(),
	
			# ADD A,r
			0x80:self.add_A_B(),
			0x81:self.add_A_C(),
			0x82:self.add_A_D(),
			0x83:self.add_A_E(),
			0x84:self.add_A_H(),
			0x85:self.add_A_L(),
			0x86:self.add_A_HLi(),
			0x87:self.add_A_A(),
	
			# ADC A,r
			0x88:self.adc_A_B(),
			0x89:self.adc_A_C(),
			0x8A:self.adc_A_D(),
			0x8B:self.adc_A_E(),
			0x8C:self.adc_A_H(),
			0x8D:self.adc_A_L(),
			0x8E:self.adc_A_HLi(),
			0x8F:self.adc_A_A(),
	
			# SUB A,r
			0x90:self.sub_A_B(),
			0x91:self.sub_A_C(),
			0x92:self.sub_A_D(),
			0x93:self.sub_A_E(),
			0x94:self.sub_A_H(),
			0x95:self.sub_A_L(),
			0x96:self.sub_A_HLi(),
			0x97:self.sub_A_A(),
	
			# SBC A,r
			0x98:self.sbc_A_B(),
			0x99:self.sbc_A_C(),
			0x9A:self.sbc_A_D(),
			0x9B:self.sbc_A_E(),
			0x9C:self.sbc_A_H(),
			0x9D:self.sbc_A_L(),
			0x9E:self.sbc_A_HLi(),
			0x9F:self.sbc_A_A(),
	
			# AND A,r
			0xA0:self.AND_A_B(),
			0xA1:self.AND_A_C(),
			0xA2:self.AND_A_D(),
			0xA3:self.AND_A_E(),
			0xA4:self.AND_A_H(),
			0xA5:self.AND_A_L(),
			0xA6:self.AND_A_HLi(),
			0xA7:self.AND_A_A(),
	
			# XOR A,r
			0xA8:self.xOR_A_B(),
			0xA9:self.xOR_A_C(),
			0xAA:self.xOR_A_D(),
			0xAB:self.xOR_A_E(),
			0xAC:self.xOR_A_H(),
			0xAD:self.xOR_A_L(),
			0xAE:self.xOR_A_HLi(),
			0xAF:self.xOR_A_A(),
	
			# OR A,r
			0xB0:self.OR_A_B(),
			0xB1:self.OR_A_C(),
			0xB2:self.OR_A_D(),
			0xB3:self.OR_A_E(),
			0xB4:self.OR_A_H(),
			0xB5:self.OR_A_L(),
			0xB6:self.OR_A_HLi(),
			0xB7:self.OR_A_A(),
	
			# CP A,r
			0xB8:self.cp_A_B(),
			0xB9:self.cp_A_C(),
			0xBA:self.cp_A_D(),
			0xBB:self.cp_A_E(),
			0xBC:self.cp_A_H(),
			0xBD:self.cp_A_L(),
			0xBE:self.cp_A_HLi(),
			0xBF:self.cp_A_A(),
	
			# RET cc
			0xC0:self.ret_NZ(),
			0xC8:self.ret_Z(),
			0xD0:self.ret_NC(),
			0xD8:self.ret_C(),
	
			# LDH (nn),A
			0xE0:self.ldh_mem_A(),
	
			# ADD SP,nn
			0xE8:self.add_SP_nn(),
	
			# LDH A,(nn)
			0xF0:self.ldh_A_mem(),
	
			# LD HL,SP+nn
			0xF8:self.ld_HP_SP_nn(),
	
			# POP rr
			0xC1:self.pop_BC(),
			0xD1:self.pop_DE(),
			0xE1:self.pop_HL(),
			0xF1:self.pop_AF(),
	
			# RET
			0xC9:self.ret(),
	
			# RETI
			0xD9:self.reti(),
	
			# LD PC,HL
			0xE9:self.ld_PC_HL(),
	
			# LD SP,HL
			0xF9:self.ld_SP_HL(),
	
			# JP cc,nnnn
			0xC2:self.jp_NZ_nnnn(),
			0xCA:self.jp_Z_nnnn(),
			0xD2:self.jp_NC_nnnn(),
			0xDA:self.jp_C_nnnn(),
	
			# LDH (C),A
			0xE2:self.ldh_Ci_A(),
	
			# LD (nnnn),A
			0xEA:self.ld_mem_A(),
	
			# LDH A,(C)
			0xF2:self.ldh_A_Ci(),
	
			# LD A,(nnnn)
			0xFA:self.ld_A_mem(),
	
			# JP nnnn
			0xC3:self.jp_nnnn(),

		0xCB:self.fetchExecute(),

		# DI
		0xF3:self.di(),

		# EI
		0xFB:self.ei(),

		# CALL cc,nnnn
		0xC4:self.call_NZ_nnnn(),
		0xCC:self.call_Z_nnnn(),
		0xD4:self.call_NC_nnnn(),
		0xDC:self.call_C_nnnn(),

		# PUSH rr
		0xC5:self.push_BC(),
		0xD5:self.push_DE(),
		0xE5:self.push_HL(),
		0xF5:self.push_AF(),

		# CALL nnnn
		0xCD:self.call_nnnn(),

		# ADD A,nn
		0xC6:self.add_A_nn(),

		# ADC A,nn
		0xCE:self.adc_A_nn(),

		# SUB A,nn
		0xD6:self.sub_A_nn(),

		# SBC A,nn
		0xDE:self.sbc_A_nn(),

		# AND A,nn
		0xE6:self.AND_A_nn(),

		# XOR A,nn
		0xEE:self.xOR_A_nn(),

		# OR A,nn
		0xF6:self.OR_A_nn(),

		# CP A,nn
		0xFE:self.cp_A_nn(),

		# RST nn
		0xC7:self.rst(0x00),
		0xCF:self.rst(0x08),
		0xD7:self.rst(0x10),
		0xDF:self.rst(0x18),
		0xE7:self.rst(0x20),
		0xEF:self.rst(0x28),
		0xF7:self.rst(0x30),
		0xFF:self.rst(0x38)
		}[opcode]()
	
		def fetchExecute(self):
			result = {
			# RLC r
			0x00:self.rlc_B(),
			0x01:self.rlc_C(),
			0x02:self.rlc_D(),
			0x03:self.rlc_E(),
			0x04:self.rlc_H(),
			0x05:self.rlc_L(),
			0x06:self.rlc_HLi(),
			0x07:self.rlc_A(),

			# RRC r
			0x08:self.rrc_B(),
			0x09:self.rrc_C(),
			0x0A:self.rrc_D(),
			0x0B:self.rrc_E(),
			0x0C:self.rrc_H(),
			0x0D:self.rrc_L(),
			0x0E:self.rrc_HLi(),
			0x0F:self.rrc_A(),

			# RL r
			0x10:self.rl_B(),
			0x11:self.rl_C(),
			0x12:self.rl_D(),
			0x13:self.rl_E(),
			0x14:self.rl_H(),
			0x15:self.rl_L(),
			0x16:self.rl_HLi(),
			0x17:self.rl_A(),

			# RR r
			0x18:self.rr_B(),
			0x19:self.rr_C(),
			0x1A:self.rr_D(),
			0x1B:self.rr_E(),
			0x1C:self.rr_H(),
			0x1D:self.rr_L(),
			0x1E:self.rr_HLi(),
			0x1F:self.rr_A(),

			# SLA r
			0x20:self.sla_B(),
			0x21:self.sla_C(),
			0x22:self.sla_D(),
			0x23:self.sla_E(),
			0x24:self.sla_H(),
			0x25:self.sla_L(),
			0x26:self.sla_HLi(),
			0x27:self.sla_A(),

			# SRA r
			0x28:self.sra_B(),
			0x29:self.sra_C(),
			0x2A:self.sra_D(),
			0x2B:self.sra_E(),
			0x2C:self.sra_H(),
			0x2D:self.sra_L(),
			0x2E:self.sra_HLi(),
			0x2F:self.sra_A(),

			# SWAP r
			0x30:self.swap_B(),
			0x31:self.swap_C(),
			0x32:self.swap_D(),
			0x33:self.swap_E(),
			0x34:self.swap_H(),
			0x35:self.swap_L(),
			0x36:self.swap_HLi(),
			0x37:self.swap_A(),

			# SRL r
			0x38:self.srl_B(),
			0x39:self.srl_C(),
			0x3A:self.srl_D(),
			0x3B:self.srl_E(),
			0x3C:self.srl_H(),
			0x3D:self.srl_L(),
			0x3E:self.srl_HLi(),
			0x3F:self.srl_A(),

			# BIT 0,r
			0x40:self.bit_B(0),
			0x41:self.bit_C(0),
			0x42:self.bit_D(0),
			0x43:self.bit_E(0),
			0x44:self.bit_H(0),
			0x45:self.bit_L(0),
			0x46:self.bit_HLi(0),
			0x47:self.bit_A(0),

			# BIT 1,r
			0x48:self.bit_B(1),
			0x49:self.bit_C(1),
			0x4A:self.bit_D(1),
			0x4B:self.bit_E(1),
			0x4C:self.bit_H(1),
			0x4D:self.bit_L(1),
			0x4E:self.bit_HLi(1),
			0x4F:self.bit_A(1),

			# BIT 2,r
			0x50:self.bit_B(2),
			0x51:self.bit_C(2),
			0x52:self.bit_D(2),
			0x53:self.bit_E(2),
			0x54:self.bit_H(2),
			0x55:self.bit_L(2),
			0x56:self.bit_HLi(2),
			0x57:self.bit_A(2),

			# BIT 3,r
			0x58:self.bit_B(3),
			0x59:self.bit_C(3),
			0x5A:self.bit_D(3),
			0x5B:self.bit_E(3),
			0x5C:self.bit_H(3),
			0x5D:self.bit_L(3),
			0x5E:self.bit_HLi(3),
			0x5F:self.bit_A(3),

			# BIT 4,r
			0x60:self.bit_B(4),
			0x61:self.bit_C(4),
			0x62:self.bit_D(4),
			0x63:self.bit_E(4),
			0x64:self.bit_H(4),
			0x65:self.bit_L(4),
			0x66:self.bit_HLi(4),
			0x67:self.bit_A(4),

			# BIT 5,r
			0x68:self.bit_B(5),
			0x69:self.bit_C(5),
			0x6A:self.bit_D(5),
			0x6B:self.bit_E(5),
			0x6C:self.bit_H(5),
			0x6D:self.bit_L(5),
			0x6E:self.bit_HLi(5),
			0x6F:self.bit_A(5),

			# BIT 6,r
			0x70:self.bit_B(6),
			0x71:self.bit_C(6),
			0x72:self.bit_D(6),
			0x73:self.bit_E(6),
			0x74:self.bit_H(6),
			0x75:self.bit_L(6),
			0x76:self.bit_HLi(6),
			0x77:self.bit_A(6),

			# BIT 7,r
			0x78:self.bit_B(7),
			0x79:self.bit_C(7),
			0x7A:self.bit_D(7),
			0x7B:self.bit_E(7),
			0x7C:self.bit_H(7),
			0x7D:self.bit_L(7),
			0x7E:self.bit_HLi(7),
			0x7F:self.bit_A(7),

			# SET 0,r
			0xC0:self.set_B(0),
			0xC1:self.set_C(0),
			0xC2:self.set_D(0),
			0xC3:self.set_E(0),
			0xC4:self.set_H(0),
			0xC5:self.set_L(0),
			0xC6:self.set_HLi(0),
			0xC7:self.set_A(0),

			# SET 1,r
			0xC8:self.set_B(1),
			0xC9:self.set_C(1),
			0xCA:self.set_D(1),
			0xCB:self.set_E(1),
			0xCC:self.set_H(1),
			0xCD:self.set_L(1),
			0xCE:self.set_HLi(1),
			0xCF:self.set_A(1),

			# SET 2,r
			0xD0:self.set_B(2),
			0xD1:self.set_C(2),
			0xD2:self.set_D(2),
			0xD3:self.set_E(2),
			0xD4:self.set_H(2),
			0xD5:self.set_L(2),
			0xD6:self.set_HLi(2),
			0xD7:self.set_A(2),

			# SET 3,r
			0xD8:self.set_B(3),
			0xD9:self.set_C(3),
			0xDA:self.set_D(3),
			0xDB:self.set_E(3),
			0xDC:self.set_H(3),
			0xDD:self.set_L(3),
			0xDE:self.set_HLi(3),
			0xDF:self.set_A(3),

			# SET 4,r
			0xE0:self.set_B(4),
			0xE1:self.set_C(4),
			0xE2:self.set_D(4),
			0xE3:self.set_E(4),
			0xE4:self.set_H(4),
			0xE5:self.set_L(4),
			0xE6:self.set_HLi(4),
			0xE7:self.set_A(4),

			# SET 5,r
			0xE8:self.set_B(5),
			0xE9:self.set_C(5),
			0xEA:self.set_D(5),
			0xEB:self.set_E(5),
			0xEC:self.set_H(5),
			0xED:self.set_L(5),
			0xEE:self.set_HLi(5),
			0xEF:self.set_A(5),

			# SET 6,r
			0xF0:self.set_B(6),
			0xF1:self.set_C(6),
			0xF2:self.set_D(6),
			0xF3:self.set_E(6),
			0xF4:self.set_H(6),
			0xF5:self.set_L(6),
			0xF6:self.set_HLi(6),
			0xF7:self.set_A(6),

			# SET 7,r
			0xF8:self.set_B(7),
			0xF9:self.set_C(7),
			0xFA:self.set_D(7),
			0xFB:self.set_E(7),
			0xFC:self.set_H(7),
			0xFD:self.set_L(7),
			0xFE:self.set_HLi(7),
			0xFF:self.set_A(7),

			# RES 0,r
			0x80:self.res_B(0),
			0x81:self.res_C(0),
			0x82:self.res_D(0),
			0x83:self.res_E(0),
			0x84:self.res_H(0),
			0x85:self.res_L(0),
			0x86:self.res_HLi(0),
			0x87:self.res_A(0),

			# RES 1,r
			0x88:self.res_B(1),
			0x89:self.res_C(1),
			0x8A:self.res_D(1),
			0x8B:self.res_E(1),
			0x8C:self.res_H(1),
			0x8D:self.res_L(1),
			0x8E:self.res_HLi(1),
			0x8F:self.res_A(1),

			# RES 2,r
			0x90:self.res_B(2),
			0x91:self.res_C(2),
			0x92:self.res_D(2),
			0x93:self.res_E(2),
			0x94:self.res_H(2),
			0x95:self.res_L(2),
			0x96:self.res_HLi(2),
			0x97:self.res_A(2),

			# RES 3,r
			0x98:self.res_B(3),
			0x99:self.res_C(3),
			0x9A:self.res_D(3),
			0x9B:self.res_E(3),
			0x9C:self.res_H(3),
			0x9D:self.res_L(3),
			0x9E:self.res_HLi(3),
			0x9F:self.res_A(3),

			# RES 4,r
			0xA0:self.res_B(4),
			0xA1:self.res_C(4),
			0xA2:self.res_D(4),
			0xA3:self.res_E(4),
			0xA4:self.res_H(4),
			0xA5:self.res_L(4),
			0xA6:self.res_HLi(4),
			0xA7:self.res_A(4),

			# RES 5,r
			0xA8:self.res_B(5),
			0xA9:self.res_C(5),
			0xAA:self.res_D(5),
			0xAB:self.res_E(5),
			0xAC:self.res_H(5),
			0xAD:self.res_L(5),
			0xAE:self.res_HLi(5),
			0xAF:self.res_A(5),

			# RES 6,r
			0xB0:self.res_B(6),
			0xB1:self.res_C(6),
			0xB2:self.res_D(6),
			0xB3:self.res_E(6),
			0xB4:self.res_H(6),
			0xB5:self.res_L(6),
			0xB6:self.res_HLi(6),
			0xB7:self.res_A(6),

			# RES 7,r
			0xB8:self.res_B(7),
			0xB9:self.res_C(7),
			0xBA:self.res_D(7),
			0xBB:self.res_E(7),
			0xBC:self.res_H(7),
			0xBD:self.res_L(7),
			0xBE:self.res_HLi(7),
			0xBF:self.res_A(7)
			}[self.fetch()]()


	 # memory Access
	def read(self, address):
		return self.memory.read(address);


	def write(self, address, data):
		self.memory.write(address, data);


	def read(self, hi, lo):
		return self.read((hi << 8) + lo);


	def write(self, hi, lo, data):
		self.write((hi << 8) + lo, data);


	 # Fetching
	def fetch():
		if (self.pc <= 0x3FFF):
			self.pc+=1
			return self.rom[self.pc] & 0xFF;

		data = self.memory.read(self.pc);
		self.pc = (self.pc + 1) & 0xFFFF;
		return data;


	 # Stack
	def push(self, data):
		self.sp = (self.sp - 1) & 0xFFFF;
		self.memory.write(self.sp, data);


	def pop():
		data = self.memory.read(self.sp);
		self.sp = (self.sp + 1) & 0xFFFF;
		return data;


	def call(self, address):
		self.push(self.pc >> 8);
		self.push(self.pc & 0xFF);
		self.pc = address;


	 # ALU
	def add(self, data):
		s = (self.a + data) & 0xFF;
		self.f = 0
		if s == 0:
			self.f = Z_FLAG
		if s < self.a:
			self.f += C_FLAG
		if (s & 0x0F) < (self.a & 0x0F):
			self.f += H_FLAG
		self.a = s;


	def adc(self, data):
		s = self.a + data + ((self.f & C_FLAG) >> 4);
		self.f = 0
		if (s & 0xFF) == 0:
			self.f += Z_FLAG 
		if s >= 0x100:
			self.f += C_FLAG
		if ((s ^ self.a ^ data) & 0x10) != 0:
			self.f +=  H_FLAG
		self.a = s & 0xFF;


	def sub(self, data):
		s = (self.a - data) & 0xFF;
		self.f = N_FLAG
		if s == 0:
			self.f += Z_FLAG 
		if s > self.a:
			self.f += C_FLAG
		if (s & 0x0F) > (self.a & 0x0F):
			self.f +=  H_FLAG
			
		self.a = s;


	def sbc(self, data):
		s = self.a - data - ((self.f & C_FLAG) >> 4);
		self.f = N_FLAG
		if (s & 0xFF) == 0:
			self.f += Z_FLAG 
		if (s & 0xFF00) != 0:
			self.f += C_FLAG
		if ((s ^ self.a ^ data) & 0x10) != 0:
			self.f +=  H_FLAG
		self.a = s & 0xFF;


	def AND(self, data):
		self.a &= data;
		self.f = 0
		if self.a == 0:
			self.f = Z_FLAG


	def xOR(self, data):
		self.a ^= data;
		self.f = 0 		
		if self.a == 0:
			self.f = Z_FLAG


	def cpuOR(self, data):
		self.a |= data;
		self.f = 0
		if self.a == 0: 	
			self.f = Z_FLAG


	def cp(self, data):
		s = (self.a - data) & 0xFF;
		self.f = N_FLAG
		if s==0:
			self.f += Z_FLAG
		if s > self.a:
			self.f += C_FLAG
		if (s & 0x0F) > (self.a & 0x0F):
			self.f += H_FLAG


	def inc(self, data):
		data = (data + 1) & 0xFF;
		self.f = 0
		if data == 0:
			self.f += Z_FLAG
		if (data & 0x0F) == 0x00:
			self.f += H_FLAG
		self.f += (self.f & C_FLAG);
		return data;


	def dec(self, data):
		data = (data - 1) & 0xFF;
		self.f = 0
		if data == 0:
			self.f += Z_FLAG
		if (data & 0x0F) == 0x0F:
				self.f += H_FLAG
		self.f += (self.f & C_FLAG) + N_FLAG;
		return data;


	def rlc(self, data):
		s = ((data & 0x7F) << 1) + ((data & 0x80) >> 7);
		self.f = 0
		if s == 0:
			self.f += Z_FLAG
		if (data & 0x80) != 0:
			self.f += C_FLAG
		return s;


	def rl(self, data):
		s = ((data & 0x7F) << 1)
		if (self.f & C_FLAG) != 0:
			self.f += 0x01;
		self.f =0
		if  (s == 0):
			self.f += Z_FLAG
		if (data & 0x80) != 0:
			self.f += C_FLAG
		return s;


	def rrc(self, data):
		s = (data >> 1) + ((data & 0x01) << 7);
		self.f = 0
		if s == 0:
			self.f += Z_FLAG
		if (data & 0x01) != 0:
			self.f += C_FLAG
		return s;


	def rr(self, data):
		s = (data >> 1) + ((self.f & C_FLAG) << 3);
		self.f = 0 
		if s == 0:
			self.f += Z_FLAG
		if (data & 0x01) != 0:
			self.f += C_FLAG
		return s;


	def sla(self, data):
		s = (data << 1) & 0xFF;
		self.f = 0
		if s == 0:
			self.f += Z_FLAG
		if (data & 0x80) != 0:
			self.f += C_FLAG
		return s;


	def sra(self, data):
		s = (data >> 1) + (data & 0x80);
		self.f = 0 
		if s == 0:
			self.f += Z_FLAG
		if  (data & 0x01) != 0:
			self.f += C_FLAG 
		return s;


	def srl(self, data):
		s = (data >> 1);
		self.f = 0
		if s == 0 :
			self.f += Z_FLAG
		if (data & 0x01) != 0:
			self.f += C_FLAG
		return s;


	def swap(self, data):
		s = ((data << 4) & 0xF0) + ((data >> 4) & 0x0F);
		self.f = 0
		if s == 0:
			self.f += Z_FLAG
		return s;


	def bit(self, n, data):
		self.f = (self.f & C_FLAG) + H_FLAG
		if (data & (1 << n)) == 0:
			self.f += Z_FLAG


	def add(self, hi, lo):
		s = ((self.h << 8) + self.l + (hi << 8) + lo) & 0xFFFF;
		self.f = (self.f & Z_FLAG)
		if ((s >> 8) & 0x0F) < (self.h & 0x0F):
			self.f += H_FLAG
		self.f += s < (self.h << 8)
		if self.l:
			self.f += C_FLAG
		self.l = s & 0xFF;
		self.h = s >> 8;


	 # LD r,r
	def ld_B_B():
		# b = b;
		self.cycles -= 1;


	def ld_B_C():
		self.b = self.c;
		self.cycles -= 1;


	def ld_B_D():
		self.b = self.d;
		self.cycles -= 1;


	def ld_B_E():
		self.b = self.e;
		self.cycles -= 1;


	def ld_B_H():
		self.b = self.h;
		self.cycles -= 1;


	def ld_B_L():
		self.b = self.l;
		self.cycles -= 1;


	def ld_B_A():
		self.b = self.a;
		self.cycles -= 1;


	def ld_C_B():
		self.c = self.b;
		self.cycles -= 1;


	def ld_C_C():
		# c = c;
		self.cycles -= 1;


	def ld_C_D():
		self.c = self.d;
		self.cycles -= 1;


	def ld_C_E():
		self.c = self.e;
		self.cycles -= 1;


	def ld_C_H():
		self.c = self.h;
		self.cycles -= 1;


	def ld_C_L():
		self.c = self.l;
		self.cycles -= 1;


	def ld_C_A():
		self.c = self.a;
		self.cycles -= 1;


	def ld_D_B():
		self.d = self.b;
		self.cycles -= 1;


	def ld_D_C():
		self.d = self.c;
		self.cycles -= 1;


	def ld_D_D():
		# d = d;
		self.cycles -= 1;


	def ld_D_E():
		self.d = self.e;
		self.cycles -= 1;


	def ld_D_H():
		self.d = self.h;
		self.cycles -= 1;


	def ld_D_L():
		self.d = self.l;
		self.cycles -= 1;


	def ld_D_A():
		self.d = self.a;
		self.cycles -= 1;


	def ld_E_B():
		self.e = self.b;
		self.cycles -= 1;


	def ld_E_C():
		self.e = self.c;
		self.cycles -= 1;


	def ld_E_D():
		self.e = self.d;
		self.cycles -= 1;


	def ld_E_E():
		# e = e;
		self.cycles -= 1;


	def ld_E_H():
		self.e = self.h;
		self.cycles -= 1;


	def ld_E_L():
		self.e = self.l;
		self.cycles -= 1;


	def ld_E_A():
		self.e = self.a;
		self.cycles -= 1;


	def ld_H_B():
		self.h = self.b;
		self.cycles -= 1;


	def ld_H_C():
		self.h = self.c;
		self.cycles -= 1;


	def ld_H_D():
		self.h = self.d;
		self.cycles -= 1;


	def ld_H_E():
		self.h = self.e;
		self.cycles -= 1;


	def ld_H_H():
		# h = h;
		self.cycles -= 1;


	def ld_H_L():
		self.h = self.l;
		self.cycles -= 1;


	def ld_H_A():
		self.h = self.a;
		self.cycles -= 1;


	def ld_L_B():
		self.l = self.b;
		self.cycles -= 1;


	def ld_L_C():
		self.l = self.c;
		self.cycles -= 1;


	def ld_L_D():
		self.l = self.d;
		self.cycles -= 1;


	def ld_L_E():
		self.l = self.e;
		self.cycles -= 1;


	def ld_L_H():
		self.l = self.h;
		self.cycles -= 1;


	def ld_L_L():
		# l = l;
		self.cycles -= 1;


	def ld_L_A():
		self.l = self.a;
		self.cycles -= 1;


	def ld_A_B():
		self.a = self.b;
		self.cycles -= 1;


	def ld_A_C():
		self.a = self.c;
		self.cycles -= 1;


	def ld_A_D():
		self.a = self.d;
		self.cycles -= 1;


	def ld_A_E():
		self.a = self.e;
		self.cycles -= 1;


	def ld_A_H():
		self.a = self.h;
		self.cycles -= 1;


	def ld_A_L():
		self.a = self.l;
		self.cycles -= 1;


	def ld_A_A():
		# a = a;
		self.cycles -= 1;


	 # LD r,nn
	def ld_B_nn():
		self.b = self.fetch();
		self.cycles -= 2;


	def ld_C_nn():
		self.c = self.fetch();
		self.cycles -= 2;


	def ld_D_nn():
		self.d = self.fetch();
		self.cycles -= 2;


	def ld_E_nn():
		self.e = self.fetch();
		self.cycles -= 2;


	def ld_H_nn():
		self.h = self.fetch();
		self.cycles -= 2;


	def ld_L_nn():
		self.l = self.fetch();
		self.cycles -= 2;


	def ld_A_nn():
		self.a = self.fetch();
		self.cycles -= 2;


	 # LD r,(HL)
	def ld_B_HLi():
		self.b = self.read(self.h, self.l);
		self.cycles -= 2;


	def ld_C_HLi():
		self.c = self.read(self.h, self.l);
		self.cycles -= 2;


	def ld_D_HLi():
		self.d = self.read(self.h, self.l);
		self.cycles -= 2;


	def ld_E_HLi():
		self.e = self.read(self.h, self.l);
		self.cycles -= 2;


	def ld_H_HLi():
		self.h = self.read(self.h, self.l);
		self.cycles -= 2;


	def ld_L_HLi():
		self.l = self.read(self.h, self.l);
		self.cycles -= 2;


	def ld_A_HLi():
		self.a = self.read(self.h, self.l);
		self.cycles -= 2;


	 # LD (HL),r
	def ld_HLi_B():
		self.write(self.h, self.l, self.b);
		self.cycles -= 2;


	def ld_HLi_C():
		self.write(self.h, self.l, self.c);
		self.cycles -= 2;


	def ld_HLi_D():
		self.write(self.h, self.l, self.d);
		self.cycles -= 2;


	def ld_HLi_E():
		self.write(self.h, self.l, self.e);
		self.cycles -= 2;


	def ld_HLi_H():
		self.write(self.h, self.l, self.h);
		self.cycles -= 2;


	def ld_HLi_L():
		self.write(self.h, self.l, self.l);
		self.cycles -= 2;


	def ld_HLi_A():
		self.write(self.h, self.l, self.a);
		self.cycles -= 2;


	 # LD (HL),nn
	def ld_HLi_nn():
		self.write(self.h, self.l, self.fetch());
		self.cycles -= 3;


	 # LD A,(rr)
	def ld_A_BCi():
		self.a = self.read(self.b, self.c);
		self.cycles -= 2;


	def load_A_DEi():
		self.a = self.read(self.d, self.e);
		self.cycles -= 2;


	 # LD A,(nnnn)
	def ld_A_mem():
		lo = self.fetch();
		hi = self.fetch();
		self.a = self.read(hi, lo);
		self.cycles -= 4;


	 # LD (rr),A
	def ld_BCi_A():
		self.write(self.b, self.c, self.a);
		self.cycles -= 2;


	def ld_DEi_A():
		self.write(self.d, self.e, self.a);
		self.cycles -= 2;


	 # LD (nnnn),SP
	def load_mem_SP():
		lo = self.fetch();
		hi = self.fetch();
		address = (hi << 8) + lo;

		self.write(address, self.sp & 0xFF);
		self.write((address + 1) & 0xFFFF, self.sp >> 8);

		self.cycles -= 5;


	 # LD (nnnn),A
	def ld_mem_A():
		lo = self.fetch();
		hi = self.fetch();
		self.write(hi, lo, self.a);
		self.cycles -= 4;


	 # LDH A,(nn)
	def ldh_A_mem():
		self.a = self.read(0xFF00 + self.fetch());
		self.cycles -= 3;


	 # LDH (nn),A
	def ldh_mem_A():
		self.write(0xFF00 + self.fetch(), self.a);
		self.cycles -= 3;


	 # LDH A,(C)
	def ldh_A_Ci():
		self.a = self.read(0xFF00 + self.c);
		self.cycles -= 2;


	 # LDH (C),A
	def ldh_Ci_A():
		self.write(0xFF00 + self.c, self.a);
		self.cycles -= 2;


	 # LDI (HL),A
	def ldi_HLi_A():
		self.write(self.h, self.l, self.a);
		self.l = (self.l + 1) & 0xFF;
		if (self.l == 0):
			self.h = (self.h + 1) & 0xFF;
		self.cycles -= 2;


	 # LDI A,(HL)
	def ldi_A_HLi():
		self.a = self.read(self.h, self.l);
		self.l = (self.l + 1) & 0xFF;
		if (self.l == 0):
			self.h = (self.h + 1) & 0xFF;
		self.cycles -= 2;


	 # LDD (HL),A
	def ldd_HLi_A():
		self.write(self.h, self.l, self.a);
		self.l = (self.l - 1) & 0xFF;
		if (self.l == 0xFF):
			self.h = (self.h - 1) & 0xFF;
		self.cycles -= 2;


	 # LDD A,(HL)
	def ldd_A_HLi():
		self.a = self.read(self.h, self.l);
		self.l = (self.l - 1) & 0xFF;
		if (self.l == 0xFF):
			self.h = (self.h - 1) & 0xFF;
		self.cycles -= 2;


	 # LD rr,nnnn
	def ld_BC_nnnn():
		self.c = self.fetch();
		self.b = self.fetch();
		self.cycles -= 3;


	def ld_DE_nnnn():
		self.e = self.fetch();
		self.d = self.fetch();
		self.cycles -= 3;


	def ld_HL_nnnn():
		self.l = self.fetch();
		self.h = self.fetch();
		self.cycles -= 3;


	def ld_SP_nnnn():
		lo = self.fetch();
		hi = self.fetch();
		self.sp = (hi << 8) + lo;
		self.cycles -= 3;


	 # LD SP,HL
	def ld_SP_HL():
		self.sp = (self.h << 8) + self.l;
		self.cycles -= 2;


	 # PUSH rr
	def push_BC():
		self.push(self.b);
		self.push(self.c);
		self.cycles -= 4;


	def push_DE():
		self.push(self.d);
		self.push(self.e);
		self.cycles -= 4;


	def push_HL():
		self.push(self.h);
		self.push(self.l);
		self.cycles -= 4;


	def push_AF():
		self.push(self.a);
		self.push(self.f);
		self.cycles -= 4;


	 # POP rr
	def pop_BC():
		self.c = self.pop();
		self.b = self.pop();
		self.cycles -= 3;


	def pop_DE():
		self.e = self.pop();
		self.d = self.pop();
		self.cycles -= 3;


	def pop_HL():
		self.l = self.pop();
		self.h = self.pop();
		self.cycles -= 3;


	def pop_AF():
		self.f = self.pop();
		self.a = self.pop();
		self.cycles -= 3;


	 # ADD A,r
	def add_A_B():
		self.add(self.b);
		self.cycles -= 1;


	def add_A_C():
		self.add(self.c);
		self.cycles -= 1;


	def add_A_D():
		self.add(self.d);
		self.cycles -= 1;


	def add_A_E():
		self.add(self.e);
		self.cycles -= 1;


	def add_A_H():
		self.add(self.h);
		self.cycles -= 1;


	def add_A_L():
		self.add(self.l);
		self.cycles -= 1;


	def add_A_A():
		self.add(self.a);
		self.cycles -= 1;


	 # ADD A,nn
	def add_A_nn():
		self.add(self.fetch());
		self.cycles -= 2;


	 # ADD A,(HL)
	def add_A_HLi():
		self.add(self.read(self.h, self.l));
		self.cycles -= 2;


	 # ADC A,r
	def adc_A_B():
		self.adc(self.b);
		self.cycles -= 1;


	def adc_A_C():
		self.adc(self.c);
		self.cycles -= 1;


	def adc_A_D():
		self.adc(self.d);
		self.cycles -= 1;


	def adc_A_E():
		self.adc(self.e);
		self.cycles -= 1;


	def adc_A_H():
		self.adc(self.h);
		self.cycles -= 1;


	def adc_A_L():
		self.adc(self.l);
		self.cycles -= 1;


	def adc_A_A():
		self.adc(self.a);
		self.cycles -= 1;


	 # ADC A,nn
	def adc_A_nn():
		self.adc(self.fetch());
		self.cycles -= 2;


	 # ADC A,(HL)
	def adc_A_HLi():
		self.adc(self.read(self.h, self.l));
		self.cycles -= 2;


	 # SUB A,r
	def sub_A_B():
		self.sub(self.b);
		self.cycles -= 1;


	def sub_A_C():
		self.sub(self.c);
		self.cycles -= 1;


	def sub_A_D():
		self.sub(self.d);
		self.cycles -= 1;


	def sub_A_E():
		self.sub(self.e);
		self.cycles -= 1;


	def sub_A_H():
		self.sub(self.h);
		self.cycles -= 1;


	def sub_A_L():
		self.sub(self.l);
		self.cycles -= 1;


	def sub_A_A():
		self.sub(self.a);
		self.cycles -= 1;


	 # SUB A,nn
	def sub_A_nn():
		self.sub(self.fetch());
		self.cycles -= 2;


	 # SUB A,(HL)
	def sub_A_HLi():
		self.sub(self.read(self.h, self.l));
		self.cycles -= 2;


	 # SBC A,r
	def sbc_A_B():
		self.sbc(self.b);
		self.cycles -= 1;


	def sbc_A_C():
		self.sbc(self.c);
		self.cycles -= 1;


	def sbc_A_D():
		self.sbc(self.d);
		self.cycles -= 1;


	def sbc_A_E():
		self.sbc(self.e);
		self.cycles -= 1;


	def sbc_A_H():
		self.sbc(self.h);
		self.cycles -= 1;


	def sbc_A_L():
		self.sbc(self.l);
		self.cycles -= 1;


	def sbc_A_A():
		self.sbc(self.a);
		self.cycles -= 1;


	 # SBC A,nn
	def sbc_A_nn():
		self.sbc(self.fetch());
		self.cycles -= 2;


	 # SBC A,(HL)
	def sbc_A_HLi():
		self.sbc(self.read(self.h, self.l));
		self.cycles -= 2;


	 # AND A,r
	def AND_A_B():
		self.AND(self.b);
		self.cycles -= 1;


	def AND_A_C():
		self.AND(self.c);
		self.cycles -= 1;


	def AND_A_D():
		self.AND(self.d);
		self.cycles -= 1;


	def AND_A_E():
		self.AND(self.e);
		self.cycles -= 1;


	def AND_A_H():
		self.AND(self.h);
		self.cycles -= 1;


	def AND_A_L():
		self.AND(self.l);
		self.cycles -= 1;


	def AND_A_A():
		self.AND(self.a);
		self.cycles -= 1;


	 # AND A,nn
	def AND_A_nn():
		self.AND(self.fetch());
		self.cycles -= 2;


	 # AND A,(HL)
	def AND_A_HLi():
		self.AND(self.read(self.h, self.l));
		self.cycles -= 2;


	 # XOR A,r
	def xOR_A_B():
		self.xOR(self.b);
		self.cycles -= 1;


	def xOR_A_C():
		self.xOR(self.c);
		self.cycles -= 1;


	def xOR_A_D():
		self.xOR(self.d);
		self.cycles -= 1;


	def xOR_A_E():
		self.xOR(self.e);
		self.cycles -= 1;


	def xOR_A_H():
		self.xOR(self.h);
		self.cycles -= 1;


	def xOR_A_L():
		self.xOR(self.l);
		self.cycles -= 1;


	def xOR_A_A():
		self.xOR(self.a);
		self.cycles -= 1;


	 # XOR A,nn
	def xOR_A_nn():
		self.xOR(self.fetch());
		self.cycles -= 2;


	 # XOR A,(HL)
	def xOR_A_HLi():
		self.xOR(self.read(self.h, self.l));
		self.cycles -= 2;


	 # OR A,r
	def OR_A_B():
		self.OR(self.b);
		self.cycles -= 1;


	def OR_A_C():
		self.OR(self.c);
		self.cycles -= 1;


	def OR_A_D():
		self.OR(self.d);
		self.cycles -= 1;


	def OR_A_E():
		self.OR(self.e);
		self.cycles -= 1;


	def OR_A_H():
		self.OR(self.h);
		self.cycles -= 1;


	def OR_A_L():
		self.OR(self.l);
		self.cycles -= 1;


	def OR_A_A():
		self.OR(self.a);
		self.cycles -= 1;


	 # OR A,nn
	def OR_A_nn():
		self.OR(self.fetch());
		self.cycles -= 2;


	 # OR A,(HL)
	def OR_A_HLi():
		self.OR(self.read(self.h, self.l));
		self.cycles -= 2;


	 # CP A,r
	def cp_A_B():
		self.cp(self.b);
		self.cycles -= 1;


	def cp_A_C():
		self.cp(self.c);
		self.cycles -= 1;


	def cp_A_D():
		self.cp(self.d);
		self.cycles -= 1;


	def cp_A_E():
		self.cp(self.e);
		self.cycles -= 1;


	def cp_A_H():
		self.cp(self.h);
		self.cycles -= 1;


	def cp_A_L():
		self.cp(self.l);
		self.cycles -= 1;


	def cp_A_A():
		self.cp(self.a);
		self.cycles -= 1;


	 # CP A,nn
	def cp_A_nn():
		self.cp(self.fetch());
		self.cycles -= 2;


	 # CP A,(HL)
	def cp_A_HLi():
		self.cp(self.read(self.h, self.l));
		self.cycles -= 2;


	 # INC r
	def inc_B():
		self.b = self.inc(self.b);
		self.cycles -= 1;


	def inc_C():
		self.c = self.inc(self.c);
		self.cycles -= 1;


	def inc_D():
		self.d = self.inc(self.d);
		self.cycles -= 1;


	def inc_E():
		self.e = self.inc(self.e);
		self.cycles -= 1;


	def inc_H():
		self.h = self.inc(self.h);
		self.cycles -= 1;


	def inc_L():
		self.l = self.inc(self.l);
		self.cycles -= 1;


	def inc_A():
		self.a = self.inc(self.a);
		self.cycles -= 1;


	 # INC (HL)
	def inc_HLi():
		self.write(self.h, self.l, self.inc(self.read(self.h, self.l)));
		self.cycles -= 3;


	 # DEC r
	def dec_B():
		self.b = self.dec(self.b);
		self.cycles -= 1;


	def dec_C():
		self.c = self.dec(self.c);
		self.cycles -= 1;


	def dec_D():
		self.d = self.dec(self.d);
		self.cycles -= 1;


	def dec_E():
		self.e = self.dec(self.e);
		self.cycles -= 1;


	def dec_H():
		self.h = self.dec(self.h);
		self.cycles -= 1;


	def dec_L():
		self.l = self.dec(self.l);
		self.cycles -= 1;


	def dec_A():
		self.a = self.dec(self.a);
		self.cycles -= 1;


	 # DEC (HL)
	def dec_HLi():
		self.write(self.h, self.l, self.dec(self.read(self.h, self.l)));
		self.cycles -= 3;


	 # CPL
	def cpl():
		self.a ^= 0xFF;
		self.f |= N_FLAG + H_FLAG;


	 # DAA
	def daa():
		delta = 0;
		if ((self.f & H_FLAG) != 0 or (self.a & 0x0F) > 0x09):
			delta |= 0x06;
		if ((self.f & C_FLAG) != 0 or (self.a & 0xF0) > 0x90):
			delta |= 0x60;
		if ((self.a & 0xF0) > 0x80 and (self.a & 0x0F) > 0x09):
			delta |= 0x60;
		if ((self.f & N_FLAG) == 0):
			self.a = (self.a + delta) & 0xFF;
		else:
			self.a = (self.a - delta) & 0xFF;

		self.f = (self.f & N_FLAG)
		if delta >= 0x60:
			self.f += C_FLAG
		if self.a == 0:
			self.f += Z_FLAG

		self.cycles -= 1;


	 # ADD HL,rr
	def add_HL_BC():
		self.add(self.b, self.c);
		self.cycles -= 2;


	def add_HL_DE():
		self.add(self.d, self.e);
		self.cycles -= 2;


	def add_HL_HL():
		self.add(self.h, self.l);
		self.cycles -= 2;


	def add_HL_SP():
		self.add(self.sp >> 8, self.sp & 0xFF);
		self.cycles -= 2;


	 # INC rr
	def inc_BC():
		self.c = (self.c + 1) & 0xFF;
		if (self.c == 0x00):
			self.b = (self.b + 1) & 0xFF;
		self.cycles -= 2;


	def inc_DE():
		self.e = (self.e + 1) & 0xFF;
		if (self.e == 0x00):
			self.d = (self.d + 1) & 0xFF;
		self.cycles -= 2;


	def inc_HL():
		self.l = (self.l + 1) & 0xFF;
		if (self.l == 0x00):
			self.h = (self.h + 1) & 0xFF;
		self.cycles -= 2;


	def inc_SP():
		self.sp = (self.sp + 1) & 0xFFFF;
		self.cycles -= 2;


	 # DEC rr
	def dec_BC():
		self.c = (self.c - 1) & 0xFF;
		if (self.c == 0xFF):
			self.b = (self.b - 1) & 0xFF;
		self.cycles -= 2;


	def dec_DE():
		self.e = (self.e - 1) & 0xFF;
		if (self.e == 0xFF):
			self.d = (self.d - 1) & 0xFF;
		self.cycles -= 2;


	def dec_HL():
		self.l = (self.l - 1) & 0xFF;
		if (self.l == 0xFF):
			self.h = (self.h - 1) & 0xFF;
		self.cycles -= 2;


	def dec_SP():
		self.sp = (self.sp - 1) & 0xFFFF;
		self.cycles -= 2;


	 # ADD SP,nn
	def add_SP_nn():
		# TODO convert to byte
		offset = self.fetch();
		s = (self.sp + offset) & 0xFFFF;
		self.updateFRegisterAfterSP_nn(offset, s)

		self.sp = s;
		self.cycles -= 4;



	 # LD HL,SP+nn
	def ld_HP_SP_nn():
		#TODO convert to byte
		s = (self.sp + offset) & 0xFFFF;
		self.updateFRegisterAfterSP_nn(offset, s)

		self.l = s & 0xFF;
		self.h = s >> 8;

		self.cycles -= 3;


	def updateFRegisterAfterSP_nn(self, offset, s):
		if (offset >= 0):
			self.f = 0
			if s < self.sp:
				self.f += C_FLAG
			if (s & 0x0F00) < (self.sp & 0x0F00):
				self.f += H_FLAG
		else:
			self.f = 0
			if s > self.sp:
				self.f += C_FLAG
			if (s & 0x0F00) > (self.sp & 0x0F00):
				self.f += H_FLAG

	 # RLCA
	def rlca():
		self.f = 0
		if (self.a & 0x80) != 0:
			self.f += C_FLAG
		self.a = ((self.a & 0x7F) << 1) + ((self.a & 0x80) >> 7);
		self.cycles -= 1;


	 # RLA
	def rla():
		s = ((self.a & 0x7F) << 1)
		if (self.f & C_FLAG) != 0:
			s +=  0x01
		self.f = 0
		if (self.a & 0x80) != 0:
			self.f += C_FLAG
		self.a = s;
		self.cycles -= 1;


	 # RRCA
	def rrca():
		self.f = 0
		if (self.a & 0x01) != 0:
			self.f += C_FLAG
		self.a = ((self.a >> 1) & 0x7F) + ((self.a << 7) & 0x80);
		self.cycles -= 1;


	 # RRA
	def rra():
		s = ((self.a >> 1) & 0x7F)
		if (self.f & C_FLAG) != 0:
			se += 0x80
		self.f = 0
		if (self.a & 0x01) != 0:
			self.f += C_FLAG
		self.a = s;
		self.cycles -= 1;


	 # RLC r
	def rlc_B():
		self.b = self.rlc(self.b);
		self.cycles -= 2;


	def rlc_C():
		self.c = self.rlc(self.c);
		self.cycles -= 2;


	def rlc_D():
		self.d = self.rlc(self.d);
		self.cycles -= 2;


	def rlc_E():
		self.e = self.rlc(self.e);
		self.cycles -= 2;


	def rlc_H():
		self.h = self.rlc(self.h);
		self.cycles -= 2;


	def rlc_L():
		self.l = self.rlc(self.l);
		self.cycles -= 2;


	def rlc_A():
		self.a = self.rlc(self.a);
		self.cycles -= 2;


	 # RLC (HL)
	def rlc_HLi():
		self.write(self.h, self.l, self.rlc(self.read(self.h, self.l)));
		self.cycles -= 4;


	 # RL r
	def rl_B():
		self.b = self.rl(self.b);
		self.cycles -= 2;


	def rl_C():
		self.c = self.rl(self.c);
		self.cycles -= 2;


	def rl_D():
		self.d = self.rl(self.d);
		self.cycles -= 2;


	def rl_E():
		self.e = self.rl(self.e);
		self.cycles -= 2;


	def rl_H():
		self.h = self.rl(self.h);
		self.cycles -= 2;


	def rl_L():
		self.l = self.rl(self.l);
		self.cycles -= 2;


	def rl_A():
		self.a = self.rl(self.a);
		self.cycles -= 2;


	 # RL (HL)
	def rl_HLi():
		self.write(self.h, self.l, self.rl(self.read(self.h, self.l)));
		self.cycles -= 4;


	 # RRC r
	def rrc_B():
		self.b = self.rrc(self.b);
		self.cycles -= 2;


	def rrc_C():
		self.c = self.rrc(self.c);
		self.cycles -= 2;


	def rrc_D():
		self.d = self.rrc(self.d);
		self.cycles -= 2;


	def rrc_E():
		self.e = self.rrc(self.e);
		self.cycles -= 2;


	def rrc_H():
		self.h = self.rrc(self.h);
		self.cycles -= 2;


	def rrc_L():
		self.l = self.rrc(self.l);
		self.cycles -= 2;


	def rrc_A():
		self.a = self.rrc(self.a);
		self.cycles -= 2;


	 # RRC (HL)
	def rrc_HLi():
		self.write(self.h, self.l, self.rrc(self.read(self.h, self.l)));
		self.cycles -= 4;


	 # RR r
	def rr_B():
		self.b = self.rr(self.b);
		self.cycles -= 2;


	def rr_C():
		self.c = self.rr(self.c);
		self.cycles -= 2;


	def rr_D():
		self.d = self.rr(self.d);
		self.cycles -= 2;


	def rr_E():
		self.e = self.rr(self.e);
		self.cycles -= 2;


	def rr_H():
		self.h = self.rr(self.h);
		self.cycles -= 2;


	def rr_L():
		self.l = self.rr(self.l);
		self.cycles -= 2;


	def rr_A():
		self.a = self.rr(self.a);
		self.cycles -= 2;


	 # RR (HL)
	def rr_HLi():
		self.write(self.h, self.l, self.rr(self.read(self.h, self.l)));
		self.cycles -= 4;


	 # SLA r
	def sla_B():
		self.b = self.sla(self.b);
		self.cycles -= 2;


	def sla_C():
		self.c = self.sla(self.c);
		self.cycles -= 2;


	def sla_D():
		self.d = self.sla(self.d);
		self.cycles -= 2;


	def sla_E():
		self.e = self.sla(self.e);
		self.cycles -= 2;


	def sla_H():
		self.h = self.sla(self.h);
		self.cycles -= 2;


	def sla_L():
		self.l = self.sla(self.l);
		self.cycles -= 2;


	def sla_A():
		self.a = self.sla(self.a);
		self.cycles -= 2;


	 # SLA (HL)
	def sla_HLi():
		self.write(self.h, self.l, self.sla(self.read(self.h, self.l)));
		self.cycles -= 4;


	 # SWAP r
	def swap_B():
		self.b = self.swap(self.b);
		self.cycles -= 2;


	def swap_C():
		self.c = self.swap(self.c);
		self.cycles -= 2;


	def swap_D():
		self.d = self.swap(self.d);
		self.cycles -= 2;


	def swap_E():
		self.e = self.swap(self.e);
		self.cycles -= 2;


	def swap_H():
		self.h = self.swap(self.h);
		self.cycles -= 2;


	def swap_L():
		self.l = self.swap(self.l);
		self.cycles -= 2;


	def swap_A():
		self.a = self.swap(self.a);
		self.cycles -= 2;


	 # SWAP (HL)
	def swap_HLi():
		self.write(self.h, self.l, self.swap(self.read(self.h, self.l)));
		self.cycles -= 4;


	 # SRA r
	def sra_B():
		self.b = self.sra(self.b);
		self.cycles -= 2;


	def sra_C():
		self.c = self.sra(self.c);
		self.cycles -= 2;


	def sra_D():
		self.d = self.sra(self.d);
		self.cycles -= 2;


	def sra_E():
		self.e = self.sra(self.e);
		self.cycles -= 2;


	def sra_H():
		self.h = self.sra(self.h);
		self.cycles -= 2;


	def sra_L():
		self.l = self.sra(self.l);
		self.cycles -= 2;


	def sra_A():
		self.a = self.sra(self.a);
		self.cycles -= 2;


	 # SRA (HL)
	def sra_HLi():
		self.write(self.h, self.l, self.sra(self.read(self.h, self.l)));
		self.cycles -= 4;


	 # SRL r
	def srl_B():
		self.b = self.srl(self.b);
		self.cycles -= 2;


	def srl_C():
		self.c = self.srl(self.c);
		self.cycles -= 2;


	def srl_D():
		self.d = self.srl(self.d);
		self.cycles -= 2;


	def srl_E():
		self.e = self.srl(self.e);
		self.cycles -= 2;


	def srl_H():
		self.h = self.srl(self.h);
		self.cycles -= 2;


	def srl_L():
		self.l = self.srl(self.l);
		self.cycles -= 2;


	def srl_A():
		self.a = self.srl(self.a);
		self.cycles -= 2;


	 # SRL (HL)
	def srl_HLi():
		self.write(self.h, self.l, self.srl(self.read(self.h, self.l)));
		self.cycles -= 4;


	 # BIT n,r
	def bit_B(self, n):
		self.bit(n, self.b);
		self.cycles -= 2;


	def bit_C(self, n):
		self.bit(n, self.c);
		self.cycles -= 2;


	def bit_D(self, n):
		self.bit(n, self.d);
		self.cycles -= 2;


	def bit_E(self, n):
		self.bit(n, self.e);
		self.cycles -= 2;


	def bit_H(self, n):
		self.bit(n, self.h);
		self.cycles -= 2;


	def bit_L(self, n):
		self.bit(n, self.l);
		self.cycles -= 2;


	def bit_A(self, n):
		self.bit(n, self.a);
		self.cycles -= 2;


	 # BIT n,(HL)
	def bit_HLi(self, n):
		self.bit(n, self.read(self.h, self.l));
		self.cycles -= 3;


	 # SET n,r
	def set_B(self, n):
		self.b |= 1 << n;
		self.cycles -= 2;


	def set_C(self, n):
		self.c |= 1 << n;
		self.cycles -= 2;


	def set_D(self, n):
		self.d |= 1 << n;
		self.cycles -= 2;


	def set_E(self, n):
		self.e |= 1 << n;
		self.cycles -= 2;


	def set_H(self, n):
		self.h |= 1 << n;
		self.cycles -= 2;


	def set_L(self, n):
		self.l |= 1 << n;
		self.cycles -= 2;


	def set_A(self, n):
		self.a |= 1 << n;
		self.cycles -= 2;


	 # SET n,(HL)
	def set_HLi(self, n):
		self.write(self.h, self.l, self.read(self.h, self.l) | (1 << n));
		self.cycles -= 4;


	 # RES n,r
	def res_B(self, n):
		self.b &= ~(1 << n);
		self.cycles -= 2;


	def res_C(self, n):
		self.c &= ~(1 << n);
		self.cycles -= 2;


	def res_D(self, n):
		self.d &= ~(1 << n);
		self.cycles -= 2;


	def res_E(self, n):
		self.e &= ~(1 << n);
		self.cycles -= 2;


	def res_H(self, n):
		self.h &= ~(1 << n);
		self.cycles -= 2;


	def res_L(self, n):
		self.l &= ~(1 << n);
		self.cycles -= 2;


	def res_A(self, n):
		self.a &= ~(1 << n);
		self.cycles -= 2;


	 # RES n,(HL)
	def res_HLi(self, n):
		self.write(self.h, self.l, self.read(self.h, self.l) & ~(1 << n));
		self.cycles -= 4;


	 # CCF/SCF
	def ccf():
		self.f = (self.f & (Z_FLAG | C_FLAG)) ^ C_FLAG;


	def scf():
		self.f = (self.f & Z_FLAG) | C_FLAG;


	 # NOP
	def nop():
		self.cycles -= 1;


	 # JP nnnn
	def jp_nnnn():
		lo = self.fetch();
		hi = self.fetch();
		self.pc = (hi << 8) + lo;
		self.cycles -= 4;


	 # LD PC,HL
	def ld_PC_HL():
		self.pc = (self.h << 8) + self.l;
		self.cycles -= 1;


	 # JP cc,nnnn
	def jp_cc_nnnn(cc):
		if (cc):
			lo = self.fetch();
			hi = self.fetch();
			self.pc = (hi << 8) + lo;
			self.cycles -= 4;
	 	else:
			self.pc = (self.pc + 2) & 0xFFFF;
			self.cycles -= 3;
	

	def jp_NZ_nnnn():
		self.jp_cc_nnnn((self.f & Z_FLAG) == 0);


	def jp_NC_nnnn():
		self.jp_cc_nnnn((self.f & C_FLAG) == 0);


	def jp_Z_nnnn():
		self.jp_cc_nnnn((self.f & Z_FLAG) != 0);


	def jp_C_nnnn():
		self.jp_cc_nnnn((self.f & C_FLAG) != 0);


	 # JR +nn
	def jr_nn():
		# TODO convert to byte
		offset = self.fetch();
		self.pc = (self.pc + offset) & 0xFFFF;
		self.cycles -= 3;


	 # JR cc,+nn
	def jr_cc_nn(cc):
		if (cc):
			# TODO convert to byte
			offset = self.fetch();

			self.pc = (self.pc + offset) & 0xFFFF;
			self.cycles -= 3;
		else:
			self.pc = (self.pc + 1) & 0xFFFF;
			self.cycles -= 2;
	

	def jr_NZ_nn():
		self.jr_cc_nn((self.f & Z_FLAG) == 0);


	def jr_Z_nn():
		self.jr_cc_nn((self.f & Z_FLAG) != 0);


	def jr_NC_nn():
		self.jr_cc_nn((self.f & C_FLAG) == 0);


	def jr_C_nn():
		self.jr_cc_nn((self.f & C_FLAG) != 0);


	 # CALL nnnn
	def call_nnnn():
		lo = self.fetch();
		hi = self.fetch();
		self.call((hi << 8) + lo);
		self.cycles -= 6;


	 # CALL cc,nnnn
	def call_cc_nnnn(cc):
		if (cc):
			lo = self.fetch();
			hi = self.fetch();
			self.call((hi << 8) + lo);
			self.cycles -= 6;
 		else:
			self.pc = (self.pc + 2) & 0xFFFF;
			self.cycles -= 3;
	


	def call_NZ_nnnn():
		self.call_cc_nnnn((self.f & Z_FLAG) == 0);


	def call_NC_nnnn():
		self.call_cc_nnnn((self.f & C_FLAG) == 0);


	def call_Z_nnnn():
		self.call_cc_nnnn((self.f & Z_FLAG) != 0);


	def call_C_nnnn():
		self.call_cc_nnnn((self.f & C_FLAG) != 0);


	 # RET
	def ret():
		lo = self.pop();
		hi = self.pop();
		self.pc = (hi << 8) + lo;
		self.cycles -= 4;


	 # RET cc
	def ret_cc(cc):
		if (cc):
			lo = self.pop();
			hi = self.pop();
			self.pc = (hi << 8) + lo;
			self.cycles -= 5;
 		else:
			self.cycles -= 2;


	def ret_NZ():
		self.ret_cc((self.f & Z_FLAG) == 0);


	def ret_NC():
		self.ret_cc((self.f & C_FLAG) == 0);


	def ret_Z():
		self.ret_cc((self.f & Z_FLAG) != 0);


	def ret_C():
		self.ret_cc((self.f & C_FLAG) != 0);


	 # RST nn
	def rst(self, nn):
		self.call(nn);
		self.cycles -= 4;


	 # RETI
	def reti():
		lo = self.pop();
		hi = self.pop();
		self.pc = (hi << 8) + lo;
		# enable interrupts
		self.ime = true;
		self.cycles -= 4;
		# execute next instruction
		self.execute();
		# check pending interrupts
		self.interrupt();


	 # DI/EI
	def di():
		# disable interrupts
		self.ime = false;
		self.cycles -= 1; 


	def ei():
		# enable interrupts
		self.ime = true;
		self.cycles -= 1;
		# execute next instruction
		self.execute();
		# check pending interrupts
		self.interrupt();


	 # HALT/STOP
	def halt():
		self.halted = true;
		# emulate bug when interrupts are pending
		if (not self.ime and self.interrupt.isPending()):
			self.execute(self.memory.read(self.pc));
		# check pending interrupts
		self.interrupt();


	def stop():
		self.fetch();

