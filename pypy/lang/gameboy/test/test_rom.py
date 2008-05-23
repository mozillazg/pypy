
import py
from pypy.lang.gameboy import constants
from pypy.lang.gameboy.cpu import *
from pypy.lang.gameboy.cartridge import *
from pypy.lang.gameboy.gameboy import *


ROM_PATH = str(py.magic.autopath().dirpath().dirpath())+"/rom"
EMULATION_CYCLES = 64

# ------------------------------------------------------------------------------

def emulate_step_op_codes_test(gameboy, op_codes):
    count = 0
    for op_code in op_codes:
        gameboy.emulate_step()
        assert gameboy.cpu.last_op_code == op_code, \
                "Excpected: %s got %s, turn: %i" % \
                ( hex(op_code), hex(gameboy.cpu.last_op_code), count)
        count += 1

# ------------------------------------------------------------------------------

def test_rom1_load():
    gameboy = GameBoy()
    try:
        gameboy.load_cartridge_file(ROM_PATH+"/rom1/rom1.raw")
        py.test.fail()
    except:
        pass
    
def test_rom1_step():
    py.test.skip()
    gameboy = GameBoy()
    gameboy.load_cartridge_file(ROM_PATH+"/rom1/rom1.raw", verify=False)
    emulate_step_op_codes_test(gameboy, [])
    
# ------------------------------------------------------------------------------
    
def test_rom2_load():
    gameboy = GameBoy()
    try:
        gameboy.load_cartridge_file(ROM_PATH+"/rom2/rom2.raw")
        py.test.fail()
    except:
        pass

# ------------------------------------------------------------------------------    

def test_rom3_load():
    """ some NOP and an endless loop at the end '"""
    gameboy = GameBoy()
    gameboy.load_cartridge_file(ROM_PATH+"/rom3/rom3.gb")
    gameboy.emulate(EMULATION_CYCLES)
    

def test_rom3_step():
    py.test.skip()
    gameboy = GameBoy()
    gameboy.load_cartridge_file(ROM_PATH+"/rom3/rom3.gb")
    # jp nop
    emulate_step_op_codes_test(gameboy, [0xC3])
    emulate_step_op_codes_test(gameboy, [0]*12)
    emulate_step_op_codes_test(gameboy, [0xC3]*100)
    
# ------------------------------------------------------------------------------
 
def test_rom4_load():
    gameboy = GameBoy()
    gameboy.load_cartridge_file(ROM_PATH+"/rom4/rom4.gb")
    gameboy.emulate(EMULATION_CYCLES)
    
    assert gameboy.cpu.ime     == False
    assert gameboy.cpu.halted  == True
    assert gameboy.cpu.a.get() != 0xFF
    
def test_rom4_step():
    gameboy = GameBoy()
    gameboy.load_cartridge_file(ROM_PATH+"/rom4/rom4.gb")
    emulate_step_op_codes_test(gameboy, [0, 0xC3, 0xF3, 0x21])
    assert gameboy.cpu.hl.get() == 0xFF40
    emulate_step_op_codes_test(gameboy, [0xCB, 0x76, 0x76, 0x3E])
    

# ------------------------------------------------------------------------------    
    
def test_rom5_load():
    gameboy = GameBoy()
    gameboy.load_cartridge_file(ROM_PATH+"/rom5/rom5.gb")
    gameboy.emulate(EMULATION_CYCLES)
    # stop test
    assert gameboy.cpu.a.get() != 0xFF
    

def test_rom5_step():
    gameboy = GameBoy()
    gameboy.load_cartridge_file(ROM_PATH+"/rom5/rom5.gb")
    
    emulate_step_op_codes_test(gameboy, [0, 0xC3, 0xF3, 0xAF, 0x3D, 0xC2])
    assert gameboy.cpu.pc.get() == 0x0152
    assert gameboy.cpu.a.get() == 0xFF
    emulate_step_op_codes_test(gameboy, [0x3D, 0xC2]*0xFF)
    assert gameboy.cpu.a.get()  == 0
    
    emulate_step_op_codes_test(gameboy, [0xDD, 0xAF, 0xC6])
    pc = gameboy.cpu.pc.get()
    assert gameboy.cpu.a.get() == 1
    assert gameboy.cpu.f.c_flag == False
    emulate_step_op_codes_test(gameboy, [0x30])
    assert gameboy.cpu.pc.get()  == pc-2
    emulate_step_op_codes_test(gameboy, [0xC6, 0x30]*255)
    assert gameboy.cpu.a.get() == 0
    assert gameboy.cpu.f.c_flag == True
    
    emulate_step_op_codes_test(gameboy, [0xDD, 0xAF])
    assert gameboy.cpu.a.get() == 0
    assert gameboy.cpu.f.c_flag == False
    pc = gameboy.cpu.pc.get()
    emulate_step_op_codes_test(gameboy, [0x3C, 0xD2])
    assert gameboy.cpu.f.c_flag == False
    assert gameboy.cpu.a.get() == 1
    assert gameboy.cpu.pc.get() == pc
    emulate_step_op_codes_test(gameboy, [0x3C, 0xD2]*255)
    assert gameboy.cpu.a.get() == 0
    assert gameboy.cpu.f.c_flag == True
    
    emulate_step_op_codes_test(gameboy, [0xDD, 0x76, 0x76])
    
# ------------------------------------------------------------------------------
    
def test_rom6_load():
    gameboy = GameBoy()
    gameboy.load_cartridge_file(ROM_PATH+"/rom6/rom6.gb")
    gameboy.emulate(EMULATION_CYCLES)
    
def test_rom6_step():
    gameboy = GameBoy()
    gameboy.load_cartridge_file(ROM_PATH+"/rom6/rom6.gb")
    cpu = gameboy.cpu
    
    emulate_step_op_codes_test(gameboy, [0, 0xC3, 0xF3, 0x21, 0xF9])
    assert cpu.hl.get() == 0xC200
    assert cpu.sp.get() == cpu.hl.get()
    
    emulate_step_op_codes_test(gameboy, [0x3E, 0xEA])
    assert cpu.a.get() == 0x01
    #assert cpu.read(0x6000) == cpu.a.get()
    
    emulate_step_op_codes_test(gameboy, [0x3E, 0xEA])
    assert cpu.a.get() == 0x01
    #assert cpu.read(0x2000) == cpu.a.get()
    
    emulate_step_op_codes_test(gameboy, [0x3E, 0xEA])
    assert cpu.a.get() == 0x00
    #assert cpu.read(0x4000) == cpu.a.get()
    
    emulate_step_op_codes_test(gameboy, [0x3E, 0xEA])
    assert cpu.a.get() == 0x0A
    #assert cpu.read(0x0000) == cpu.a.get()
    
    emulate_step_op_codes_test(gameboy, [0x21, 0x01, 0x3E])
    assert cpu.hl.get() == 0xA000
    assert cpu.bc.get() == 0x0020
    assert cpu.a.get()  == 0xFF
    
    def call_mem_set():
        pc_return = cpu.pc.get()
        emulate_step_op_codes_test(gameboy, [0xCD])
        assert cpu.pc.get() == 0x0198

        pc, b, c = cpu.pc.get(), cpu.b.get(), cpu.c.get()
        emulate_step_op_codes_test(gameboy, [0x04, 0x0C, 0x18])
        assert cpu.b.get() == b+1
        assert cpu.c.get() == c+1
        assert cpu.pc.get() == pc+5
        
        c = cpu.c.get()
        emulate_step_op_codes_test(gameboy, [0x0D, 0x20])
        assert cpu.c.get() == c-1
        
        while not cpu.f.z_flag:
            hl = cpu.hl.get()
            emulate_step_op_codes_test(gameboy, [0x22])
            assert cpu.hl.get() == hl+1
            #assert cpu.read(cpu.hl.get()) == cpu.a.get()
            
            emulate_step_op_codes_test(gameboy, [0x0D, 0x20])
        
        b = cpu.b.get()
        emulate_step_op_codes_test(gameboy, [0x05, 0x20])
        assert cpu.b.get() == b-1
        
        emulate_step_op_codes_test(gameboy, [0xC9])
        assert cpu.pc.get() == pc_return+3
    
    call_mem_set()
    
    emulate_step_op_codes_test(gameboy, [0x3E, 0xEA, 0x21, 0x01])
    assert cpu.a.get() == 0x01
    #assert cpu.read(0x4000) == cpu.a.get()
    assert cpu.hl.get() == 0xA000
    assert cpu.bc.get() == 0x0020
    emulate_step_op_codes_test(gameboy, [0x3E])
    assert cpu.a.get() == 0x22
    
    call_mem_set()
    
    
    emulate_step_op_codes_test(gameboy, [0x3E, 0xEA])
    assert cpu.a.get() == 0x00
    
    emulate_step_op_codes_test(gameboy, [0x3E, 0x21, 0xBE])
    assert cpu.a.get() == 0xFF
    assert cpu.hl.get() == 0xA000
    assert cpu.read(cpu.hl.get()) == cpu.a.get()
    
    emulate_step_op_codes_test(gameboy, [0x20, 0xAF, 0x76, 0x76, 0xdd])
    assert cpu.a.get() == 0
    
                                
    
# ------------------------------------------------------------------------------
    
def test_rom7_load():
    py.test.skip("Current Default ROM Implemenation doesnt allow write")
    gameboy = GameBoy()
    gameboy.load_cartridge_file(ROM_PATH+"/rom7/rom7.gb")
    gameboy.emulate(EMULATION_CYCLES)
    
    
def test_rom7_step():
    py.test.skip("Current Default ROM Implemenation doesnt allow write")
    
# ------------------------------------------------------------------------------
    
def test_rom8_load():
    gameboy = GameBoy()
    gameboy.load_cartridge_file(ROM_PATH+"/rom8/rom8.gb")
    gameboy.emulate(EMULATION_CYCLES)
    
    
    
# ------------------------------------------------------------------------------
    
def test_rom9():
    gameboy = GameBoy()
    gameboy.load_cartridge_file(ROM_PATH+"/rom9/rom9.gb")
    gameboy.emulate(EMULATION_CYCLES)
    
