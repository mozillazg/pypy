import py
from pypy.jit.backend.x86.ri386 import *

class CodeBuilder(I386CodeBuilder):
    def __init__(self):
        self.buffer = []

    def writechar(self, c):
        self.buffer.append(c)    # append a character

    def getvalue(self):
        return ''.join(self.buffer)


def test_mov_ri():
    s = CodeBuilder()
    s.MOV_ri(ecx, -2)
    assert s.getvalue() == '\xB9\xFE\xFF\xFF\xFF'

def test_mov_si():
    s = CodeBuilder()
    s.MOV_si(-36, 1<<24)
    assert s.getvalue() == '\xC7\x45\xDC\x00\x00\x00\x01'

def test_mov_rr():
    s = CodeBuilder()
    s.MOV_rr(ebx, ebp)
    assert s.getvalue() == '\x89\xEB'

def test_mov_sr():
    s = CodeBuilder()
    s.MOV_sr(-36, edx)
    assert s.getvalue() == '\x89\x55\xDC'

def test_mov_rs():
    s = CodeBuilder()
    s.MOV_rs(edx, -36)
    assert s.getvalue() == '\x8B\x55\xDC'

def test_nop_add_rr():
    s = CodeBuilder()
    s.NOP()
    s.ADD_rr(eax, eax)
    assert s.getvalue() == '\x90\x01\xC0'

def test_lea_rs():
    s = CodeBuilder()
    s.LEA_rs(ecx, -36)
    assert s.getvalue() == '\x8D\x4D\xDC'

def test_lea32_rs():
    s = CodeBuilder()
    s.LEA32_rs(ecx, -36)
    assert s.getvalue() == '\x8D\x8D\xDC\xFF\xFF\xFF'
