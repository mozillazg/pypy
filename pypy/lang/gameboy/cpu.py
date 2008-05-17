
from pypy.lang.gameboy import constants
from pypy.lang.gameboy.ram import *
from pypy.lang.gameboy.interrupt import *


class iRegister(object):
    def get(self, use_cycles=True):
        return 0xFF

class Register(iRegister):
    
    def __init__(self, cpu, value=0):
        assert isinstance(cpu, CPU)
        self.reset_value = self.value = value
        self.cpu = cpu
        if value != 0:
            self.set(value)
        
    def reset(self):
        self.value = self.reset_value
        
    def set(self, value, use_cycles=True):
        self.value = value & 0xFF
        if use_cycles:
            self.cpu.cycles -= 1
        
    def get(self, use_cycles=True):
        return self.value
    
    def add(self, value, use_cycles=True):
        self.set(self.get(use_cycles)+value, use_cycles)
        
    def sub(self, value, use_cycles=True):
        self.set(self.get(use_cycles)-value, use_cycles)
    
#------------------------------------------------------------------------------

class DoubleRegister(iRegister):
    
    def __init__(self, cpu, hi, lo, reset_value=0):
        assert isinstance(cpu, CPU)
        assert isinstance(lo, Register)
        assert isinstance(hi, Register)
        self.cpu = cpu
        self.hi = hi
        self.lo = lo
        self.reset_value = reset_value
        
    def set(self, hi=0, lo=-1, use_cycles=True):
        if lo < 0:
            self.set_hi(hi >> 8, use_cycles)
            self.set_lo(hi & 0xFF, use_cycles)
            if use_cycles:
                self.cpu.cycles += 1
        else:
            self.set_hi(hi, use_cycles)
            self.set_lo(lo, use_cycles) 
            
    def reset(self):
        self.set(self.reset_value, use_cycles=False)
            
    def set_hi(self, hi=0, use_cycles=True):
        self.hi.set(hi, use_cycles)
    
    def set_lo(self, lo=0, use_cycles=True):
        self.lo.set(lo, use_cycles)
        
    def get(self, use_cycles=True):
        return (self.hi.get(use_cycles)<<8) + self.lo.get(use_cycles)
    
    def get_hi(self, use_cycles=True):
        return self.hi.get(use_cycles)
        
    def get_lo(self, use_cycles=True):
        return self.lo.get(use_cycles)
    
    def inc(self, use_cycles=True):
        self.set(self.get(use_cycles) +1, use_cycles=use_cycles)
        if use_cycles:
            self.cpu.cycles -= 1
        
    def dec(self, use_cycles=True):
        self.set(self.get(use_cycles) - 1, use_cycles=use_cycles)
        if use_cycles:
            self.cpu.cycles -= 1
        
    def add(self, n=2, use_cycles=True):
        self.set(self.get(use_cycles) + n, use_cycles=use_cycles)
        if use_cycles:
            self.cpu.cycles -= 2
    
# ------------------------------------------------------------------------------

class ImmediatePseudoRegister(iRegister):
    
        def __init__(self, cpu, hl):
            assert isinstance(cpu, CPU)
            self.cpu = cpu
            self.hl = hl
            
        def set(self, value, use_cycles=True):
            self.cpu.write(self.hl.get(use_cycles=use_cycles), value) # 2 + 0
            if not use_cycles:
                self.cpu.cycles += 2
        
        def get(self, use_cycles=True):
            if not use_cycles:
                self.cpu.cycles += 1
            return self.cpu.read(self.hl.get(use_cycles=use_cycles)) # 1
    
# ------------------------------------------------------------------------------
  
class FlagRegister(Register):
    
    def __init__(self, cpu):
        assert isinstance(cpu, CPU)
        self.cpu = cpu
        self.reset()
         
    def reset(self, keep_z=False, keep_n=False, keep_h=False, keep_c=False,\
                keep_p=False, keep_s=False):
        if not keep_z:
            self.z_flag = False
        if not keep_n:
            self.n_flag = False
        if not keep_h:
            self.h_flag = False
        if not keep_c:
            self.c_flag = False
        if not keep_p:
            self.p_flag = False
        if not keep_s:
            self.s_flag = False
        self.lower = 0x00
            
    def get(self, use_cycles=True):
        value = 0
        value += (int(self.c_flag) << 4)
        value += (int(self.h_flag) << 5)
        value += (int(self.n_flag) << 6)
        value += (int(self.z_flag) << 7)
        return value + self.lower
            
    def set(self, value, use_cycles=True):
        self.c_flag = bool(value & (1 << 4))
        self.h_flag = bool(value & (1 << 5))
        self.n_flag = bool(value & (1 << 6))
        self.z_flag = bool(value & (1 << 7))
        self.lower = value & 0x0F
        if use_cycles:
            self.cpu.cycles -= 1
        
    def z_flag_compare(self, a, reset=False):
        if reset:
             self.reset()
        if isinstance(a, (Register)):
            a = a.get()
        self.z_flag = ((a & 0xFF) == 0)
            
    def c_flag_add(self, s, compare_and=0x01, reset=False):
        if reset:
             self.reset()
        if (s & compare_and) != 0:
            self.c_flag = True

    def h_flag_compare(self, a, b):
        if (a & 0x0F) < (b & 0x0F):
            self.h_flag = True
            
    def c_flag_compare(self,  a, b):
        if a < b:
            self.c_flag = True
        
# # ------------------------------------------------------------------------------

class CPU(object):
    """
    PyBoy GameBoy (TM) Emulator
    
    Central Unit ProcessOR (Sharp LR35902 CPU)
    """
    def __init__(self, interrupt, memory):
        assert isinstance(interrupt, Interrupt)
        self.interrupt = interrupt
        self.memory = memory
        self.ime = False
        self.halted = False
        self.cycles = 0
        self.ini_registers()
        self.rom = []
        self.reset()

    def ini_registers(self):
        self.b  = Register(self)
        self.c  = Register(self)
        self.bc = DoubleRegister(self, self.b, self.c, constants.RESET_BC)
        
        self.d  = Register(self)
        self.e  = Register(self)
        self.de = DoubleRegister(self, self.d, self.e, constants.RESET_DE)

        self.h  = Register(self)
        self.l  = Register(self)
        self.hl = DoubleRegister(self, self.h, self.l, constants.RESET_HL)
        
        self.hli = ImmediatePseudoRegister(self, self.hl)
        self.pc  = DoubleRegister(self, Register(self), Register(self), reset_value=constants.RESET_PC)
        self.sp  = DoubleRegister(self, Register(self), Register(self), reset_value=constants.RESET_SP)
        
        self.a  = Register(self, constants.RESET_A)
        self.f  = FlagRegister(self)
        self.af = DoubleRegister(self, self.a, self.f)
        

    def reset(self):
        self.reset_registers()
        self.f.reset()
        self.f.z_flag = True
        self.ime     = False
        self.halted  = False
        self.cycles  = 0
        
    def reset_registers(self):
        self.a.reset()
        self.f.reset()
        self.bc.reset()
        self.de.reset()
        self.hl.reset()
        self.sp.reset()
        self.pc.reset()
        
    def get_af(self):
        return self.af
        
    def get_a(self):
        return self.a
    
    def get_f(self):
        return self.f
        
    def get_bc(self):
        return self.bc
    
    def get_b(self):
        return self.b
    
    def get_c(self):
        return self.c
        
    def get_de(self):
        return self.de
        
    def get_d(self):
        return self.d
        
    def get_e(self):
        return self.e
        
    def get_hl(self):
        return self.hl
        
    def get_hli(self):
        return self.hli
        
    def get_h(self):
        return self.h
        
    def get_l(self):
        return self.l
             
    def get_sp(self):
        return self.sp

    def get_if(self):
        val = 0x00
        if self.ime:
            val = 0x01
        if self.halted:
            val += 0x80
        return val

    def is_z(self):
        """ zero flag"""
        return self.f.z_flag

    def is_c(self):
        """ carry flag, true if the result did not fit in the register"""
        return self.f.c_flag

    def is_h(self):
        """ half carry, carry from bit 3 to 4"""
        return self.f.h_flag

    def is_n(self):
        """ subtract flag, true if the last operation was a subtraction"""
        return self.f.n_flag
    
    def isS(self):
        return self.f.s_flag
    
    def is_p(self):
        return self.f.p_flag
    
    def is_not_z(self):
        return not self.is_z()

    def is_not_c(self):
        return not self.is_c()
    
    def is_not_h(self):
        return not self.is_h()

    def is_not_n(self):
        return not self.is_n()

    def set_rom(self, banks):
        self.rom = banks       
            
    def emulate(self, ticks):
        self.cycles += ticks
        self.handle_pending_interrupt()
        while self.cycles > 0:
            self.execute(self.fetch())

    def handle_pending_interrupt(self):
        # Interrupts
        if self.halted:
            if self.interrupt.is_pending():
                self.halted = False
                self.cycles -= 4
            elif (self.cycles > 0):
                self.cycles = 0
        if self.ime and self.interrupt.is_pending():
            self.lower_pending_interrupt()
            
    def lower_pending_interrupt(self):
        for flag in self.interrupt.interrupt_flags:
            if flag.is_pending():
                self.ime = False
                self.call(flag.call_code, use_cycles=False)
                flag.set_pending(False)
                return

    def fetch_execute(self):
        # Execution
        FETCH_EXECUTE_OP_CODES[self.fetch()](self)
        
    def execute(self, opCode):
        OP_CODES[opCode](self)
        
    def read(self, hi, lo=None):
        # memory Access, 1 cycle
        address = hi
        if lo is not None:
            address = (hi << 8) + lo
        self.cycles -= 1
        return self.memory.read(address)

    def write(self, address, data):
        # 2 cycles
        self.memory.write(address, data)
        self.cycles -= 2

    def fetch(self, use_cycles=True):
        # Fetching  1 cycle
        self.cycles += 1
        if self.pc.get(use_cycles) <= 0x3FFF:
            data =  self.rom[self.pc.get(use_cycles)]
        else:
            data = self.memory.read(self.pc.get(use_cycles))
        self.pc.inc(use_cycles) # 2 cycles
        return data
    
    def fetch_double_address(self):
        lo = self.fetch() # 1 cycle
        hi = self.fetch() # 1 cycle
        return (hi << 8) + lo
        
    def fetch_double_register(self, register):
        self.double_register_inverse_call(CPU.fetch, register)

    def push(self, data, use_cycles=True):
        # Stack, 2 cycles
        self.sp.dec(use_cycles) # 2 cycles
        self.memory.write(self.sp.get(use_cycles), data)
        
    def push_double_register(self, register, use_cycles=True):
        # PUSH rr 4 cycles
        self.push(register.get_hi(), use_cycles) # 2 cycles
        self.push(register.get_lo(), use_cycles) # 2 cycles

    def pop(self):
        # 1 cycle
        data = self.memory.read(self.sp.get())
        self.sp.inc() # 2 cycles
        self.cycles += 1
        return data
    
    def pop_double_register(self, register):
        # 3 cycles
        self.double_register_inverse_call(CPU.pop, register)
        
    def double_register_inverse_call(self, getter, register):
        b = getter(self) # 1 cycle
        a = getter(self) # 1 cycle
        register.set(a, b) # 2 cycles
        self.cycles += 1
        
    def call(self, address, use_cycles=True):
        # 4 cycles
        self.push(self.pc.get_hi(use_cycles), use_cycles) # 2 cycles
        self.push(self.pc.get_lo(use_cycles), use_cycles) # 2 cycles
        self.pc.set(address, use_cycles=use_cycles)       # 1 cycle
        if use_cycles:
            self.cycles += 1
        
    def ld(self, getter, setter):
        # 1 cycle
        setter(getter()) # 1 cycle
        
    def load_fetch_register(self, register):
        self.ld(self.fetch, register.set)
        
    def store_hl_in_pc(self):
        # LD PC,HL, 1 cycle
        self.ld(self.hl.get, self.pc.set)
        
    def fetch_load(self, getter, setter):
        self.ld(self.fetch, setter)

    def add_a(self, getter, setter=None):
        # ALU, 1 cycle
        added = (self.a.get() + getter()) & 0xFF
        self.f.z_flag_compare(added, reset=True)
        self.f.h_flag_compare(added, self.a.get())
        self.f.c_flag_compare(added, self.a.get())
        self.a.set(added) # 1 cycle
        
    def add_hl(self, register):
        # 2 cycles
        a=1
        added = (self.hl.get() + register.get()) & 0xFFFF # 1 cycle
        self.f.reset(keep_z=True)
        self.f.h_flag_compare((added >> 8), self.hl.get())
        self.f.c_flag_compare(added, self.hl.get())
        self.hl.set(added)
        self.cycles -= 1
        
    def add_with_carry(self, getter, setter=None):
        # 1 cycle
        data = getter()
        s = self.a.get() + data
        if self.f.c_flag:
            s +=1
        self.carry_flag_finish(s,data)

    def subtract_with_carry(self, getter, setter=None):
        # 1 cycle
        data = getter()
        s = self.a.get() - data
        if self.f.c_flag:
            s -= 1
        self.carry_flag_finish(s, data)
        self.f.n_flag = True
        
    def carry_flag_finish(self, s, data):
        self.f.reset()
        # set the hflag if the 0x10 bit was affected
        if ((s ^ self.a.get() ^ data) & 0x10) != 0:
            self.f.h_flag = True
        if s >= 0x100:
            self.f.c_flag= True
        self.f.z_flag_compare(s)
        self.a.set(s)  # 1 cycle
        
    def subtract_a(self, getter, setter=None):
        # 1 cycle
        self.compare_a(getter) # 1 cycle
        self.a.sub(getter(use_cycles=False), False)

    def fetch_subtract_a(self):
        data = self.fetch()
        # 1 cycle
        self.compare_a_simple(data) # 1 cycle
        self.a.sub(data, False)

    def compare_a(self, getter, setter=None):
        # 1 cycle
        self.compare_a_simple(int(self.a.get() - getter()))
        
    def compare_a_simple(self, s):
        s = s & 0xFF
        self.f.reset()
        self.f.n_flag = True
        self.f.z_flag_compare(s)
        self.hc_flag_finish(s)
        self.cycles -= 1
            
    def hc_flag_finish(self, data):
        if data > self.a.get():
            self.f.c_flag = True
        self.f.h_flag_compare(self.a.get(), data)
        
    def AND(self, getter, setter=None):
        # 1 cycle
        self.a.set(self.a.get() & getter())  # 1 cycle
        self.f.z_flag_compare(self.a.get(), reset=True)

    def XOR(self, getter, setter=None):
        # 1 cycle
        self.a.set( self.a.get() ^ getter())  # 1 cycle
        self.f.z_flag_compare(self.a.get(), reset=True)

    def OR(self, getter, setter=None):
        # 1 cycle
        self.a.set(self.a.get() | getter())  # 1 cycle
        self.f.z_flag_compare(self.a.get(), reset=True)

    def inc_double_register(self, doubleRegister):
        doubleRegister.inc()
        
    def dec_double_register(self, doubleRegister):
        doubleRegister.dec()
        
    def inc(self, getter, setter):
        # 1 cycle
        data = (getter() + 1) & 0xFF
        self.decInc_flagFinish(data, setter, 0x00)
        
    def dec(self, getter, setter):
        # 1 cycle
        data = (getter() - 1) & 0xFF
        self.decInc_flagFinish(data, setter, 0x0F)
        self.f.n_flag = True
     
    def decInc_flagFinish(self, data, setter, compare):
        self.f.reset(keep_c=True)
        self.f.z_flag_compare(data)
        if (data & 0x0F) == compare:
            self.f.h_flag = True
        setter(data) # 1 cycle

    def rotate_left_circular(self, getter, setter):
        # RLC 1 cycle
        data = getter()
        s = (data  << 1) + (data >> 7)
        self.flags_and_setter_finish(s, setter, 0x80)
        #self.cycles -= 1

    def rotate_left_circular_a(self):
        # RLCA rotate_left_circular_a 1 cycle
        self.rotate_left_circular(self.a.get, self.a.set)

    def rotate_left(self, getter, setter):
        # 1 cycle
        s = (getter() << 1) & 0xFF
        if self.f.c_flag:
            s += 0x01
        self.flags_and_setter_finish(s, setter, 0x80) # 1 cycle

    def rotate_left_a(self):
        # RLA  1 cycle
        self.rotate_left(self.a.get, self.a.set)
        
    def rotate_right_circular(self, getter, setter):
        data = getter()
        # RRC 1 cycle
        s = (data >> 1) + ((data & 0x01) << 7)
        self.flags_and_setter_finish(s, setter) # 1 cycle
   
    def rotate_right_circular_a(self):
        # RRCA 1 cycle
        self.rotate_right_circular(self.a.get, self.a.set)

    def rotate_right(self, getter, setter):
        # 1 cycle
        s = (getter() >> 1)
        if self.f.c_flag:
            s +=  0x08
        self.flags_and_setter_finish(s, setter) # 1 cycle

    def rotate_right_a(self):
        # RRA 1 cycle
        self.rotate_right(self.a.get, self.a.set)

    def shift_left_arithmetic(self, getter, setter):
        # 2 cycles
        s = (getter() << 1) & 0xFF
        self.flags_and_setter_finish(s, setter, 0x80) # 1 cycle

    def shift_right_arithmetic(self, getter, setter):
        data = getter()
        # 1 cycle
        s = (data >> 1) + (data & 0x80)
        self.flags_and_setter_finish(s, setter) # 1 cycle

    def shift_word_right_logical(self, getter, setter):
        # 2 cycles
        s = (getter() >> 1)
        self.flags_and_setter_finish(s, setter) # 2 cycles
        
    def flags_and_setter_finish(self, s, setter, compare_and=0x01):
        # 2 cycles
        s &= 0xFF
        self.f.z_flag_compare(s,  reset=True)
        self.f.c_flag_add(s, compare_and)
        setter(s) # 1 cycle

    def swap(self, getter, setter):
        data = getter()
        # 1 cycle
        s = ((data << 4) + (data >> 4)) & 0xFF
        self.f.z_flag_compare(s, reset=True)
        setter(s)

    def test_bit(self, getter, setter, n):
        # 2 cycles
        self.f.reset(keep_c=True)
        self.f.h_flag = True
        self.f.z_flag = False
        if (getter() & (1 << n)) == 0:
            self.f.z_flag = True
        self.cycles -= 1

    def set_bit(self, getter, setter, n):
        # 1 cycle
        setter(getter() | (1 << n)) # 1 cycle
        
    def reset_bit(self, getter, setter, n):
        # 1 cycle
        setter(getter() & (~(1 << n))) # 1 cycle
        
    def store_fetched_memory_in_a(self):
        # LD A,(nnnn), 4 cycles
        self.a.set(self.read(self.fetch_double_address()))  # 1+1 + 2 cycles

    def write_a_at_bc_address(self):
        # 2 cycles
        self.write(self.bc.get(), self.a.get())
        
    def write_a_at_de_address(self):
        self.write(self.de.get(), self.a.get())
           
    def store_memory_at_bc_in_a(self):
        self.a.set(self.read(self.bc.get()))

    def store_memory_at_de_in_a(self):
        self.a.set(self.read(self.de.get()))

    def ld_dbRegisteri_A(self, register):
        # LD (rr),A  2 cycles
        self.write(register.get(), self.a.get()) # 2 cycles

    def load_mem_sp(self):
        # LD (nnnn),SP  5 cycles
        address = self.fetch_double_address() # 2 cycles
        self.write(address, self.sp.get_lo())  # 2 cycles
        self.write((address + 1), self.sp.get_hi()) # 2 cycles
        self.cycles += 1

    def store_a_at_fetched_address(self):
        # LD (nnnn),A  4 cycles
        self.write(self.fetch_double_address(), self.a.get()) # 2 cycles

    def store_memory_at_axpanded_fetch_address_in_a(self):
        # LDH A,(nn) 3 cycles
        self.a.set(self.read(0xFF00 + self.fetch())) # 1+1+1 cycles
        
    def store_expanded_c_in_a(self):
        # LDH A,(C) 2 cycles
        self.a.set(self.read(0xFF00 + self.bc.get_lo())) # 1+2 cycles
        
    def load_and_increment_a_hli(self):
        # loadAndIncrement A,(HL) 2 cycles
        self.a.set(self.read(self.hl.get())) # 2 cycles
        self.hl.inc()# 2 cycles
        self.cycles += 2
        
    def load_and_decrement_a_hli(self):
        # loadAndDecrement A,(HL)  2 cycles
        self.a.set(self.read(self.hl.get())) # 2 cycles
        self.hl.dec() # 2 cycles
        self.cycles += 2
        
    def write_a_at_expanded_fetch_address(self):
        # LDH (nn),A 3 cycles
        self.write(0xFF00 + self.fetch(), self.a.get()) # 2 + 1 cycles

    def write_a_at_expaded_c_address(self):
        # LDH (C),A 2 cycles
        self.write(0xFF00 + self.bc.get_lo(), self.a.get()) # 2 cycles
        
    def load_and_increment_hli_a(self):
        # loadAndIncrement (HL),A 2 cycles
        self.write(self.hl.get(), self.a.get()) # 2 cycles
        self.hl.inc() # 2 cycles
        self.cycles += 2

    def load_and_decrement_hli_a(self):
        # loadAndDecrement (HL),A  2 cycles
        self.write(self.hl.get(), self.a.get()) # 2 cycles
        self.hl.dec() # 2 cycles
        self.cycles += 2

    def store_hl_in_sp(self):
        # LD SP,HL 2 cycles
        self.sp.set(self.hl.get()) # 1 cycle
        self.cycles -= 1

    def complement_a(self):
        # CPA
        self.a.set(self.a.get() ^ 0xFF)
        self.f.n_flag = True
        self.f.h_flag = True

    def decimal_adjust_accumulator(self):
        # DAA 1 cycle
        delta = 0
        if self.is_h(): 
            delta |= 0x06
        if self.is_c():
            delta |= 0x60
        if (self.a.get() & 0x0F) > 0x09:
            delta |= 0x06
            if (self.a.get() & 0xF0) > 0x80:
                delta |= 0x60
        if (self.a.get() & 0xF0) > 0x90:
            delta |= 0x60
        if not self.is_n():
            self.a.set((self.a.get() + delta) & 0xFF) # 1 cycle
        else:
            self.a.set((self.a.get() - delta) & 0xFF) # 1 cycle
        self.f.reset(keep_n=True)
        if delta >= 0x60:
            self.f.c_flag = True
        self.f.z_flag_compare(self.a.get())

    def inc_double_register(self, register):
        # INC rr
        register.inc()

    def dec_double_register(self, register):
        # DEC rr
        register.dec()

    def increment_sp_by_fetch(self):
        # ADD SP,nn 4 cycles
        self.sp.set(self.get_fetchadded_sp()) # 1+1 cycle
        self.cycles -= 2

    def store_fetch_added_sp_in_hl(self):
        # LD HL,SP+nn   3  cycles
        self.hl.set(self.get_fetchadded_sp()) # 1+1 cycle
        self.cycles -= 1

    def get_fetchadded_sp(self):
        # 1 cycle
        offset = self.fetch() # 1 cycle
        s = (self.sp.get() + offset) & 0xFFFF
        self.f.reset()
        if (offset >= 0):
            if s < self.sp.get():
                self.f.c_flag = True
            if (s & 0x0F00) < (self.sp.get() & 0x0F00):
                self.f.h_flag = True
        else:
            if s > self.sp.get():
                self.f.c_flag = True
            if (s & 0x0F00) > (self.sp.get() & 0x0F00):
                self.f.h_flag = True
        return s

    def complement_carry_flag(self):
        # CCF/SCF
        self.f.reset(keep_z=True, keep_c=True)
        self.f.c_flag = not self.f.c_flag

    def set_carry_flag(self):
        self.f.reset(keep_z=True)
        self.f.c_flag = True

    def nop(self):
        # NOP 1 cycle
        self.cycles -= 1

    def unconditional_jump(self):
        # JP nnnn, 4 cycles
        self.pc.set(self.fetch_double_address()) # 1+2 cycles
        self.cycles -= 1

    def conditional_jump(self, cc):
        # JP cc,nnnn 3,4 cycles
        if cc:
            self.unconditional_jump() # 4 cycles
        else:
            self.pc.add(2) # 3 cycles

    def relative_unconditional_jump(self):
        # JR +nn, 3 cycles
        self.pc.add(self.fetch()) # 3 + 1 cycles
        self.cycles += 1

    def relative_conditional_jump(self, cc):
        # JR cc,+nn, 2,3 cycles
        if cc:
            self.relative_unconditional_jump() # 3 cycles
        else:
            self.pc.inc() # 2 cycles
    
    def unconditional_call(self):
        # CALL nnnn, 6 cycles
        self.call(self.fetch_double_address())  # 4+2 cycles

    def conditional_call(self, cc):
        # CALL cc,nnnn, 3,6 cycles
        if cc:
            self.unconditional_call() # 6 cycles
        else:
            self.pc.add(2) # 3 cycles

    def ret(self):
        # RET 4 cycles
        lo = self.pop() # 1 cycle
        hi = self.pop() # 1 cycle
        self.pc.set(hi, lo) # 2 cycles

    def conditional_return(self, cc):
        # RET cc 2,5 cycles
        if cc:
            self.ret() # 4 cycles
            # FIXME maybe this should be the same
            self.cycles -= 1
        else:
            self.cycles -= 2

    def return_form_interrupt(self):
        # RETI 4 cycles
        self.ret() # 4 cycles
        self.enable_interrupts() # 1 cycle + others
        self.cycles += 1

    def restart(self, nn):
        # RST nn 4 cycles
        self.call(nn) # 4 cycles

    def disable_interrups(self):
        # DI/EI 1 cycle
        self.ime = False
        self.cycles -= 1

    def enable_interrupts(self):
        # 1 cycle
        self.ime = True
        self.execute(self.fetch()) #  1
        self.handle_pending_interrupt()

    def halt(self):
        # HALT/STOP
        self.halted = True
        # emulate bug when interrupts are pending
        if not self.ime and self.interrupt.is_pending():
            self.execute(self.memory.read(self.pc.get()))
        self.handle_pending_interrupt()

    def stop(self):
        # 0 cycles
        self.cycles += 1
        self.fetch()

# ------------------------------------------------------------------------------
# OPCODE LOOKUP TABLE GENERATION -----------------------------------------------


GROUPED_REGISTERS = (CPU.get_b, CPU.get_c, CPU.get_d, CPU.get_e, CPU.get_h, CPU.get_l, CPU.get_hli, CPU.get_a)

def create_group_op_codes(table):
    opCodes =[]
    for entry in table:
        opCode   = entry[0]
        step     = entry[1]
        function = entry[2]
        if len(entry) == 4:
            for registerGetter in GROUPED_REGISTERS:
                for n in entry[3]:
                    opCodes.append((opCode, group_lambda(function, registerGetter, n)))
                    opCode += step
        if len(entry) == 5:
            entryStep = entry[4]
            for registerGetter in GROUPED_REGISTERS:
                stepOpCode = opCode
                for n in entry[3]:
                    opCodes.append((stepOpCode, group_lambda(function, registerGetter, n)))
                    stepOpCode += entryStep
                opCode+=step
        else:
            for registerGetter in GROUPED_REGISTERS:
                opCodes.append((opCode,group_lambda(function, registerGetter)))
                opCode += step
    return opCodes

def group_lambda(function, registerGetter, value=None):
    if value is None:
        return lambda s: function(s, registerGetter(s).get, registerGetter(s).set)
    else:
        return  lambda s: function(s, registerGetter(s).get, registerGetter(s).set, value)


def create_load_group_op_codes():
    opCodes = []
    opCode  = 0x40
    for storeRegister in GROUPED_REGISTERS:
        for loadRegister in GROUPED_REGISTERS:
            if loadRegister != CPU.get_hli or storeRegister != CPU.get_hli:
                opCodes.append((opCode, load_group_lambda(storeRegister, loadRegister)))
            opCode += 1
    return opCodes
            
def load_group_lambda(storeRegister, loadRegister):
        return lambda s: CPU.ld(s, loadRegister(s).get, storeRegister(s).set)
    
    
def create_register_op_codes(table):
    opCodes = []
    for entry in table:
        opCode   = entry[0]
        step     = entry[1]
        function = entry[2]
        for registerOrGetter in entry[3]:
            opCodes.append((opCode, register_lambda(function, registerOrGetter)))
            opCode += step
    return opCodes

def register_lambda(function, registerOrGetter):
    if callable(registerOrGetter):
        return lambda s: function(s, registerOrGetter(s))
    else:
        return lambda s: function(s, registerOrGetter)
        
        
def initialize_op_code_table(table):
    result = [None] * (0xFF+1)
    for entry in  table:
        if (entry is None) or (len(entry) == 0) or entry[-1] is None:
            continue
        if len(entry) == 2:
            positions = [entry[0]]
        else:
            positions = range(entry[0], entry[1]+1)
        for pos in positions:
            result[pos] = entry[-1]
    return result

# OPCODE TABLES ---------------------------------------------------------------
                        
FIRST_ORDER_OP_CODES = [
    (0x00, CPU.nop),
    (0x08, CPU.load_mem_sp),
    (0x10, CPU.stop),
    (0x18, CPU.relative_unconditional_jump),
    (0x02, CPU.write_a_at_bc_address),
    (0x12, CPU.write_a_at_de_address),
    (0x22, CPU.load_and_increment_hli_a),
    (0x32, CPU.load_and_decrement_hli_a),
    (0x0A, CPU.store_memory_at_bc_in_a),
    (0x1A, CPU.store_memory_at_de_in_a),
    (0x2A, CPU.load_and_increment_a_hli),
    (0x3A, CPU.load_and_decrement_a_hli),
    (0x07, CPU.rotate_left_circular_a),
    (0x0F, CPU.rotate_right_circular_a),
    (0x17, CPU.rotate_left_a),
    (0x1F, CPU.rotate_right_a),
    (0x27, CPU.decimal_adjust_accumulator),
    (0x2F, CPU.complement_a),
    (0x37, CPU.set_carry_flag),
    (0x3F, CPU.complement_carry_flag),
    (0x76, CPU.halt),
    (0xF3, CPU.disable_interrups),
    (0xFB, CPU.enable_interrupts),
    (0xE2, CPU.write_a_at_expaded_c_address),
    (0xEA, CPU.store_a_at_fetched_address),
    (0xF2, CPU.store_expanded_c_in_a),
    (0xFA, CPU.store_fetched_memory_in_a),
    (0xC3, CPU.unconditional_jump),
    (0xC9, CPU.ret),
    (0xD9, CPU.return_form_interrupt),
    (0xE9, CPU.store_hl_in_pc),
    (0xF9, CPU.store_hl_in_sp),
    (0xE0, CPU.write_a_at_expanded_fetch_address),
    (0xE8, CPU.increment_sp_by_fetch),
    (0xF0, CPU.store_memory_at_axpanded_fetch_address_in_a),
    (0xF8, CPU.store_fetch_added_sp_in_hl),
    (0xCB, CPU.fetch_execute),
    (0xCD, CPU.unconditional_call),
    (0xC6, lambda s: CPU.add_a(s, s.fetch)),
    (0xCE, lambda s: CPU.add_with_carry(s,  s.fetch)),
    (0xD6, CPU.fetch_subtract_a),
    (0xDE, lambda s: CPU.subtract_with_carry(s,  s.fetch)),
    (0xE6, lambda s: CPU.AND(s,  s.fetch)),
    (0xEE, lambda s: CPU.XOR(s,  s.fetch)),
    (0xF6, lambda s: CPU.OR(s,   s.fetch)),
    (0xFE, lambda s: CPU.compare_a(s,  s.fetch)),
    (0xC7, lambda s: CPU.restart(s, 0x00)),
    (0xCF, lambda s: CPU.restart(s, 0x08)),
    (0xD7, lambda s: CPU.restart(s, 0x10)),
    (0xDF, lambda s: CPU.restart(s, 0x18)),
    (0xE7, lambda s: CPU.restart(s, 0x20)),
    (0xEF, lambda s: CPU.restart(s, 0x28)),
    (0xF7, lambda s: CPU.restart(s, 0x30)),
    (0xFF, lambda s: CPU.restart(s, 0x38)),
]

REGISTER_GROUP_OP_CODES = [
    (0x04, 0x08, CPU.inc),
    (0x05, 0x08, CPU.dec),    
    (0x06, 0x08, CPU.load_fetch_register),
    (0x80, 0x01, CPU.add_a),    
    (0x88, 0x01, CPU.add_with_carry),    
    (0x90, 0x01, CPU.subtract_a),    
    (0x98, 0x01, CPU.subtract_with_carry),    
    (0xA0, 0x01, CPU.AND),    
    (0xA8, 0x01, CPU.XOR),    
    (0xB0, 0x01, CPU.OR),
    (0xB8, 0x01, CPU.compare_a),
    (0x06, 0x08, CPU.fetch_load)
]    
        

REGISTER_SET_A = [CPU.get_bc, CPU.get_de, CPU.get_hl, CPU.get_sp]
REGISTER_SET_B = [CPU.get_bc, CPU.get_de, CPU.get_hl, CPU.get_af]
FLAG_REGISTER_SET = [CPU.is_not_z, CPU.is_z, CPU.is_not_c, CPU.is_c]
REGISTER_OP_CODES = [ 
    (0x01, 0x10, CPU.fetch_double_register,     REGISTER_SET_A),
    (0x09, 0x10, CPU.add_hl,                    REGISTER_SET_A),
    (0x03, 0x10, CPU.inc_double_register,       REGISTER_SET_A),
    (0x0B, 0x10, CPU.dec_double_register,       REGISTER_SET_A),
    (0xC0, 0x08, CPU.conditional_return,        FLAG_REGISTER_SET),
    (0xC2, 0x08, CPU.conditional_jump,          FLAG_REGISTER_SET),
    (0xC4, 0x08, CPU.conditional_call,          FLAG_REGISTER_SET),
    (0x20, 0x08, CPU.relative_conditional_jump, FLAG_REGISTER_SET),
    (0xC1, 0x10, CPU.pop_double_register,       REGISTER_SET_B),
    (0xC5, 0x10, CPU.push_double_register,      REGISTER_SET_B)
]

SECOND_ORDER_REGISTER_GROUP_OP_CODES = [
    (0x00, 0x01, CPU.rotate_left_circular),    
    (0x08, 0x01, CPU.rotate_right_circular),    
    (0x10, 0x01, CPU.rotate_left),    
    (0x18, 0x01, CPU.rotate_right),    
    (0x20, 0x01, CPU.shift_left_arithmetic),    
    (0x28, 0x01, CPU.shift_right_arithmetic),    
    (0x30, 0x01, CPU.swap),    
    (0x38, 0x01, CPU.shift_word_right_logical),
    (0x40, 0x01, CPU.test_bit,  range(0, 8), 0x08),    
    (0xC0, 0x01, CPU.set_bit,   range(0, 8), 0x08),
    (0x80, 0x01, CPU.reset_bit, range(0, 8), 0x08)         
]

# RAW OPCODE TABLE INITIALIZATION ----------------------------------------------

FIRST_ORDER_OP_CODES += create_register_op_codes(REGISTER_OP_CODES)
FIRST_ORDER_OP_CODES += create_group_op_codes(REGISTER_GROUP_OP_CODES)
FIRST_ORDER_OP_CODES += create_load_group_op_codes()
SECOND_ORDER_OP_CODES = create_group_op_codes(SECOND_ORDER_REGISTER_GROUP_OP_CODES)


OP_CODES = initialize_op_code_table(FIRST_ORDER_OP_CODES)
FETCH_EXECUTE_OP_CODES = initialize_op_code_table(SECOND_ORDER_OP_CODES)
