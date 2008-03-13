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


	def getBC(self):
		return (self.b << 8) + self.c;


	def getDE(self):
		return (self.d << 8) + self.e;


	def getHL(self):
		return (self.h << 8) + self.l;


	def getSP(self):
		return self.sp;


	def getPC(self):
		return self.pc;


	def getAF(self):
		return (self.a << 8) + self.f;


	def getIF(self):
		val = 0x00
		#if (self.ime ? 0x01 : 0x00) + (self.halted ? 0x80 : 0x00);
		if self.ime:
			val = 0x01
		if self.halted:
			val += 0x80
		return val
			

	def setROM(self, banks):
		self.rom = banks;


	def reset(self):
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
	def interrupt(self):
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
	def execute(self):
		self.execute(self.fetch());


	def execute(self, opcode):
		result = { 0x00:self.nop(),
			# LD (nnnn),SP
			0x08:self.load_mem_SP(),
	
			# STOP
			0x10:self.stop(),
	
			# JR nn
			0x18:SELF.JR_nn(),
	
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
	
			# XXX Should be ranges
			0x04:self.inc
			0x05:self.dec
			0x06:self.ld_nn
	
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
	
            # XXX Should be ranges 
			0x40:self.ld
			0x48:self.ld
			0x50:self.ld
			0x58:self.ld
			0x60:self.ld
			0x68:self.ld
			0x70:self.ld
			0x78:self.ld
			0x80:self.add
			0x88:self.adc
			0x90:self.sub
			0x98:self.sbc
			0xA0:self.AND
			0xA8:self.xOR
			0xB0:self.OR
			0xB8:self.cp
	
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
			result = [
			self.rlc,
			self.rrc,
			self.rl,
			self.rr,
			self.sla,
			self.sra,
			self.swap,
			self.srl,
			self.bit
			self.set_0
			self.set_1
			self.set_2
			self.set_3
			self.set_4
			self.set_5
			self.set_6
			self.set_7
			self.res_0,
			self.res_1,
			self.res_2,
			self.res_3,
			self.res_4,
			self.res_5,
			self.res_6,
			self.res_7,
			][self.fetch()]()


	 # memory Access
	def read(self, address):
        self.cycles -= 1
		return self.memory.read(address);


	def write(self, address, data):
		self.memory.write(address, data);
        self.cycles -= 1


	def read(self, hi, lo):
        self.cycles -= 1
		return self.read((hi << 8) + lo);


	def write(self, hi, lo, data):
		self.write((hi << 8) + lo, data);
        self.cycles -= 2


	 # Fetching
	def fetch(self):
        self.cycles -=1

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


	def pop(self):
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


	def ld(self, setter, getter):
		setter(getter());

	def ld_nn(self, setter):
		self(setter, self.fetch());

	 # LD A,(rr)
	def ld_A_BCi(self):
		self.seta(self.read(self.b, self.c));

	def load_A_DEi(self):
		self.seta(self.read(self.d, self.e));

	 # LD A,(nnnn)
	def ld_A_mem(self):
		lo = self.fetch();
		hi = self.fetch();
		self.seta(self.read(hi, lo));

	 # LD (rr),A
	def ld_BCi_A(self):
		self.write(self.b, self.c, self.a);

	def ld_DEi_A(self):
		self.write(self.d, self.e, self.a);

	 # LD (nnnn),SP
	def load_mem_SP(self):
		lo = self.fetch();
		hi = self.fetch();
		address = (hi << 8) + lo;

		self.write(address, self.sp & 0xFF);
		self.write((address + 1) & 0xFFFF, self.sp >> 8);

		self.cycles -= 5;


	 # LD (nnnn),A
	def ld_mem_A(self):
		lo = self.fetch();
		hi = self.fetch();
		self.write(hi, lo, self.a);
		self.cycles -= 4;


	 # LDH A,(nn)
	def ldh_A_mem(self):
		self.a = self.read(0xFF00 + self.fetch());
		self.cycles -= 3;


	 # LDH (nn),A
	def ldh_mem_A(self):
		self.write(0xFF00 + self.fetch(), self.a);
		self.cycles -= 3;


	 # LDH A,(C)
	def ldh_A_Ci(self):
		self.a = self.read(0xFF00 + self.c);
		self.cycles -= 2;


	 # LDH (C),A
	def ldh_Ci_A(self):
		self.write(0xFF00 + self.c, self.a);
		self.cycles -= 2;


	 # LDI (HL),A
	def ldi_HLi_A(self):
		self.write(self.h, self.l, self.a);
		self.l = (self.l + 1) & 0xFF;
		if (self.l == 0):
			self.h = (self.h + 1) & 0xFF;
		self.cycles -= 2;


	 # LDI A,(HL)
	def ldi_A_HLi(self):
		self.a = self.read(self.h, self.l);
		self.l = (self.l + 1) & 0xFF;
		if (self.l == 0):
			self.h = (self.h + 1) & 0xFF;
		self.cycles -= 2;


	 # LDD (HL),A
	def ldd_HLi_A(self):
		self.write(self.h, self.l, self.a);
		self.l = (self.l - 1) & 0xFF;
		if (self.l == 0xFF):
			self.h = (self.h - 1) & 0xFF;
		self.cycles -= 2;


	 # LDD A,(HL)
	def ldd_A_HLi(self):
		self.a = self.read(self.h, self.l);
		self.l = (self.l - 1) & 0xFF;
		if (self.l == 0xFF):
			self.h = (self.h - 1) & 0xFF;
		self.cycles -= 2;


	 # LD rr,nnnn
	def ld_BC_nnnn(self):
		self.c = self.fetch();
		self.b = self.fetch();
		self.cycles -= 3;


	def ld_DE_nnnn(self):
		self.e = self.fetch();
		self.d = self.fetch();
		self.cycles -= 3;


	def ld_HL_nnnn(self):
		self.l = self.fetch();
		self.h = self.fetch();
		self.cycles -= 3;


	def ld_SP_nnnn(self):
		lo = self.fetch();
		hi = self.fetch();
		self.sp = (hi << 8) + lo;
		self.cycles -= 3;


	 # LD SP,HL
	def ld_SP_HL(self):
		self.sp = (self.h << 8) + self.l;
		self.cycles -= 2;


	 # PUSH rr
	def push_BC(self):
		self.push(self.b);
		self.push(self.c);
		self.cycles -= 4;


	def push_DE(self):
		self.push(self.d);
		self.push(self.e);
		self.cycles -= 4;


	def push_HL(self):
		self.push(self.h);
		self.push(self.l);
		self.cycles -= 4;


	def push_AF(self):
		self.push(self.a);
		self.push(self.f);
		self.cycles -= 4;


	 # POP rr
	def pop_BC(self):
		self.c = self.pop();
		self.b = self.pop();
		self.cycles -= 3;


	def pop_DE(self):
		self.e = self.pop();
		self.d = self.pop();
		self.cycles -= 3;


	def pop_HL(self):
		self.l = self.pop();
		self.h = self.pop();
		self.cycles -= 3;


	def pop_AF(self):
		self.f = self.pop();
		self.a = self.pop();
		self.cycles -= 3;


	 # XXX ADD A,r
	def add(self):
		self.add(self.b);
		self.cycles -= 1; # 2 for hli

	 # ADD A,nn
	def add_A_nn(self):
		self.add(self.fetch());
		self.cycles -= 2;


	 # ADC A,r
	def adc_A_B(self):
		self.adc(self.b);
		self.cycles -= 1;


	def adc_A_C(self):
		self.adc(self.c);
		self.cycles -= 1;


	def adc_A_D(self):
		self.adc(self.d);
		self.cycles -= 1;


	def adc_A_E(self):
		self.adc(self.e);
		self.cycles -= 1;


	def adc_A_H(self):
		self.adc(self.h);
		self.cycles -= 1;


	def adc_A_L(self):
		self.adc(self.l);
		self.cycles -= 1;


	def adc_A_A(self):
		self.adc(self.a);
		self.cycles -= 1;


	 # ADC A,nn
	def adc_A_nn(self):
		self.adc(self.fetch());
		self.cycles -= 2;


	 # ADC A,(HL)
	def adc_A_HLi(self):
		self.adc(self.read(self.h, self.l));
		self.cycles -= 2;


	 # SUB A,r
	def sub_A_B(self):
		self.sub(self.b);
		self.cycles -= 1;


	def sub_A_C(self):
		self.sub(self.c);
		self.cycles -= 1;


	def sub_A_D(self):
		self.sub(self.d);
		self.cycles -= 1;


	def sub_A_E(self):
		self.sub(self.e);
		self.cycles -= 1;


	def sub_A_H(self):
		self.sub(self.h);
		self.cycles -= 1;


	def sub_A_L(self):
		self.sub(self.l);
		self.cycles -= 1;


	def sub_A_A(self):
		self.sub(self.a);
		self.cycles -= 1;


	 # SUB A,nn
	def sub_A_nn(self):
		self.sub(self.fetch());
		self.cycles -= 2;


	 # SUB A,(HL)
	def sub_A_HLi(self):
		self.sub(self.read(self.h, self.l));
		self.cycles -= 2;


	 # SBC A,r
	def sbc_A_B(self):
		self.sbc(self.b);
		self.cycles -= 1;


	def sbc_A_C(self):
		self.sbc(self.c);
		self.cycles -= 1;


	def sbc_A_D(self):
		self.sbc(self.d);
		self.cycles -= 1;


	def sbc_A_E(self):
		self.sbc(self.e);
		self.cycles -= 1;


	def sbc_A_H(self):
		self.sbc(self.h);
		self.cycles -= 1;


	def sbc_A_L(self):
		self.sbc(self.l);
		self.cycles -= 1;


	def sbc_A_A(self):
		self.sbc(self.a);
		self.cycles -= 1;


	 # SBC A,nn
	def sbc_A_nn(self):
		self.sbc(self.fetch());
		self.cycles -= 2;


	 # SBC A,(HL)
	def sbc_A_HLi(self):
		self.sbc(self.read(self.h, self.l));
		self.cycles -= 2;


	 # AND A,r
	def AND_A_B(self):
		self.AND(self.b);
		self.cycles -= 1;


	def AND_A_C(self):
		self.AND(self.c);
		self.cycles -= 1;


	def AND_A_D(self):
		self.AND(self.d);
		self.cycles -= 1;


	def AND_A_E(self):
		self.AND(self.e);
		self.cycles -= 1;


	def AND_A_H(self):
		self.AND(self.h);
		self.cycles -= 1;


	def AND_A_L(self):
		self.AND(self.l);
		self.cycles -= 1;


	def AND_A_A(self):
		self.AND(self.a);
		self.cycles -= 1;


	 # AND A,nn
	def AND_A_nn(self):
		self.AND(self.fetch());
		self.cycles -= 2;


	 # AND A,(HL)
	def AND_A_HLi(self):
		self.AND(self.read(self.h, self.l));
		self.cycles -= 2;


	 # XOR A,r
	def xOR_A_B(self):
		self.xOR(self.b);
		self.cycles -= 1;


	def xOR_A_C(self):
		self.xOR(self.c);
		self.cycles -= 1;


	def xOR_A_D(self):
		self.xOR(self.d);
		self.cycles -= 1;


	def xOR_A_E(self):
		self.xOR(self.e);
		self.cycles -= 1;


	def xOR_A_H(self):
		self.xOR(self.h);
		self.cycles -= 1;


	def xOR_A_L(self):
		self.xOR(self.l);
		self.cycles -= 1;


	def xOR_A_A(self):
		self.xOR(self.a);
		self.cycles -= 1;


	 # XOR A,nn
	def xOR_A_nn(self):
		self.xOR(self.fetch());
		self.cycles -= 2;


	 # XOR A,(HL)
	def xOR_A_HLi(self):
		self.xOR(self.read(self.h, self.l));
		self.cycles -= 2;


	 # XXX OR A,r
	def OR(self, getter):
		self.OR(getter());
		self.cycles -= 1; # 2 for hli

	 # OR A,nn
	def OR_A_nn(self):
        self.OR(self.fetch)


	 # XXX CP A,r
	def cp(self, getter):
		self.cp(getter());
		self.cycles -= 1;

	 # CP A,nn
	def cp_nn(self):
		self.cp(self.fetch);

	 # CP A,(HL)
	def cp_A_HLi(self):
		self.cp(self.read(self.h, self.l));
		self.cycles -= 2;


	 # INC r
	def inc_B(self):
		self.b = self.inc(self.b);
		self.cycles -= 1; # XXX 1 cycle less

	 # DEC r
	def dec_B(self):
		self.b = self.dec(self.b);
		self.cycles -= 1;


	def dec_C(self):
		self.c = self.dec(self.c);
		self.cycles -= 1;


	def dec_D(self):
		self.d = self.dec(self.d);
		self.cycles -= 1;


	def dec_E(self):
		self.e = self.dec(self.e);
		self.cycles -= 1;


	def dec_H(self):
		self.h = self.dec(self.h);
		self.cycles -= 1;


	def dec_L(self):
		self.l = self.dec(self.l);
		self.cycles -= 1;


	def dec_A(self):
		self.a = self.dec(self.a);
		self.cycles -= 1;


	 # DEC (HL)
	def dec_HLi(self):
		self.write(self.h, self.l, self.dec(self.read(self.h, self.l)));
		self.cycles -= 3;


	 # CPL
	def cpl(self):
		self.a ^= 0xFF;
		self.f |= N_FLAG + H_FLAG;


	 # DAA
	def daa(self):
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
	def add_HL_BC(self):
		self.add(self.b, self.c);
		self.cycles -= 2;


	def add_HL_DE(self):
		self.add(self.d, self.e);
		self.cycles -= 2;


	def add_HL_HL(self):
		self.add(self.h, self.l);
		self.cycles -= 2;


	def add_HL_SP(self):
		self.add(self.sp >> 8, self.sp & 0xFF);
		self.cycles -= 2;


	 # INC rr
	def inc_BC(self):
		self.c = (self.c + 1) & 0xFF;
		if (self.c == 0x00):
			self.b = (self.b + 1) & 0xFF;
		self.cycles -= 2;


	def inc_DE(self):
		self.e = (self.e + 1) & 0xFF;
		if (self.e == 0x00):
			self.d = (self.d + 1) & 0xFF;
		self.cycles -= 2;


	def inc_HL(self):
		self.l = (self.l + 1) & 0xFF;
		if (self.l == 0x00):
			self.h = (self.h + 1) & 0xFF;
		self.cycles -= 2;


	def inc_SP(self):
		self.sp = (self.sp + 1) & 0xFFFF;
		self.cycles -= 2;


	 # DEC rr
	def dec_BC(self):
		self.c = (self.c - 1) & 0xFF;
		if (self.c == 0xFF):
			self.b = (self.b - 1) & 0xFF;
		self.cycles -= 2;


	def dec_DE(self):
		self.e = (self.e - 1) & 0xFF;
		if (self.e == 0xFF):
			self.d = (self.d - 1) & 0xFF;
		self.cycles -= 2;


	def dec_HL(self):
		self.l = (self.l - 1) & 0xFF;
		if (self.l == 0xFF):
			self.h = (self.h - 1) & 0xFF;
		self.cycles -= 2;


	def dec_SP(self):
		self.sp = (self.sp - 1) & 0xFFFF;
		self.cycles -= 2;


	 # ADD SP,nn
	def add_SP_nn(self):
		# TODO convert to byte
		offset = self.fetch();
		s = (self.sp + offset) & 0xFFFF;
		self.updateFRegisterAfterSP_nn(offset, s)

		self.sp = s;
		self.cycles -= 4;



	 # LD HL,SP+nn
	def ld_HP_SP_nn(self):
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
	def rlca(self):
		self.f = 0
		if (self.a & 0x80) != 0:
			self.f += C_FLAG
		self.a = ((self.a & 0x7F) << 1) + ((self.a & 0x80) >> 7);
		self.cycles -= 1;


	 # RLA
	def rla(self):
		s = ((self.a & 0x7F) << 1)
		if (self.f & C_FLAG) != 0:
			s +=  0x01
		self.f = 0
		if (self.a & 0x80) != 0:
			self.f += C_FLAG
		self.a = s;
		self.cycles -= 1;


	 # RRCA
	def rrca(self):
		self.f = 0
		if (self.a & 0x01) != 0:
			self.f += C_FLAG
		self.a = ((self.a >> 1) & 0x7F) + ((self.a << 7) & 0x80);
		self.cycles -= 1;


	 # RRA
	def rra(self):
		s = ((self.a >> 1) & 0x7F)
		if (self.f & C_FLAG) != 0:
			se += 0x80
		self.f = 0
		if (self.a & 0x01) != 0:
			self.f += C_FLAG
		self.a = s;
		self.cycles -= 1;

	 # CCF/SCF
	def ccf(self):
		self.f = (self.f & (Z_FLAG | C_FLAG)) ^ C_FLAG;


	def scf(self):
		self.f = (self.f & Z_FLAG) | C_FLAG;


	 # NOP
	def nop(self):
		self.cycles -= 1;


	 # JP nnnn
	def jp_nnnn(self):
		lo = self.fetch();
		hi = self.fetch();
		self.pc = (hi << 8) + lo;
		self.cycles -= 4;


	 # LD PC,HL
	def ld_PC_HL(self):
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
	

	def jp_NZ_nnnn(self):
		self.jp_cc_nnnn((self.f & Z_FLAG) == 0);


	def jp_NC_nnnn(self):
		self.jp_cc_nnnn((self.f & C_FLAG) == 0);


	def jp_Z_nnnn(self):
		self.jp_cc_nnnn((self.f & Z_FLAG) != 0);


	def jp_C_nnnn(self):
		self.jp_cc_nnnn((self.f & C_FLAG) != 0);


	 # JR +nn
	def jr_nn(self):
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
	

	def jr_NZ_nn(self):
		self.jr_cc_nn((self.f & Z_FLAG) == 0);


	def jr_Z_nn(self):
		self.jr_cc_nn((self.f & Z_FLAG) != 0);


	def jr_NC_nn(self):
		self.jr_cc_nn((self.f & C_FLAG) == 0);


	def jr_C_nn(self):
		self.jr_cc_nn((self.f & C_FLAG) != 0);


	 # CALL nnnn
	def call_nnnn(self):
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
	


	def call_NZ_nnnn(self):
		self.call_cc_nnnn((self.f & Z_FLAG) == 0);


	def call_NC_nnnn(self):
		self.call_cc_nnnn((self.f & C_FLAG) == 0);


	def call_Z_nnnn(self):
		self.call_cc_nnnn((self.f & Z_FLAG) != 0);


	def call_C_nnnn(self):
		self.call_cc_nnnn((self.f & C_FLAG) != 0);


	 # RET
	def ret(self):
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


	def ret_NZ(self):
		self.ret_cc((self.f & Z_FLAG) == 0);


	def ret_NC(self):
		self.ret_cc((self.f & C_FLAG) == 0);


	def ret_Z(self):
		self.ret_cc((self.f & Z_FLAG) != 0);


	def ret_C(self):
		self.ret_cc((self.f & C_FLAG) != 0);


	 # RST nn
	def rst(self, nn):
		self.call(nn);
		self.cycles -= 4;


	 # RETI
	def reti(self):
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
	def di(self):
		# disable interrupts
		self.ime = false;
		self.cycles -= 1; 


	def ei(self):
		# enable interrupts
		self.ime = true;
		self.cycles -= 1;
		# execute next instruction
		self.execute();
		# check pending interrupts
		self.interrupt();


	 # HALT/STOP
	def halt(self):
		self.halted = true;
		# emulate bug when interrupts are pending
		if (not self.ime and self.interrupt.isPending()):
			self.execute(self.memory.read(self.pc));
		# check pending interrupts
		self.interrupt();


	def stop(self):
		self.fetch();

