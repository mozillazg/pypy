from pypy.jit.backend.x86.ri386 import *
from pypy.jit.backend.x86.assembler import Assembler386
from pypy.rpython.lltypesystem import lltype, rffi, rstr, llmemory
from pypy.jit.backend.x86.regalloc import X86FrameManager, get_ebp_ofs
from pypy.jit.backend.x86.test.test_assembler import FakeMC, FakeCPU

def do_unwinder_recovery_func(withfloats=False):
    import random
    S = lltype.GcStruct('S')

    def get_random_int():
        return random.randrange(-10000, 10000)
    def get_random_ptr():
        return lltype.cast_opaque_ptr(llmemory.GCREF, lltype.malloc(S))

    def get_random_float():
        assert withfloats
        value = random.random() - 0.5
        # make sure it fits into 64 bits
        tmp = lltype.malloc(rffi.LONGP.TO, 2, flavor='raw')
        rffi.cast(rffi.DOUBLEP, tmp)[0] = value
        return rffi.cast(rffi.DOUBLEP, tmp)[0], tmp[0], tmp[1]

    # memory locations: 26 integers, 26 pointers, 26 floats
    # main registers: half of them as signed and the other half as ptrs
    # xmm registers: all floats, from xmm0 to xmm7
    # holes: 8
    locations = []
    baseloc = 4
    for i in range(26+26+26):
        if baseloc < 128:
            baseloc += random.randrange(2, 20)
        else:
            baseloc += random.randrange(2, 1000)
        locations.append(baseloc)
    random.shuffle(locations)
    content = ([('int', locations.pop()) for _ in range(26)] +
               [('ptr', locations.pop()) for _ in range(26)] +
               [(['int', 'ptr'][random.randrange(0, 2)], reg)
                         for reg in [eax, ecx, edx, ebx, esi, edi]])
    if withfloats:
        content += ([('float', locations.pop()) for _ in range(26)] +
                    [('float', reg) for reg in [xmm0, xmm1, xmm2, xmm3,
                                                xmm4, xmm5, xmm6, xmm7]])
    for i in range(8):
        content.append(('hole', None))
    random.shuffle(content)

    # prepare the expected target arrays, the descr_bytecode,
    # the 'registers' and the 'stack' arrays according to 'content'
    xmmregisters = lltype.malloc(rffi.LONGP.TO, 16+9, flavor='raw')
    registers = rffi.ptradd(xmmregisters, 16)
    stacklen = baseloc + 10
    stack = lltype.malloc(rffi.LONGP.TO, stacklen, flavor='raw')
    expected_ints = [] 
    expected_ptrs = [] 
    expected_floats = [] 

    def write_in_stack(loc, value):
        assert loc >= 0
        ofs = get_ebp_ofs(loc)
        assert ofs < 0
        assert (ofs % 4) == 0
        stack[stacklen + ofs//4] = value

    descr_bytecode = []
    for i, (kind, loc) in enumerate(content):
        if kind == 'hole':
            num = Assembler386.CODE_HOLE
        else:
            if kind == 'float':
                value, lo, hi = get_random_float()
                expected_floats.append(value)
                kind = Assembler386.DESCR_FLOAT
                if isinstance(loc, REG):
                    xmmregisters[2*loc.op] = lo
                    xmmregisters[2*loc.op+1] = hi
                else:
                    write_in_stack(loc, hi)
                    write_in_stack(loc+1, lo)
            else:
                if kind == 'int':
                    value = get_random_int()
                    expected_ints.append(value)
                    kind = Assembler386.DESCR_INT
                elif kind == 'ptr':
                    value = get_random_ptr()
                    expected_ptrs.append(value)
                    kind = Assembler386.DESCR_REF
                    value = rffi.cast(rffi.LONG, value)
                else:
                    assert 0, kind
                if isinstance(loc, REG):
                    registers[loc.op] = value
                else:
                    write_in_stack(loc, value)

            if isinstance(loc, REG):
                num = kind + 4*loc.op
            else:
                num = kind + 4*(8+loc)
            while num >= 0x80:
                descr_bytecode.append((num & 0x7F) | 0x80)
                num >>= 7
        descr_bytecode.append(num)

    descr_bytecode.append(Assembler386.CODE_STOP)
    descr_bytecode.append(0xC3)   # fail_index = 0x1C3
    descr_bytecode.append(0x01)
    descr_bytecode.append(0x00)
    descr_bytecode.append(0x00)
    descr_bytecode.append(0xCC)   # end marker
    descr_bytes = lltype.malloc(rffi.UCHARP.TO, len(descr_bytecode),
                                flavor='raw')
    for i in range(len(descr_bytecode)):
        assert 0 <= descr_bytecode[i] <= 255
        descr_bytes[i] = rffi.cast(rffi.UCHAR, descr_bytecode[i])
    registers[8] = rffi.cast(rffi.LONG, descr_bytes)
    registers[ebp.op] = rffi.cast(rffi.LONG, stack) + 4*stacklen

    # test
    assembler = Assembler386(FakeCPU())
    state_header = assembler.unwinder_recovery_func(registers)

    if state_header.saved_ints:
        for x,y in zip(state_header.saved_ints, expected_ints):
            assert x == y

    if state_header.saved_floats:
        for x,y in zip(state_header.saved_floats, expected_floats):
            assert x == y

    if state_header.saved_refs:
        for x,y in zip(state_header.saved_refs, expected_ptrs):
            assert x == y

def test_unwinder_recovery():
    do_unwinder_recovery_func()

def test_unwinder_recovery_with_floats():
    do_unwinder_recovery_func(withfloats=True)
