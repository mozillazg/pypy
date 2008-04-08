from pypy.lang.gameboy.cpu import *
from pypy.lang.gameboy.ram import *
from pypy.lang.gameboy import *
from pypy.lang.gameboy.interrupt import * 

class Memory(object):
    def __init__(self):
        self.memory = [0xFF]*0xFFFFF
        
    def write(self, address, data):
        self.memory[address] = data
        
    def read(self, address):
        return self.memory[address]
    
global TEST_CPU

TEST_CPU = None
def get_cpu(new=False):
    if new:
        cpu = CPU(Interrupt(), Memory())
        cpu.setROM([0]*0xFFFF);
        return cpu
    global TEST_CPU
    if TEST_CPU == None:
        TEST_CPU = get_cpu(True)
    TEST_CPU.reset()
    return TEST_CPU

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
    register.set(0)
    assert register.get() == 0
    
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
    register.inc(False)
    assert oldCycles-register.cpu.cycles == 0
    assert register.get() == value+1
    
    register.set(value)
    oldCycles = register.cpu.cycles
    register.inc(True)
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