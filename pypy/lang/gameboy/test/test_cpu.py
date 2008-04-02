import py
from pypy.lang.gameboy.cpu import *
from pypy.lang.gameboy.ram import *
from pypy.lang.gameboy import *

class Memory(object):
    def __init__(self):
        self.memory = [0xFF]*0xFFFFF
        
    def write(self, address, data):
        self.memory[address] = data
        
    def read(self, address):
        return self.memory[address]
    
def get_cpu():
    cpu =  CPU(None, Memory())
    cpu.setROM([0]*0xFFFF);
    return cpu

# ------------------------------------------------------------
# TEST REGISTER
def test_register_constructor():
    register = Register(get_cpu())
    assert register.get() == 0
    value = 10
    register = Register(get_cpu(), value)
    assert register.get() == value
    
def test_register():
    register = Register(get_cpu())
    value = 2
    oldCycles = register.cpu.cycles
    register.set(value)
    assert register.get() == value
    assert oldCycles-register.cpu.cycles == 1
    
def test_register_bounds():
    register = Register(get_cpu())
    value = 0x1234FF
    register.set(value)
    assert register.get() == 0xFF
    
def test_reset():
    value = 0x12
    register = Register(get_cpu(), value)
    register.set(value+1)
    assert register.get() == value+1
    register.reset()
    assert register.get() == value
    
# ------------------------------------------------------------
# TEST DOUBLE REGISTER

def test_double_register_constructor():
    cpu = get_cpu()
    register = DoubleRegister(cpu)
    assert register.get() == 0
    assert register.getHi() == 0
    assert register.getLo() == 0
    value = 0x1234
    reg1 = Register(cpu)
    reg1.set(0x12)
    reg2 = Register(cpu)
    reg2.set(0x34)
    register = DoubleRegister(cpu, reg1, reg2)
    assert register.hi == reg1
    assert register.lo == reg2
    assert register.getHi() == reg1.get()
    assert register.getLo() == reg2.get()
    
def test_double_register():
    register = DoubleRegister(get_cpu())
    value = 0x1234
    oldCycles = register.cpu.cycles
    register.set(value)
    assert oldCycles-register.cpu.cycles == 1
    assert register.get() == value
    
def test_double_register_bounds():
    register = DoubleRegister(get_cpu())
    value = 0xFFFF1234
    register.set(value)
    assert register.get() == 0x1234
    
def test_double_register_hilo():
    register = DoubleRegister(get_cpu())
    value = 0x1234
    valueHi = 0x12
    valueLo = 0x34
    oldCycles = register.cpu.cycles
    register.set(valueHi, valueLo)
    assert oldCycles-register.cpu.cycles == 2
    assert register.getHi() == valueHi
    assert register.getLo() == valueLo
    assert register.get() == value
    
    valueHi = 0x56
    oldCycles = register.cpu.cycles
    register.setHi(valueHi)
    assert oldCycles-register.cpu.cycles == 1
    assert register.getHi() == valueHi
    assert register.getLo() == valueLo
    
    valueLo = 0x78
    oldCycles = register.cpu.cycles
    register.setLo(valueLo)
    assert oldCycles-register.cpu.cycles == 1
    assert register.getHi() == valueHi
    assert register.getLo() == valueLo
    
    
def test_double_register_methods():
    value = 0x1234
    register = DoubleRegister(get_cpu())
    register.set(value)
    
    oldCycles = register.cpu.cycles
    register.inc()
    assert oldCycles-register.cpu.cycles == 2
    assert register.get() == value+1
    
    oldCycles = register.cpu.cycles
    register.dec()
    assert oldCycles-register.cpu.cycles == 2
    assert register.get() == value
    
    addValue = 0x1001
    oldCycles = register.cpu.cycles
    register.add(addValue)
    assert oldCycles-register.cpu.cycles == 3
    assert register.get() == value+addValue
    
       
def test_double_register_reset():
    value = 0x1234;
    
    register = DoubleRegister(get_cpu(), value)
    register.set(value+1)
    assert register.get() == value+1;
    register.reset()
    assert register.get() == value
# ------------------------------------------------------------
# TEST CPU

def test_getters():
    cpu = get_cpu()
    assert_default_registers(cpu)
    assert cpu.af.cpu == cpu
    assert cpu.a.cpu == cpu
    assert cpu.f.cpu == cpu
    
    assert cpu.bc.cpu == cpu
    assert cpu.b.cpu == cpu
    assert cpu.c.cpu == cpu
    
    assert cpu.de.cpu == cpu
    assert cpu.d.cpu == cpu
    assert cpu.e.cpu == cpu
    
    assert cpu.hl.cpu == cpu
    assert cpu.hli.cpu == cpu
    assert cpu.h.cpu == cpu
    assert cpu.l.cpu == cpu
    
    assert cpu.sp.cpu == cpu
    assert cpu.pc.cpu == cpu
    

def test_fetch():
    cpu = get_cpu()
    address = 0x3FFF
    value = 0x12
    # in rom
    cpu.pc.set(address)
    cpu.rom[address] = value
    startCycles = cpu.cycles
    assert cpu.fetch() == value
    assert startCycles-cpu.cycles == 1
    # in the memory
    value = 0x13
    address = 0xC000
    cpu.pc.set(address)
    cpu.memory.write(address, value)
    assert cpu.fetch() == value
    
    
def test_read_write():
    cpu = get_cpu()
    address = 0xC000
    value = 0x12
    startCycles = cpu.cycles
    cpu.write(address, value)
    assert startCycles-cpu.cycles == 2
    startCycles = cpu.cycles
    assert cpu.read(address) == value
    assert startCycles-cpu.cycles == 1
    
    address +=1
    value += 1
    cpu.write(address, value)
    assert cpu.read(address) == value
    

def test_relativeConditionalJump():
    cpu = get_cpu()
    pc = cpu.pc.get()
    value = 0x12
    cpu.rom[constants.RESET_PC] = value
    # test jr_nn
    startCycles = cpu.cycles
    cpu.relativeConditionalJump(True)
    assert startCycles-cpu.cycles == 3
    assert_registers(cpu, pc=pc+value+1)
    # test pc.inc
    startCycles = cpu.cycles
    pc = cpu.pc.get()
    cpu.relativeConditionalJump(False)
    assert startCycles-cpu.cycles == 2
    assert cpu.pc.get() == pc+1
    
    
def test_flags():
    cpu = get_cpu()
    cpu.f.set(constants.Z_FLAG)
    assert cpu.isZ() == True
    assert cpu.isNZ() == False
    cpu.f.set(~constants.Z_FLAG)
    assert cpu.isZ() == False
    assert cpu.isNZ() == True
    
    cpu.f.set(constants.C_FLAG)
    assert cpu.isC() == True
    assert cpu.isNC() == False
    cpu.f.set(~constants.C_FLAG)
    assert cpu.isC() == False
    assert cpu.isNC() == True
 
def test_flags_memory_access(): 
    cpu = get_cpu()
    cpu.f.set(constants.Z_FLAG)
    assert cpu.isZ() == True
    prepare_for_fetch(cpu, 0x1234, 0x1234)
    cpu.memory.write(0x1234, 0x12)
    assert cpu.isZ() == True
    cpu.rom[0x1234] = 0x12
    assert cpu.isZ() == True
   

def fetch_execute_cycle_test(cpu, opCode, cycles=0):
    prepare_for_fetch(cpu, opCode)
    cycle_test(cpu, 0xCB, cycles)
    
def cycle_test(cpu, opCode, cycles=0):
    startCycles = cpu.cycles
    try:
        cpu.execute(opCode)
    except Exception, inst:
        assert False, "Opcode %s %s failed to execute: %s" % (hex(opCode), OP_CODES[opCode], inst)
    cpuUsedCycles = startCycles-cpu.cycles 
    assert cpuUsedCycles == cycles,\
        "Cycles for opCode %s [CPU.%s] should be %i not %i" %\
         (hex(opCode).ljust(2),\
          OP_CODES[opCode],\
          cycles, cpuUsedCycles)
      
      
# TEST HELPERS ---------------------------------------

def test_create_group_op_codes():
    assert len(GROUPED_REGISTERS) == 8
    start=0x12
    step=0x03
    func = CPU.inc
    table = [(start, step, func)]
    grouped = create_group_op_codes(table)
    assert len(grouped) == len(table)*8
    
    opCode = start
    for entry in grouped:
        assert len(entry) == 2
        assert entry[0] == opCode
        assert entry[1].func_name == "<lambda>"
        assert entry[1].func_closure[0].cell_contents == func
        opCode += step
        
        
def test_create_register_op_codes():
    start = 0x09
    step = 0x10
    func = CPU.addHL
    registers = [CPU.getBC]*128
    table = [(start, step, func, registers)]
    list = create_register_op_codes(table)
    opCode = start
    assert len(list) == len(registers)
    for entry in list:
        assert len(entry) == 2
        assert entry[0] == opCode
        assert entry[1].func_name == "<lambda>"
        assert entry[1].func_closure[0].cell_contents == func
        opCode += step
 # HELPERS
 
def assert_default_registers(cpu, a=constants.RESET_A, bc=constants.RESET_BC,\
                             de=constants.RESET_DE, f=constants.RESET_F,\
                             hl=constants.RESET_HL, sp=constants.RESET_SP,\
                             pc=constants.RESET_PC):
    return assert_registers(cpu, a, bc, de, f, hl, sp, pc)

def assert_registers(cpu, a=None, bc=None, de=None, f=None, hl=None, sp=None, pc=None):
    if a is not None:
        assert cpu.a.get() == a, "Register a  is %s but should be %s" % (hex(cpu.a.get()), hex(a))
    if bc is not None:
        assert cpu.bc.get() == bc, "Register bc  is %s but should be %s" % (hex(cpu.bc.get()), hex(bc))
    if de is not None:
        assert cpu.de.get() == de, "Register de is %s but should be %s" % (hex(cpu.de.get()),hex(de))
    if f is not None:
        assert cpu.f.get() == f, "Register f is %s but should be %s" % (hex(cpu.f.get()),hex(f))
    if hl is not None:
        assert cpu.hl.get() == hl, "Register hl is %s but should be %s" % (hex(cpu.hl.get()), hex(hl))
    if sp is not None:
        assert cpu.sp.get() == sp, "Register sp is %s but should be %s" % (hex(cpu.sp.get()), hex(sp))
    if pc is not None:
        assert cpu.pc.get() == pc, "Register pc is %s but should be %s" % (hex(cpu.pc.get()), hex(pc))
        
def prepare_for_fetch(cpu, value, valueLo=None):
    pc = cpu.pc.get()
    if valueLo is not None:
        cpu.rom[pc] = valueLo & 0xFF
        cpu.memory.write(pc, valueLo & 0xFF)
        pc += 1
    cpu.rom[pc] = value & 0xFF
    cpu.memory.write(pc, value & 0xFF)
        
def prepare_for_pop(cpu, value, valueLo=None):
    sp = cpu.sp.get()
    if valueLo is not None:
        cpu.memory.write(sp, valueLo & 0xFF)
        sp += 1
    cpu.memory.write(sp, value & 0xFF)
        
def set_registers(registers, value):
    #if registers is not list:
      #  registers = [registers]
    for register in registers:
        register.set(value);
        
        
# test helper methods ---------------------------------------------------------

def test_prepare_for_pop():
    cpu = get_cpu()
    value = 0x12
    prepare_for_pop(cpu, value, value+1)
    assert cpu.pop() == value+1
    assert cpu.pop() == value
    
def test_prepare_for_fetch():
    cpu = get_cpu()
    value = 0x12
    prepare_for_fetch(cpu, value, value+1)
    assert cpu.fetch() == value+1
    assert cpu.fetch() == value
    
# ------------------------------------------------------------
# opCode Testing

#nop
def test_0x00():
    cpu = get_cpu()
    cycle_test(cpu, 0x00, 1)
    assert_default_registers(cpu)

#load_mem_SP
def test_0x08():
    cpu = get_cpu()
    assert_default_registers(cpu)
    startPC = cpu.pc.get()
    prepare_for_fetch(cpu, 0xCD, 0xEF)
    cpu.sp.set(0x1234)
    cycle_test(cpu, 0x08, 5)
    assert_default_registers(cpu, pc=startPC+2, sp=0x1234)
    assert cpu.memory.read(0xCDEF) == cpu.sp.getLo()
    assert cpu.memory.read(0xCDEF+1) == cpu.sp.getHi()
    
# stop
def test_0x10():
    cpu = get_cpu()
    pc = cpu.pc.get()
    cycle_test(cpu, 0x10, 0)
    # fetches 1 cycle
    assert_default_registers(cpu, pc=pc+1)
    
# jr_nn
def test_0x18():
    cpu = get_cpu();
    pc = cpu.pc.get()
    value = 0x12
    cpu.rom[constants.RESET_PC] = value
    assert_default_registers(cpu)
    cycle_test(cpu, 0x18, 3)
    assert_default_registers(cpu, pc=pc+value+1)
    
# jr_NZ_nn see test_jr_cc_nn
def test_0x20_0x28_0x30():
    cpu = get_cpu()
    flags  = [~constants.Z_FLAG, constants.Z_FLAG, ~constants.C_FLAG, constants.C_FLAG]
    opCode = 0x20
    value = 0x12
    for i in range(0, 4):
        prepare_for_fetch(cpu, value)
        pc = cpu.pc.get()
        cpu.f.set(flags[i])
        cycle_test(cpu, opCode, 3)
        assert cpu.pc.get() == pc+value+1
        
        pc = cpu.pc.get()
        cpu.f.set(~flags[i])
        cycle_test(cpu, opCode, 2)
        assert cpu.pc.get() == pc+1
        value += 3
        opCode += 0x08
        
# ld_BC_nnnn to ld_SP_nnnn
def test_0x01_0x11_0x21_0x31():
    cpu = get_cpu()
    registers= [cpu.bc, cpu.de, cpu.hl, cpu.sp]
    value = 0x12
    opCode = 0x01
    for index in range(0, len(registers)):
        prepare_for_fetch(cpu, value, value+1)
        cycle_test(cpu, opCode, 3)
        assert registers[index].getLo() == value+1
        assert registers[index].getHi() == value
        value += 3
        opCode += 0x10
        
# add_HL_BC to add_HL_SP
def test_0x09_0x19_0x29_0x39():
    cpu = get_cpu()
    registers= [cpu.bc, cpu.de, cpu.hl, cpu.sp]
    value = 0x1234
    opCode = 0x09
    for i in range(0, len(registers)):
        cpu.hl.set(value)
        registers[i].set(value)
        assert  registers[i].get() == value
        cycle_test(cpu, opCode, 2)
        assert cpu.hl.get() == value+value
        value += 3
        opCode += 0x10
        
# ld_BCi_A
def test_0x02():
    cpu = get_cpu();
    cpu.bc.set(0xC2, 0x23);
    cpu.a.set(0x12);
    cycle_test(cpu, 0x02, 2);
    assert cpu.read(cpu.bc.get()) == cpu.a.get()
    
# ld_A_BCi
def test_0x0A():
    cpu = get_cpu()
    value = 0x12
    address = 0xC020
    cpu.bc.set(address)
    cpu.write(address, value)
    assert cpu.read(address) == value
    cycle_test(cpu, 0x0A, 2)
    assert_default_registers(cpu, a=value, bc=address)
    
        
# ld_DEi_A
def test_0x12():
    cpu = get_cpu();
    cpu.de.set(0xC2, 0x23);
    cpu.a.set(0x12);
    cycle_test(cpu, 0x12, 2);
    assert cpu.read(cpu.de.get()) == cpu.a.get()

# load_a_DEi
def test_0x1A():
    cpu = get_cpu()
    value = 0x12
    address = 0xC020
    cpu.de.set(address)
    cpu.write(address, value)
    assert cpu.read(address) == value
    cycle_test(cpu, 0x1A, 2)
    assert_default_registers(cpu, a=value, de=address)

# ldi_HLi_A
def test_0x22():
    cpu = get_cpu();
    cpu.hl.set(0xCD, 0xEF);
    cpu.a.set(0x12);
    cycle_test(cpu, 0x22, 2);
    assert cpu.read(0xCDEF) == cpu.a.get()
    assert cpu.hl.get() == 0xCDEF+1

# ldd_HLi_A
def test_0x32():
    cpu = get_cpu();
    cpu.hl.set(0xCD, 0xEF);
    cpu.a.set(0x12);
    cycle_test(cpu, 0x32, 2);
    assert cpu.read(0xCDEF) == cpu.a.get()
    assert cpu.hl.get() == 0xCDEF-1
    
    
# ldi_A_HLi
def test_0x2A():
    cpu = get_cpu()
    value = 0x12
    address = 0xCDEF
    cpu.hl.set(address)
    cpu.write(address, value)
    assert cpu.read(address) == value
    cycle_test(cpu, 0x2A, 2)
    assert_default_registers(cpu, a=value, hl=address+1)

# ldd_A_HLi
def test_0x3A():
    cpu = get_cpu()
    value = 0x12
    address = 0xCDEF
    cpu.hl.set(address)
    cpu.write(address, value)
    assert cpu.read(address) == value
    cycle_test(cpu, 0x3A, 2)
    assert_default_registers(cpu, a=value, hl=address-1)
    
# inc_BC DE HL SP
def test_0x03_to_0x33_inc_double_registers():
    cpu = get_cpu()
    opCode = 0x03
    registers = [cpu.bc, cpu.de, cpu.hl, cpu.sp]
    value = 0x12
    for i in range(0,4):
        set_registers(registers, 0)
        registers[i].set(value)
        cycle_test(cpu, opCode, 2);
        assert  registers[i].get() == value +1
        cpu.reset()
        opCode += 0x10
        value += 3
 
# dec_BC
def test_0x0B_to_0c38_dec_double_registers():
    cpu = get_cpu()
    opCode = 0x0B
    registers = [cpu.bc, cpu.de, cpu.hl, cpu.sp]
    value = 0x12
    for i in range(0,4):
        set_registers(registers, 0)
        registers[i].set(value)
        cycle_test(cpu, opCode, 2);
        assert  registers[i].get() == value-1
        cpu.reset()
        cpu.reset()
        opCode += 0x10
        value += 3

# inc_B C D E H L  A
def test_0x04_to_0x3C_inc_registers():
    cpu = get_cpu()
    registers = [cpu.b, cpu.c, cpu.d, cpu.e, cpu.h, cpu.l, cpu.hli, cpu.a]
    opCode = 0x04
    value = 0x12
    for register in registers:
        if register == cpu.hli:
            opCode += 0x08
            continue
        set_registers(registers, 0)
        register.set(value)
        cycle_test(cpu, opCode, 1)
        assert register.get() == value+1
        cpu.reset()
        opCode += 0x08
        value += 3
        
# inc_HLi
def test_0x34():
    cpu = get_cpu()
    value = 0x12
    cpu.hl.set(0xCDEF)
    cpu.write(cpu.hl.get(), value)
    assert cpu.read(cpu.hl.get()) == value
    cycle_test(cpu, 0x34, 3)
    assert cpu.read(cpu.hl.get()) == value +1

# dec_B C D E H L  A
def test_0x05_to_0x3D_dec_registers():
    cpu = get_cpu()
    registers = [cpu.b, cpu.c, cpu.d, cpu.e, cpu.h, cpu.l, cpu.hli, cpu.a]
    opCode = 0x05
    value = 0x12
    for register in registers:
        if register ==  cpu.hli:
            opCode += 0x08
            continue
        cpu.reset()
        set_registers(registers, 0)
        register.set(value)
        cycle_test(cpu, opCode, 1)
        assert register.get() == value-1
        opCode += 0x08
        value += 3

# dec_HLi
def test_0x35():
    cpu = get_cpu()
    value = 0x12
    cpu.hl.set(0xCDEF)
    cpu.write(cpu.hl.get(), value)
    assert cpu.read(cpu.hl.get()) == value
    cycle_test(cpu, 0x35, 3)
    assert cpu.read(cpu.hl.get()) == value -1
    
# ld_B_nn C D E H L A )
def test_0x06_to_0x3A():
    cpu = get_cpu()
    registers = [cpu.b, cpu.c, cpu.d, cpu.e, cpu.h, cpu.l, cpu.hli, cpu.a]
    opCode = 0x06
    value = 0x12
    for i in range(0, len(registers)):
        if registers[i] ==  cpu.hli:
            opCode += 0x08
            continue
        oldPC = cpu.pc.get()
        set_registers(registers, 0)
        prepare_for_fetch(cpu, value)
        cycle_test(cpu, opCode, 2)
        assert registers[i].get() == value
        assert cpu.pc.get() - oldPC == 1
        cpu.reset()
        opCode += 0x08
        value += 3
        
# ld_HLi_nn
def test_0x36():
    cpu = get_cpu()
    value = 0x12
    address = 0xCDEF
    prepare_for_fetch(cpu, value)
    cpu.hl.set(address)
    oldPC = cpu.pc.get()
    cycle_test(cpu, 0x36, 3)
    assert cpu.read(cpu.hl.get()) == value 
    assert cpu.pc.get() - oldPC == 1
    
# rlca
def test_0x07():
    cpu = get_cpu()
    cycle_test(cpu, 0x07, 1)
    
# rrca
def test_0x0F():
    cpu = get_cpu()
    cycle_test(cpu, 0x0F, 1)

# rla
def test_0x17():
    cpu = get_cpu()
    cycle_test(cpu, 0x17, 1)

# rra
def test_0x1F():
    cpu = get_cpu()
    cycle_test(cpu, 0x1F, 1)

# daa
def test_0x27():
    cpu = get_cpu()
    cycle_test(cpu, 0x27, 1)

# cpl
def test_0x2F():
    cpu = get_cpu()
    value = 0x12
    cpu.a.set(value)
    cpu.f.set(value)
    cycle_test(cpu, 0x2F, 1)
    assert_default_registers(cpu, a=value^0xFF, f=value|constants.N_FLAG+constants.H_FLAG)

# scf
def test_0x37():
    cpu = get_cpu()
    value = 0x12
    cpu.f.set(value)
    cycle_test(cpu, 0x37, 0)
    assert_default_registers(cpu, f=(value & constants.Z_FLAG)|constants.C_FLAG)

# ccf
def test_0x3F():
    cpu = get_cpu()
    value = 0x12
    cpu.f.set(value)
    cycle_test(cpu, 0x3F, 0)
    assert_default_registers(cpu, f=(value & (constants.Z_FLAG|constants.C_FLAG))^constants.C_FLAG)

# halt
def test_0x76():
    py.test.skip("test not completed yet")
    cpu = get_cpu()
    assert cpu.halted == False
    cycle_test(cpu, 0x76, 0)
    assert cpu.halted == True


# ld_B_B to ld_A_A
def test_load_registers():
    cpu = get_cpu()
    opCode = 0x40
    value = 0x12
    registers = [cpu.b, cpu.c, cpu.d, cpu.e, cpu.h, cpu.l, cpu.hli, cpu.a]
    for store in registers:
         for load in registers:
             if store == cpu.hli and load == cpu.hli:
                 opCode += 0x01
                 continue
             cpu.reset()
             set_registers(registers, 0)
             load.set(value)
             numCycles= 1
             if store == cpu.hli or load == cpu.hli:
                numCycles = 2
             cycle_test(cpu, opCode, numCycles)
             assert store.get() == value
             opCode += 0x01


# add_A_B to add_A_A
def test_0x80_to_0x87():
    cpu = get_cpu()
    opCode = 0x80
    valueA = 0x11
    value = 0x12
    registers = [cpu.b, cpu.c, cpu.d, cpu.e, cpu.h, cpu.l, cpu.hli, cpu.a]
    for register in registers:
        cpu.reset()
        cpu.a.set(valueA)
        register.set(value)
        numCycles= 1
        if register == cpu.hli:
            numCycles = 2
        cycle_test(cpu, opCode, numCycles)
        if register == cpu.a:
            assert cpu.a.get() == 2*value
        else:
            assert cpu.a.get() == valueA+value
        value += 3
        opCode += 0x01

# adc_A_B to adx_A_A
def test_0x88_to_0x8F():
    py.test.skip("need a full flag checker imlementation")
    cpu = get_cpu()
    opCode = 0x88
    value = 0x12
    registers = [cpu.b, cpu.c, cpu.d, cpu.e, cpu.h, cpu.l, cpu.hli, cpu.a]
    for register in registers:
        cpu.reset()
        cpu.a.set(value)
        register.set(value)
        numCycles= 1
        if add == cpu.hli:
            numCycles = 2
        cycle_test(cpu, opCode, numCycles)
        assert cpu.a.get() == 2*value
        value += 3
        opCode += 0x01

# sub_A_B to sub_A_A
def test_0x90_to_0x98():
    cpu = get_cpu()
    opCode = 0x90
    value = 0x12
    registers = [cpu.b, cpu.c, cpu.d, cpu.e, cpu.h, cpu.l, cpu.hli, cpu.a]
    for register in registers:
        cpu.reset()
        cpu.a.set(value)
        register.set(value)
        numCycles= 1
        if register == cpu.hli:
            numCycles = 2
        cycle_test(cpu, opCode, numCycles)
        assert cpu.a.get() == 0
        value += 3
        opCode += 0x01

# sbc_A_B to sbc_A_A
def test_0x98():
    pass

# and_A_B to and_A_A
def test_0xA0_to_0xA7():
    cpu = get_cpu()
    opCode = 0xA0
    value = 0x12
    valueA = 0x11
    registers = [cpu.b, cpu.c, cpu.d, cpu.e, cpu.h, cpu.l, cpu.hli, cpu.a]
    for register in registers:
        cpu.reset()
        cpu.a.set(valueA)
        register.set(value)
        numCycles= 1
        if register == cpu.hli:
            numCycles = 2
        cycle_test(cpu, opCode, numCycles)
        if register == cpu.a:
            assert cpu.a.get() == (value & value)
        else:
            assert cpu.a.get() == (valueA & value)
        if cpu.a.get() == 0:
            assert cpu.f.get() == constants.Z_FLAG
        else:
            assert cpu.f.get() == 0
        value += 1
        opCode += 0x01

# xor_A_B to xor_A_A
def test_0xA8_to_0xAF():
    cpu = get_cpu()
    opCode = 0xA8
    value = 0x12
    valueA = 0x11
    registers = [cpu.b, cpu.c, cpu.d, cpu.e, cpu.h, cpu.l, cpu.hli, cpu.a]
    for register in registers:
        cpu.reset()
        cpu.a.set(valueA)
        register.set(value)
        numCycles= 1
        if register == cpu.hli:
            numCycles = 2
        cycle_test(cpu, opCode, numCycles)
        if register == cpu.a:
            assert cpu.a.get() == (value ^ value)
        else:
            assert cpu.a.get() == (valueA ^ value)
        if cpu.a.get() == 0:
            assert cpu.f.get() == constants.Z_FLAG
        else:
            assert cpu.f.get() == 0
        value += 1
        opCode += 0x01

# or_A_B to or_A_A
def test_0xB0_to_0xB7():
    cpu = get_cpu()
    opCode = 0xB0
    value = 0x12
    valueA = 0x11
    registers = [cpu.b, cpu.c, cpu.d, cpu.e, cpu.h, cpu.l, cpu.hli, cpu.a]
    for register in registers:
        cpu.reset()
        cpu.a.set(valueA)
        register.set(value)
        numCycles= 1
        if register == cpu.hli:
            numCycles = 2
        cycle_test(cpu, opCode, numCycles)
        if register == cpu.a:
            assert cpu.a.get() == (value | value)
        else:
            assert cpu.a.get() == (valueA | value)
        if cpu.a.get() == 0:
            assert cpu.f.get() == constants.Z_FLAG
        else:
            assert cpu.f.get() == 0
        value += 1
        opCode += 0x01

# cp_A_B to cp_A_A
def test_0xB8_to_0xBF():
    cpu = get_cpu()
    opCode = 0xB8
    value = 0x12
    valueA = 0x11
    registers = [cpu.b, cpu.c, cpu.d, cpu.e, cpu.h, cpu.l, cpu.hli, cpu.a]
    for register in registers:
        cpu.reset()
        cpu.a.set(valueA)
        register.set(value)
        numCycles= 1
        if register == cpu.hli:
            numCycles = 2
        cycle_test(cpu, opCode, numCycles)
        if register == cpu.a:
            valueA = value
        assert cpu.f.get() & constants.N_FLAG != 0
        if valueA == value:
            assert cpu.f.get() & constants.Z_FLAG != 0
        if value < 0:
            assert cpu.f.get() & constants.C_FLAG != 0
        if ((valueA-value) & 0x0F) > (valueA & 0x0F):
            assert cpu.f.get() & constants.H_FLAG != 0
        value += 1
        opCode += 0x01

# ret_NZ to ret_C
def test_0xC0():
    cpu = get_cpu()
    flags  = [~constants.Z_FLAG, constants.Z_FLAG, ~constants.C_FLAG, constants.C_FLAG]
    opCode = 0xC0
    value = 0x1234
    for i in range(0, 4):
        cpu.reset()
        prepare_for_pop(cpu, value >> 8, value & 0xFF)
        cpu.f.set(flags[i])
        cycle_test(cpu, opCode, 5)
        assert cpu.pc.get() == value
        
        cpu.reset()
        prepare_for_pop(cpu, value >> 8, value & 0xFF)
        cpu.f.set(~flags[i])
        cycle_test(cpu, opCode, 2)
        assert_default_registers(cpu, f=~flags[i] & 0xFF)
        value += 3
        opCode += 0x08

# ldh_mem_A
def test_0xE0():
    cpu = get_cpu()
    valueA = 0x11
    value = 0x12
    prepare_for_fetch(cpu, value)
    cpu.a.set(valueA)
    cycle_test(cpu, 0xE0, 3)
    assert cpu.read(0xFF00+value) == valueA
    

# add_SP_nn
def test_0xE8():
    cpu = get_cpu()
    value = 0x12
    spValue = 0xCDEF
    prepare_for_fetch(cpu, value)
    cpu.sp.set(spValue)
    cycle_test(cpu, 0xE8, 4)
    assert cpu.sp.get() == spValue+value

# ldh_A_mem
def test_0xF0():
    cpu = get_cpu()
    valueA = 0x11
    value= 0x12
    address = 0x13
    cpu.a.set(valueA)
    prepare_for_fetch(cpu, address)
    cpu.write(0xFF00+address, value)
    cycle_test(cpu, 0xF0, 3)
    assert cpu.a.get() == value

# ld_A_mem
def test_0xFA():
    cpu = get_cpu()
    value = 0x11
    valueA = 0x12
    cpu.a.set(valueA)
    pc = cpu.pc.get();
    prepare_for_fetch(cpu, 0x12, 0x34)
    cpu.write(0x1234, value)
    cycle_test(cpu, 0xFA, 4)
    assert_default_registers(cpu, a=value, pc=pc+2)

# ld_mem_A
def test_0xEA():
    cpu = get_cpu()
    valueA = 0x56
    prepare_for_fetch(cpu, 0x12, 0x34)
    cpu.a.set(valueA)
    cycle_test(cpu, 0xEA, 4)
    assert cpu.read(0x1234) == valueA
    
    
# ld_HL_SP_nn
def test_0xF8():
    cpu = get_cpu()
    value = 0x12
    valueSp = 0x1234
    prepare_for_fetch(cpu, value)
    cpu.sp.set(valueSp)
    pc = cpu.pc.get()
    cycle_test(cpu, 0xF8, 3)
    f = cpu.f.get();
    assert_default_registers(cpu, hl=valueSp+value, f=f, sp=valueSp, pc=pc+1)

# pop_BC to pop_AF
def test_0xC1_to_0xF1():
    cpu = get_cpu()
    registers = [cpu.bc, cpu.de, cpu.hl, cpu.af]
    opCode = 0xC1
    value = 0x1234
    for register in registers:
        cpu.reset()
        prepare_for_pop(cpu, value >> 8, value & 0xFF)
        cycle_test(cpu, opCode, 3)
        assert register.get() == value
        value += 3
        opCode += 0x10

# ret
def test_0xC9():
    cpu = get_cpu()
    value = 0x1234
    valueSp = 0x5678
    cpu.sp.set(valueSp)
    prepare_for_pop(cpu, value >> 8, value & 0xFF)
    cycle_test(cpu, 0xC9, 4)
    assert_default_registers(cpu, pc=value, sp=valueSp+2)
    

# reti
def test_0xD9():
    py.test.skip("deeper knowledge necessary")
    cpu = get_cpu()
    value = 0x1234
    prepare_for_pop(cpu, value >> 8, value & 0xFF)
    prepare_for_fetch(cpu, 0x00)
    pc = cpu.pc.get()
    cycle_test(cpu, 0xD9, 4+1)
    assert_default_registers(cpu, pc=pc+value)

# ld_PC_HL
def test_0xE9():
    cpu = get_cpu()
    value = 0x1234
    cpu.hl.set(value)
    cycle_test(cpu, 0xE9, 1)
    assert_default_registers(cpu, pc=value, hl=value)

# ld_SP_HL
def test_0xF9():
    cpu = get_cpu()
    value = 0x1234
    cpu.hl.set(value)
    cycle_test(cpu, 0xF9, 2)
    assert_default_registers(cpu, sp=value, hl=value)

# jp_NZ_nnnn to jp_C_nnnn
def test_0xC2_to_0xDA():
    cpu = get_cpu()
    flags  = [~constants.Z_FLAG, constants.Z_FLAG, ~constants.C_FLAG, constants.C_FLAG]
    opCode = 0xC2
    value = 0x1234
    for i in range(0, 4):
        cpu.reset()
        prepare_for_fetch(cpu, value >> 8, value & 0xFF)
        pc = cpu.pc.get()
        cpu.f.set(flags[i])
        cycle_test(cpu, opCode, 4)
        assert_default_registers(cpu, f=flags[i] & 0xFF, pc=value)
        
        cpu.reset()
        prepare_for_fetch(cpu, value >> 8, value & 0xFF)
        cpu.f.set(~flags[i])
        pc = cpu.pc.get()
        cycle_test(cpu, opCode, 3)
        assert_default_registers(cpu, f=~flags[i] & 0xFF, pc=pc+2)
        value += 3
        opCode += 0x08
        

# ldh_Ci_A
def test_0xE2():
    cpu = get_cpu()
    value = 0x12
    valueA = value+1
    cpu.c.set(value)
    cpu.a.set(valueA)
    cycle_test(cpu, 0xE2, 2)
    assert cpu.read(0xFF00+value) == valueA

# ldh_A_Ci
def test_0xF2():
    cpu = get_cpu()
    valueC = 0x12
    valueA = 0x11
    cpu.c.set(valueC)
    cpu.b.set(0);
    cpu.write(0xFF00+valueC, valueA)
    cycle_test(cpu, 0xF2, 2)
    assert_default_registers(cpu, a=valueA, bc=valueC)




# jp_nnnn
def test_0xC3():
    cpu = get_cpu()
    prepare_for_fetch(cpu, 0x12, 0x34)
    cycle_test(cpu, 0xC3, 4)
    assert_default_registers(cpu, pc=0x1234)


# di
def test_0xF3():
    cpu = get_cpu()
    cpu.ime == True
    cycle_test(cpu, 0xF3, 1)
    assert cpu.ime == False

# ei
def test_0xFB():
    py.test.skip("interupt error")
    cpu = get_cpu()
    cpu.ime = False
    prepare_for_fetch(cpu, 0x00)
    cycle_test(cpu, 0xFB, 1+1)
    assert cpu.ime == True

# call_NZ_nnnn
def test_0xC4():
    pass
# call_Z_nnnn
def test_0xCC():
    pass
# call_NC_nnnn
def test_0xD4():
    pass
# call_C_nnnn
def test_0xDC():
    pass

# push_BC to push_AF
def test_0xC5_to_0xF5():
    cpu = get_cpu()
    registers  = [cpu.bc, cpu.de, cpu.hl, cpu.af]
    opCode = 0xC5
    value = 0x1234
    for register in registers:
        register.set(value)
        cycle_test(cpu, opCode, 4)
        assert cpu.memory.read(cpu.sp.get()+1) == value >> 8
        assert cpu.memory.read(cpu.sp.get()) == value & 0xFF
        opCode += 0x10
        value += 0x0101
            

# call_nnnn
def test_0xCD():
    pass

# add_A_nn
def test_0xC6():
    pass

# adc_A_nn
def test_0xCE():
    pass

# sub_A_nn
def test_0xD6():
    pass

# sbc_A_nn
def test_0xDE():
    pass

# and_A_nn
def test_0xE6():
    pass

# xor_A_nn
def test_0xEE():
    pass

# or_A_nn
def test_0xF6():
    pass

# cp_A_nn
def test_0xFE():
    pass

# rst(0x00) to rst(0x38)
def test_0xC7_to_0xFF():
    cpu = get_cpu()
    opCode = 0xC7
    rstValue = 0x00
    for i in range(0,8):
        cpu.reset()
        cpu.pc.set(0x1234)
        cycle_test(cpu, opCode, 4)
        assert cpu.pop() == 0x34
        assert cpu.pop() == 0x12
        assert cpu.pc.get() == rstValue
        opCode += 0x08
        rstValue += 0x08
    pass

# switching to other opcode set
def test_0xCB():
    pass

# rlc_B to rlc_A
def test_0x00_to_0x07():
    py.test.skip("Bug in cpu")
    cpu = get_cpu()
    registers = [cpu.b, cpu.c, cpu.d, cpu.e, cpu.h, cpu.l, cpu.hli, cpu.a]
    opCode = 0x00
    value = 0x12
    for register in registers:
        cpu.reset()
        register.set(value)
        cycles = 2
        if register == cpu.hli:
            cycles = 4
        fetch_execute_cycle_test(cpu, opCode, cycles)
        rlc = ((value & 0x7F) << 1) + ((value & 0x80) >> 7)
        assert register.get() ==  rcl
        opCode += 0x01
        vaue += 1

# rrc_B to rrc_F
def test_0x08_to_0x0F():
    cpu = get_cpu()
    opCode = 0x38

# rl_B to rl_A
def test_0x10_to_0x17():
    cpu = get_cpu()
    opCode = 0x38

# rr_B to rr_A
def test_0x18_to_0x1F():
    cpu = get_cpu()
    opCode = 0x38

# sla_B to sla_A
def test_0x20_to_0x27():
    cpu = get_cpu()
    opCode = 0x38

# sra_B to sra_A
def test_0x28_to_0x2F():
    cpu = get_cpu()
    opCode = 0x38

# swap_B to swap_A
def test_0x30_to_0x37():
    cpu = get_cpu()
    opCode = 0x38

# srl_B to srl_A
def test_0x38_to_0x3F():
    cpu = get_cpu()
    opCode = 0x38

# bit_B to bit_A
def test_bit_opCodes():
    opCode = 0x40
    
# set_B to set_C
def test_set_opCodes():
    opCode = 0xC0

# res_B to res_A
def test_res_opCodes():
    opCode = 0x80
    




    