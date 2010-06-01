from pypy.jit.backend.x86.regloc import *
from pypy.jit.backend.x86.test.test_rx86 import CodeBuilder32, assert_encodes_as

class LocationCodeBuilder32(CodeBuilder32, LocationCodeBuilder):
    pass

cb32 = LocationCodeBuilder32

def test_mov_16():
    assert_encodes_as(cb32, "MOV16", (ecx, ebx), '\x66\x89\xD9')
    assert_encodes_as(cb32, "MOV16", (ecx, ImmedLoc(12345)), '\x66\xB9\x39\x30')

def test_cmp_16():
    assert_encodes_as(cb32, "CMP16", (ecx, ebx), '\x66\x39\xD9')
    assert_encodes_as(cb32, "CMP16", (ecx, ImmedLoc(12345)), '\x66\x81\xF9\x39\x30')
