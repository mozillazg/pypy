import py
from pypy.lang.gameboy.cpu import *
from pypy.lang.gameboy.ram import *
from pypy.lang.gameboy import *

def get_cpu():
    cpu =  CPU(None, RAM())
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
    
    
# ------------------------------------------------------------
# TEST CPU

def test_getters():
    assert_default_registers(get_cpu())
    

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
    

def test_jr_cc_nn():
    cpu = get_cpu()
    pc = cpu.pc.get()
    value = 0x12
    cpu.rom[constants.RESET_PC] = value
    # test jr_nn
    startCycles = cpu.cycles
    cpu.jr_cc_nn((lambda :True))
    assert startCycles-cpu.cycles == 3
    assert_registers(cpu, pc=pc+value+1)
    # test pc.inc
    startCycles = cpu.cycles
    pc = cpu.pc.get()
    cpu.jr_cc_nn((lambda: False))
    assert startCycles-cpu.cycles == 2
    assert cpu.pc.get() == pc+1
    
    
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
          OP_CODES[opCode].func_closure[0].cell_contents.func_name,\
          cycles, cpuUsedCycles)
      
      
# TEST HELPERS ---------------------------------------

def test_create_group_op_codes():
    py.test.skip()
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
    py.test.skip()
    start = 0x09
    step = 0x10
    func = CPU.addHL
    registers = [CPU.bc]*128
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
        assert cpu.bc.get() == bc, "Register bc  is %s but should be %s" % (hex(cpu.bc.get(), hex(bc)))
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
    cpu.rom[cpu.pc.get()] = value & 0xFF
    if valueLo is not None:
        cpu.rom[cpu.pc.get()+1] = value & 0xFF
        
def set_registers(registers, value):
    #if registers is not list:
      #  registers = [registers]
    for register in registers:
        register.set(value);
        
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
    cpu.sp.set(0x1234)
    cpu.rom[startPC] = 0xD0
    cpu.rom[startPC+1] = 0xC0
    cycle_test(cpu, 0x08, 5)
    assert_default_registers(cpu, pc=startPC+2)
    assert cpu.memory.read(0xC0D0) == cpu.sp.getLo()
    assert cpu.memory.read(0xC0D0+1) == cpu.sp.getHi()
    
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
    py.test.skip("OpCode Table incomplete")
    cpu = get_cpu()
    flags  = [~constants.Z_FLAG, constants.Z_FLAG, ~constants.C_FLAG, constants.C_FLAG]
    opCode = 0x20
    value = 0x12
    for i in range(0, 4):
        prepare_for_fetch(cpu, value)
        pc = cpu.pc.get()
        cpu.f.set(flags[i])
        cycle_test(cpu, opCode, 3)
        assert cpu.pc.get() == pc+value
        
        pc = cpu.pc.get()
        cpu.f.set(~flags[i])
        cycle_test(cpu, opCode, 2)
        assert cpu.pc.get() == pc+1
        value += 2
        
# ld_BC_nnnn to ld_SP_nnnn
def test_0x01_0x11_0x21_0x31():
    py.test.skip("OpCode Table incomplete")
    cpu = get_cpu()
    registers= [cpu.bc, cpu.de, cpu.hl, cpu.sp]
    value = 0x12
    for index in range(0, 8):
        prepare_for_fetch(cpu, value, value+1)
        cycle_test(cpu, 0x01+index*0x10, 3)
        assert registers[index].getHi() == value
        assert registers[index].getlo() == value+1
        value += 2
        
# add_HL_BC to add_HL_SP
def test_0x09_0x19_0x29_0x39():
    py.test.skip("OpCode Table incomplete")
    cpu = get_cpu()
    registers= [cpu.bc, cpu.de, cpu.hl, cpu.sp]
    value = 0x1234
    for i in range(0, 8):
        cpu.hl.set(0x00)
        registers[i].set(value)
        assert  registers[i].get() == value
        cycle_test(cpu, 0x09+i*0x10, 2)
        assert cpu.hl.get() == value
        value += 1
        
# ld_BCi_A
def test_0x02():
    cpu = get_cpu();
    cpu.bc.set(0xC2, 0x23);
    cpu.a.set(0x12);
    cycle_test(cpu, 0x02, 2);
    assert cpu.read(cpu.bc.get()) == cpu.a.get()
    
# ld_A_BCi
def test_0x0A():
    passs
        
# ld_DEi_A
def test_0x12():
    cpu = get_cpu();
    cpu.de.set(0xC2, 0x23);
    cpu.a.set(0x12);
    cycle_test(cpu, 0x02, 2);
    assert cpu.read(cpu.de.get()) == cpu.a.get()

# load_a_DEi
def test_0x1A():
    pass

# ldi_HLi_A
def test_0x22():
    cpu = get_cpu();
    cpu.hl.set(0xC2, 0x23);
    cpu.a.set(0x12);
    cycle_test(cpu, 0x02, 2);
    assert cpu.read(cpu.hl.get()) == cpu.a.get()+1

# ldi_A_HLi
def test_0x2A():
    pass

# ldd_HLi_A
def test_0x32():
    cpu = get_cpu();
    cpu.hl.set(0xC2, 0x23);
    cpu.a.set(0x12);
    cycle_test(cpu, 0x02, 2);
    assert cpu.read(cpu.hl.get()) == cpu.a.get()-1
    
# ldd_A_HLi
def test_0x3A():
    pass
    
# inc_BC DE HL SP
def test_0x03_to_0x33_inc_double_registers():
    py.test.skip("OpCode Table incomplete")
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
    py.test.skip("OpCode Table incomplete")
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
    py.test.skip("Op Code Mapping not fully implemented")
    cpu = get_cpu()
    registers = [cpu.b, cpu.c, cpu.d, cpu.e, cpu.h, cpu.l, cpu.hl, cpu.a]
    opCode = 0x04
    value = 0x12
    for i in range(0, len(registers)):
        if registers[i] == cpu.hl:
            continue
        set_registers(registers, 0)
        cycle_test(cpu, opCode, 1)
        assert registers[i].get() == value+1
        cpu.reset()
        opCode += 0x08
        value += 3
        
# inc_HLi
def test_0x34():
    cpu = get_cpu()
    value = 0x1234
    cpu.hl.set(0xC003)
    cpu.write(cpu.hl.get(), value)
    cycle_test(cpu, 0x34, 3)
    assert cpu.read(cpu.hl.get()) == value +1

# dec_B C D E H L  A
def test_0x05_to_0x3D_dec_registers():
    py.test.skip("Op Code Mapping not fully implemented")
    cpu = get_cpu()
    registers = [cpu.b, cpu.c, cpu.d, cpu.e, cpu.h, cpu.l, cpu.hl, cpu.a]
    opCode = 0x05
    value = 0x12
    for i in range(0, len(registers)):
        if registers[i] ==  cpu.hl:
            continue
        set_registers(registers, 0)
        cycle_test(cpu, opCode, 1)
        assert registers[i].get() == value-1
        cpu.reset()
        opCode += 0x08
        value += 3

# dec_HLi
def test_0x35():
    cpu = get_cpu()
    value = 0x1234
    cpu.hl.set(0xC003)
    cpu.write(cpu.hl.get(), value)
    cycle_test(cpu, 0x35, 3)
    assert cpu.read(cpu.hl.get()) == value -1
    
# ld_B_nn C D E H L A )
def test_0x06_to_0x3A():
    py.test.skip("Op Code Mapping not fully implemented")
    cpu = get_cpu()
    registers = [cpu.b, cpu.c, cpu.d, cpu.e, cpu.h, cpu.l, cpu.hl, cpu.a]
    opCode = 0x06
    value = 0x12
    for i in range(0, len(registers)):
        if registers[i] ==  cpu.hl:
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
    value = 0x1234
    prepare_for_fetch(cpu, value)
    oldPC = cpu.pc.get()
    cycle_test(cpu, 0x36, 3)
    assert cpu.read(cpu.hl.get()) == value 
    assert cpu.pc.get() - oldPC == 1
    
# rlca
def test_0x07():
    pass
    
    
# rrca
def test_0x0F():
    pass

# rla
def test_0x17():
    pass

# rra
def test_0x1F():
    pass

# daa
def test_0x27():
    pass

# cpl
def test_0x2F():
    pass

# scf
def test_0x37():
    pass

# ccf
def test_0x3F():
    pass

# halt
def test_0x76():
    pass

# ld_B_B
def test_0x40():
    pass
# ld_B_C
def test_0x41():
    pass
# ld_B_D
def test_0x42():
    pass
# ld_B_E
def test_0x43():
    pass
# ld_B_H
def test_0x44():
    pass
# ld_B_L
def test_0x45():
    pass
# ld_B_HLi
def test_0x46():
    pass
# ld_B_A
def test_0x47():
    pass
# ld_C_B
def test_0x48():
    pass
# ld_C_C
def test_0x49():
    pass
# ld_C_D
def test_0x4A():
    pass
# ld_C_E
def test_0x4B():
    pass
# ld_C_H
def test_0x4C():
    pass
# ld_C_L
def test_0x4D():
    pass
# ld_C_HLi
def test_0x4E():
    pass
# ld_C_A
def test_0x4F():
    pass
# ld_D_B
def test_0x50():
    pass
# ld_D_C
def test_0x51():
    pass
# ld_D_D
def test_0x52():
    pass
# ld_D_E
def test_0x53():
    pass
# ld_D_H
def test_0x54():
    pass
# ld_D_L
def test_0x55():
    pass
# ld_D_HLi
def test_0x56():
    pass
# ld_D_A
def test_0x57():
    pass
# ld_E_B
def test_0x58():
    pass
# ld_E_C
def test_0x59():
    pass
# ld_E_D
def test_0x5A():
    pass
# ld_E_E
def test_0x5B():
    pass
# ld_E_H
def test_0x5C():
    pass
# ld_E_L
def test_0x5D():
    pass
# ld_E_HLi
def test_0x5E():
    pass
# ld_E_A
def test_0x5F():
    pass
# ld_H_B
def test_0x60():
    pass
# ld_H_C
def test_0x61():
    pass
# ld_H_D
def test_0x62():
    pass
# ld_H_E
def test_0x63():
    pass
# ld_H_H
def test_0x64():
    pass
# ld_H_L
def test_0x65():
    pass
# ld_H_HLi
def test_0x66():
    pass
# ld_H_A
def test_0x67():
    pass
# ld_L_B
def test_0x68():
    pass
# ld_L_C
def test_0x69():
    pass
# ld_L_D
def test_0x6A():
    pass
# ld_L_E
def test_0x6B():
    pass
# ld_L_H
def test_0x6C():
    pass
# ld_L_L
def test_0x6D():
    pass
# ld_L_HLi
def test_0x6E():
    pass
# ld_L_A
def test_0x6F():
    pass
# ld_HLi_B
def test_0x70():
    pass
# ld_HLi_C
def test_0x71():
    pass
# ld_HLi_D
def test_0x72():
    pass
# ld_HLi_E
def test_0x73():
    pass
# ld_HLi_H
def test_0x74():
    pass
# ld_HLi_L
def test_0x75():
    pass
# ld_HLi_A
def test_0x77():
    pass
# ld_A_B
def test_0x78():
    pass
# ld_A_C
def test_0x79():
    pass
# ld_A_D
def test_0x7A():
    pass
# ld_A_E
def test_0x7B():
    pass
# ld_A_H
def test_0x7C():
    pass
# ld_A_L
def test_0x7D():
    pass
# ld_A_HLi
def test_0x7E():
    pass
# ld_A_A
def test_0x7F():
    pass

# add_A_B
def test_0x80():
    pass
# add_A_C
def test_0x81():
    pass
# add_A_D
def test_0x82():
    pass
# add_A_E
def test_0x83():
    pass
# add_A_H
def test_0x84():
    pass
# add_A_L
def test_0x85():
    pass
# add_A_HLi
def test_0x86():
    pass
# add_A_A
def test_0x87():
    pass

# adc_A_B
def test_0x88():
    pass
# adc_A_C
def test_0x89():
    pass
# adc_A_D
def test_0x8A():
    pass
# adc_A_E
def test_0x8B():
    pass
# adc_A_H
def test_0x8C():
    pass
# adc_A_L
def test_0x8D():
    pass
# adc_A_HLi
def test_0x8E():
    pass
# adc_A_A
def test_0x8F():
    pass

# sub_A_B
def test_0x90():
    pass
# sub_A_C
def test_0x91():
    pass
# sub_A_D
def test_0x92():
    pass
# sub_A_E
def test_0x93():
    pass
# sub_A_H
def test_0x94():
    pass
# sub_A_L
def test_0x95():
    pass
# sub_A_HLi
def test_0x96():
    pass
# sub_A_A
def test_0x97():
    pass

# sbc_A_B
def test_0x98():
    pass
# sbc_A_C
def test_0x99():
    pass
# sbc_A_D
def test_0x9A():
    pass
# sbc_A_E
def test_0x9B():
    pass
# sbc_A_H
def test_0x9C():
    pass
# sbc_A_L
def test_0x9D():
    pass
# sbc_A_HLi
def test_0x9E():
    pass
# sbc_A_A
def test_0x9F():
    pass

# and_A_B
def test_0xA0():
    pass
# and_A_C
def test_0xA1():
    pass
# and_A_D
def test_0xA2():
    pass
# and_A_E
def test_0xA3():
    pass
# and_A_H
def test_0xA4():
    pass
# and_A_L
def test_0xA5():
    pass
# and_A_HLi
def test_0xA6():
    pass
# and_A_A
def test_0xA7():
    pass

# xor_A_B
def test_0xA8():
    pass
# xor_A_C
def test_0xA9():
    pass
# xor_A_D
def test_0xAA():
    pass
# xor_A_E
def test_0xAB():
    pass
# xor_A_H
def test_0xAC():
    pass
# xor_A_L
def test_0xAD():
    pass
# xor_A_HLi
def test_0xAE():
    pass
# xor_A_A
def test_0xAF():
    pass

# or_A_B
def test_0xB0():
    pass
# or_A_C
def test_0xB1():
    pass
# or_A_D
def test_0xB2():
    pass
# or_A_E
def test_0xB3():
    pass
# or_A_H
def test_0xB4():
    pass
# or_A_L
def test_0xB5():
    pass
# or_A_HLi
def test_0xB6():
    pass
# or_A_A
def test_0xB7():
    pass

# cp_A_B
def test_0xB8():
    pass
# cp_A_C
def test_0xB9():
    pass
# cp_A_D
def test_0xBA():
    pass
# cp_A_E
def test_0xBB():
    pass
# cp_A_H
def test_0xBC():
    pass
# cp_A_L
def test_0xBD():
    pass
# cp_A_HLi
def test_0xBE():
    pass
# cp_A_A
def test_0xBF():
    pass

# ret_NZ
def test_0xC0():
    pass
# ret_Z
def test_0xC8():
    pass
# ret_NC
def test_0xD0():
    pass
# ret_C
def test_0xD8():
    pass

# ldh_mem_A
def test_0xE0():
    pass

# add_SP_nn
def test_0xE8():
    pass

# ldh_A_mem
def test_0xF0():
    pass

# ld_HL_SP_nn
def test_0xF8():
    pass

# pop_BC
def test_0xC1():
    pass
# pop_DE
def test_0xD1():
    pass
# pop_HL
def test_0xE1():
    pass
# pop_AF
def test_0xF1():
    pass

# ret
def test_0xC9():
    pass

# reti
def test_0xD9():
    pass

# ld_PC_HL
def test_0xE9():
    pass

# ld_SP_HL
def test_0xF9():
    pass

# jp_NZ_nnnn
def test_0xC2():
    pass
# jp_Z_nnnn
def test_0xCA():
    pass
# jp_NC_nnnn
def test_0xD2():
    pass
# jp_C_nnnn
def test_0xDA():
    pass

# ldh_Ci_A
def test_0xE2():
    pass

# ld_mem_A
def test_0xEA():
    pass

# ldh_A_Ci
def test_0xF2():
    pass

# ld_A_mem
def test_0xFA():
    pass

# jp_nnnn
def test_0xC3():
    pass


# di
def test_0xF3():
    pass

# ei
def test_0xFB():
    pass

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

# push_BC
def test_0xC5():
    pass
# push_DE
def test_0xD5():
    pass
# push_HL
def test_0xE5():
    pass
# push_AF
def test_0xF5():
    pass

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

# rst
def test_0xC7():
    pass
# rst
def test_0xCF():
    pass
# rst
def test_0xD7():
    pass
# rst
def test_0xDF():
    pass
# rst
def test_0xE7():
    pass
# rst
def test_0xEF():
    pass
# rst
def test_0xF7():
    pass
# rst
def test_0xFF():
    pass



# switching to other opcode set
def test_0xCB():
    pass


# rlc_B
def test_0x00():
    pass
# rlc_C
def test_0x01():
    pass
# rlc_D
def test_0x02():
    pass
# rlc_E
def test_0x03():
    pass
# rlc_H
def test_0x04():
    pass
# rlc_L
def test_0x05():
    pass
# rlc_HLi
def test_0x06():
    pass
# rlc_A
def test_0x07():
    pass

# rrc_B
def test_0x08():
    pass
# rrc_C
def test_0x09():
    pass
# rrc_D
def test_0x0A():
    pass
# rrc_E
def test_0x0B():
    pass
# rrc_H
def test_0x0C():
    pass
# rrc_L
def test_0x0D():
    pass
# rrc_HLi
def test_0x0E():
    pass
# rrc_A
def test_0x0F():
    pass

# rl_B
def test_0x10():
    pass
# rl_C
def test_0x11():
    pass
# rl_D
def test_0x12():
    pass
# rl_E
def test_0x13():
    pass
# rl_H
def test_0x14():
    pass
# rl_L
def test_0x15():
    pass
# rl_HLi
def test_0x16():
    pass
# rl_A
def test_0x17():
    pass

# rr_B
def test_0x18():
    pass
# rr_C
def test_0x19():
    pass
# rr_D
def test_0x1A():
    pass
# rr_E
def test_0x1B():
    pass
# rr_H
def test_0x1C():
    pass
# rr_L
def test_0x1D():
    pass
# rr_HLi
def test_0x1E():
    pass
# rr_A
def test_0x1F():
    pass

# sla_B
def test_0x20():
    pass
# sla_C
def test_0x21():
    pass
# sla_D
def test_0x22():
    pass
# sla_E
def test_0x23():
    pass
# sla_H
def test_0x24():
    pass
# sla_L
def test_0x25():
    pass
# sla_HLi
def test_0x26():
    pass
# sla_A
def test_0x27():
    pass

# sra_B
def test_0x28():
    pass
# sra_C
def test_0x29():
    pass
# sra_D
def test_0x2A():
    pass
# sra_E
def test_0x2B():
    pass
# sra_H
def test_0x2C():
    pass
# sra_L
def test_0x2D():
    pass
# sra_HLi
def test_0x2E():
    pass
# sra_A
def test_0x2F():
    pass

# swap_B
def test_0x30():
    pass
# swap_C
def test_0x31():
    pass
# swap_D
def test_0x32():
    pass
# swap_E
def test_0x33():
    pass
# swap_H
def test_0x34():
    pass
# swap_L
def test_0x35():
    pass
# swap_HLi
def test_0x36():
    pass
# swap_A
def test_0x37():
    pass

# srl_B
def test_0x38():
    pass
# srl_C
def test_0x39():
    pass
# srl_D
def test_0x3A():
    pass
# srl_E
def test_0x3B():
    pass
# srl_H
def test_0x3C():
    pass
# srl_L
def test_0x3D():
    pass
# srl_HLi
def test_0x3E():
    pass
# srl_A
def test_0x3F():
    pass

# bit_B
def test_0x40():
    pass
# bit_C
def test_0x41():
    pass
# bit_D
def test_0x42():
    pass
# bit_E
def test_0x43():
    pass
# bit_H
def test_0x44():
    pass
# bit_L
def test_0x45():
    pass
# bit_HLi
def test_0x46():
    pass
# bit_A
def test_0x47():
    pass

# bit_B
def test_0x48():
    pass
# bit_C
def test_0x49():
    pass
# bit_D
def test_0x4A():
    pass
# bit_E
def test_0x4B():
    pass
# bit_H
def test_0x4C():
    pass
# bit_L
def test_0x4D():
    pass
# bit_HLi
def test_0x4E():
    pass
# bit_A
def test_0x4F():
    pass

# bit_B
def test_0x50():
    pass
# bit_C
def test_0x51():
    pass
# bit_D
def test_0x52():
    pass
# bit_E
def test_0x53():
    pass
# bit_H
def test_0x54():
    pass
# bit_L
def test_0x55():
    pass
# bit_HLi
def test_0x56():
    pass
# bit_A
def test_0x57():
    pass

# bit_B
def test_0x58():
    pass
# bit_C
def test_0x59():
    pass
# bit_D
def test_0x5A():
    pass
# bit_E
def test_0x5B():
    pass
# bit_H
def test_0x5C():
    pass
# bit_L
def test_0x5D():
    pass
# bit_HLi
def test_0x5E():
    pass
# bit_A
def test_0x5F():
    pass

# bit_B
def test_0x60():
    pass
# bit_C
def test_0x61():
    pass
# bit_D
def test_0x62():
    pass
# bit_E
def test_0x63():
    pass
# bit_H
def test_0x64():
    pass
# bit_L
def test_0x65():
    pass
# bit_HLi
def test_0x66():
    pass
# bit_A
def test_0x67():
    pass

# bit_B
def test_0x68():
    pass
# bit_C
def test_0x69():
    pass
# bit_D
def test_0x6A():
    pass
# bit_E
def test_0x6B():
    pass
# bit_H
def test_0x6C():
    pass
# bit_L
def test_0x6D():
    pass
# bit_HLi
def test_0x6E():
    pass
# bit_A
def test_0x6F():
    pass

# bit_B
def test_0x70():
    pass
# bit_C
def test_0x71():
    pass
# bit_D
def test_0x72():
    pass
# bit_E
def test_0x73():
    pass
# bit_H
def test_0x74():
    pass
# bit_L
def test_0x75():
    pass
# bit_HLi
def test_0x76():
    pass
# bit_A
def test_0x77():
    pass

# bit_B
def test_0x78():
    pass
# bit_C
def test_0x79():
    pass
# bit_D
def test_0x7A():
    pass
# bit_E
def test_0x7B():
    pass
# bit_H
def test_0x7C():
    pass
# bit_L
def test_0x7D():
    pass
# bit_HLi
def test_0x7E():
    pass
# bit_A
def test_0x7F():
    pass

# set_B
def test_0xC0():
    pass
# set_C
def test_0xC1():
    pass
# set_D
def test_0xC2():
    pass
# set_E
def test_0xC3():
    pass
# set_H
def test_0xC4():
    pass
# set_L
def test_0xC5():
    pass
# set_HLi
def test_0xC6():
    pass
# set_A
def test_0xC7():
    pass

# set_B
def test_0xC8():
    pass
# set_C
def test_0xC9():
    pass
# set_D
def test_0xCA():
    pass
# set_E
def test_0xCB():
    pass
# set_H
def test_0xCC():
    pass
# set_L
def test_0xCD():
    pass
# set_HLi
def test_0xCE():
    pass
# set_A
def test_0xCF():
    pass

# set_B
def test_0xD0():
    pass
# set_C
def test_0xD1():
    pass
# set_D
def test_0xD2():
    pass
# set_E
def test_0xD3():
    pass
# set_H
def test_0xD4():
    pass
# set_L
def test_0xD5():
    pass
# set_HLi
def test_0xD6():
    pass
# set_A
def test_0xD7():
    pass

# set_B
def test_0xD8():
    pass
# set_C
def test_0xD9():
    pass
# set_D
def test_0xDA():
    pass
# set_E
def test_0xDB():
    pass
# set_H
def test_0xDC():
    pass
# set_L
def test_0xDD():
    pass
# set_HLi
def test_0xDE():
    pass
# set_A
def test_0xDF():
    pass

# set_B
def test_0xE0():
    pass
# set_C
def test_0xE1():
    pass
# set_D
def test_0xE2():
    pass
# set_E
def test_0xE3():
    pass
# set_H
def test_0xE4():
    pass
# set_L
def test_0xE5():
    pass
# set_HLi
def test_0xE6():
    pass
# set_A
def test_0xE7():
    pass

# set_B
def test_0xE8():
    pass
# set_C
def test_0xE9():
    pass
# set_D
def test_0xEA():
    pass
# set_E
def test_0xEB():
    pass
# set_H
def test_0xEC():
    pass
# set_L
def test_0xED():
    pass
# set_HLi
def test_0xEE():
    pass
# set_A
def test_0xEF():
    pass

# set_B
def test_0xF0():
    pass
# set_C
def test_0xF1():
    pass
# set_D
def test_0xF2():
    pass
# set_E
def test_0xF3():
    pass
# set_H
def test_0xF4():
    pass
# set_L
def test_0xF5():
    pass
# set_HLi
def test_0xF6():
    pass
# set_A
def test_0xF7():
    pass

# set_B
def test_0xF8():
    pass
# set_C
def test_0xF9():
    pass
# set_D
def test_0xFA():
    pass
# set_E
def test_0xFB():
    pass
# set_H
def test_0xFC():
    pass
# set_L
def test_0xFD():
    pass
# set_HLi
def test_0xFE():
    pass
# set_A
def test_0xFF():
    pass

# res_B
def test_0x80():
    pass
# res_C
def test_0x81():
    pass
# res_D
def test_0x82():
    pass
# res_E
def test_0x83():
    pass
# res_H
def test_0x84():
    pass
# res_L
def test_0x85():
    pass
# res_HLi
def test_0x86():
    pass
# res_A
def test_0x87():
    pass

# res_B
def test_0x88():
    pass
# res_C
def test_0x89():
    pass
# res_D
def test_0x8A():
    pass
# res_E
def test_0x8B():
    pass
# res_H
def test_0x8C():
    pass
# res_L
def test_0x8D():
    pass
# res_HLi
def test_0x8E():
    pass
# res_A
def test_0x8F():
    pass

# res_B
def test_0x90():
    pass
# res_C
def test_0x91():
    pass
# res_D
def test_0x92():
    pass
# res_E
def test_0x93():
    pass
# res_H
def test_0x94():
    pass
# res_L
def test_0x95():
    pass
# res_HLi
def test_0x96():
    pass
# res_A
def test_0x97():
    pass

# res_B
def test_0x98():
    pass
# res_C
def test_0x99():
    pass
# res_D
def test_0x9A():
    pass
# res_E
def test_0x9B():
    pass
# res_H
def test_0x9C():
    pass
# res_L
def test_0x9D():
    pass
# res_HLi
def test_0x9E():
    pass
# res_A
def test_0x9F():
    pass

# res_B
def test_0xA0():
    pass
# res_C
def test_0xA1():
    pass
# res_D
def test_0xA2():
    pass
# res_E
def test_0xA3():
    pass
# res_H
def test_0xA4():
    pass
# res_L
def test_0xA5():
    pass
# res_HLi
def test_0xA6():
    pass
# res_A
def test_0xA7():
    pass

# res_B
def test_0xA8():
    pass
# res_C
def test_0xA9():
    pass
# res_D
def test_0xAA():
    pass
# res_E
def test_0xAB():
    pass
# res_H
def test_0xAC():
    pass
# res_L
def test_0xAD():
    pass
# res_HLi
def test_0xAE():
    pass
# res_A
def test_0xAF():
    pass

# res_B
def test_0xB0():
    pass
# res_C
def test_0xB1():
    pass
# res_D
def test_0xB2():
    pass
# res_E
def test_0xB3():
    pass
# res_H
def test_0xB4():
    pass
# res_L
def test_0xB5():
    pass
# res_HLi
def test_0xB6():
    pass
# res_A
def test_0xB7():
    pass

# res_B
def test_0xB8():
    pass
# res_C
def test_0xB9():
    pass
# res_D
def test_0xBA():
    pass
# res_E
def test_0xBB():
    pass
# res_H
def test_0xBC():
    pass
# res_L
def test_0xBD():
    pass
# res_HLi
def test_0xBE():
    pass
# res_A
def test_0xBF():
    pass




    