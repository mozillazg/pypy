import py
from pypy.lang.gameboy.cpu import CPU, Register, DoubleRegister
from pypy.lang.gameboy.ram import RAM
from pypy.lang.gameboy import constants

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
    cpu = get_cpu()
    assert cpu.getA() == constants.RESET_A
    assert cpu.getF() == constants.RESET_F
    assert cpu.bc.get() == constants.RESET_BC
    assert cpu.de.get() == constants.RESET_DE
    assert cpu.pc.get() == constants.RESET_PC
    assert cpu.sp.get() == constants.RESET_SP
    

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
    cpu.jr_cc_nn(True)
    assert startCycles-cpu.cycles == 3
    assert_registers(cpu, pc=pc+value+1)
    # test pc.inc
    startCycles = cpu.cycles
    pc = cpu.pc.get()
    cpu.jr_cc_nn(False)
    assert startCycles-cpu.cycles == 2
    assert cpu.pc.get() == pc+1
    
    
def cycle_test(cpu, opCode, cycles=0):
    startCycles = cpu.cycles
    cpu.execute(opCode)
    cpuUsedCycles = startCycles-cpu.cycles 
    assert cpuUsedCycles == cycles,\
        "Cycles for opCode %s should be %i not %i" %\
         (hex(opCode), cycles, cpuUsedCycles)
         
 # HELPERS
 
def assert_reset_registers(cpu):
    return assert_registers(cpu, \
                            constants.RESET_A, constants.RESET_BC,\
                            constants.RESET_DE, constants.RESET_F,\
                            constants.RESET_HL, constants.RESET_SP,\
                            constants.RESET_PC)

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
        
        
# ------------------------------------------------------------
# opCode Testing

#nop
def test_0x00():
    cpu = get_cpu()
    cycle_test(cpu, 0x00, 1)
    assert_reset_registers(cpu)

#load_mem_SP
def test_0x08():
    cpu = get_cpu()
    assert_reset_registers(cpu)
    startPC = cpu.pc.get()
    cpu.sp.set(0x1234)
    cpu.rom[startPC] = 0xD0
    cpu.rom[startPC+1] = 0xC0
    cycle_test(cpu, 0x08, 5)
    assert_registers(cpu, pc=startPC+2)
    assert cpu.memory.read(0xC0D0) == cpu.sp.getLo()
    assert cpu.memory.read(0xC0D0+1) == cpu.sp.getHi()
    
# stop
def test_0x10():
    cpu = get_cpu()
    pc = cpu.pc.get()
    cycle_test(cpu, 0x10, 0)
    # fetches 1 cycle
    assert_registers(cpu, pc=pc+1)
    
# jr_nn
def test_0x18():
    cpu = get_cpu();
    pc = cpu.pc.get()
    value = 0x12
    cpu.rom[constants.RESET_PC] = value
    assert_reset_registers(cpu)
    cycle_test(cpu, 0x18, 3)
    assert_registers(cpu, pc=pc+value+1)
    
# jr_NZ_nn see test_jr_cc_nn
def test_0x20_0x28_0x30():
    py.test.skip("Op Code Mapping not fully implemented")
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
        assert cpu.pc.ge() == pc+1
        value += 2
        
    
# ld_BC_nnnn to ld_SP_nnnn
def test_0x01_0x11_0x21_0x31():
    py.test.skip("Op Code Mapping not fully implemented")
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
    py.test.skip("Op Code Mapping not fully implemented")
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
        
    
    
    
    