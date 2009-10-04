import os, random, struct
import py
from pypy.jit.backend.x86 import ri386
from pypy.rlib.rarithmetic import intmask
from pypy.tool.udir import udir

INPUTNAME = str(udir.join('checkfile_%s.s'))
FILENAME = str(udir.join('checkfile_%s.o'))
BEGIN_TAG = '<<<ri386-test-begin>>>'
END_TAG =   '<<<ri386-test-end>>>'

COUNT1 = 15
COUNT2 = 25

suffixes = {0:'', 1:'b', 2:'w', 4:'l'}

def reg_tests():
    return range(8)

def stack_tests(count=COUNT1):
    return ([0, 4, -4, 124, 128, -128, -132] +
            [random.randrange(-0x20000000, 0x20000000) * 4
             for i in range(count)])

def memory_tests():
    return [ri386.reg_offset(reg, ofs)
                for reg in [ri386.eax, ri386.ecx, ri386.edx, ri386.ebx,
                            ri386.esi, ri386.edi]
                for ofs in stack_tests(5)
            ]

def array_tests():
    return [ri386.reg_reg_scaleshift_offset(reg1, reg2, scaleshift, ofs)
                for reg1 in [ri386.eax, ri386.ecx, ri386.edx, ri386.ebx,
                             ri386.esi, ri386.edi]  #, ri386.esp
                for reg2 in [ri386.eax, ri386.ecx, ri386.edx, ri386.ebx,
                             ri386.esi, ri386.edi]  #, ri386.ebp
                for scaleshift in [0, 1, 2, 3]
                for ofs in stack_tests(1)
            ]

def imm8_tests():
    v = [-128,-1,0,1,127] + [random.randrange(-127, 127) for i in range(COUNT1)]
    return v

def imm16_tests():
    v = [-32768,32767] + [random.randrange(-32767, -128) for i in range(COUNT1)] \
           + [random.randrange(128, 32767) for i in range(COUNT1)]
    return v

def imm32_tests():
    v = ([0x80000000, 0x7FFFFFFF, 128, 256, -129, -255] +
         [random.randrange(0,65536)<<16 |
             random.randrange(0,65536) for i in range(COUNT1)] +
         [random.randrange(128, 256) for i in range(COUNT1)])
    return imm8_tests() + v

def pick1(memSIB, cache=[]):
    base = random.choice([None, None, None] + i386.registers)
    index = random.choice([None, None, None] + i386.registers)
    if index is i386.esp: index=None
    scale = random.randrange(0,4)
    if not cache:
        cache[:] = [x.value for x in imm8_tests() + imm32_tests()] + [0,0]
        random.shuffle(cache)
    offset = cache.pop()
    if base is None and scale==0:
        base = index
        index = None
    return memSIB(base, index, scale, offset)

def modrm_tests():
    return i386.registers + [pick1(i386.memSIB) for i in range(COUNT2)]

def modrm_noreg_tests():
    return [pick1(i386.memSIB) for i in range(COUNT2)]

def modrm64_tests():
    return [pick1(i386.memSIB64) for i in range(COUNT2)]

def xmm_tests():
    return i386.xmm_registers

def modrm8_tests():
    return i386.registers8 + [pick1(i386.memSIB8) for i in range(COUNT2)]

tests = {
    'r': reg_tests,
    's': stack_tests,
    'm': memory_tests,
    'a': array_tests,
    'i': imm32_tests,
    }

regnames = ['%eax', '%ecx', '%edx', '%ebx', '%esp', '%ebp', '%esi', '%edi']
def assembler_operand_reg(regnum):
    return regnames[regnum]

def assembler_operand_stack(position):
    return '%d(%%ebp)' % position

def assembler_operand_memory(reg1_offset):
    reg1 = intmask(reg1_offset >> 32)
    offset = intmask(reg1_offset)
    if not offset: offset = ''
    return '%s(%s)' % (offset, regnames[reg1])

def assembler_operand_array(reg1_reg2_scaleshift_offset):
    SIB = intmask(reg1_reg2_scaleshift_offset >> 32)
    offset = intmask(reg1_reg2_scaleshift_offset)
    if not offset: offset = ''
    reg1 = SIB & 7
    reg2 = (SIB >> 3) & 7
    scaleshift = SIB >> 6
    return '%s(%s,%s,%d)' % (offset, regnames[reg1], regnames[reg2],
                             1<<scaleshift)

def assembler_operand_imm(value):
    return '$%d' % value

assembler_operand = {
    'r': assembler_operand_reg,
    's': assembler_operand_stack,
    'm': assembler_operand_memory,
    'a': assembler_operand_array,
    'i': assembler_operand_imm,
    }

def run_test(methname, instrname, argmodes, args_lists):
    global labelcount
    labelcount = 0
    oplist = []
    g = open(INPUTNAME % methname, 'w')
    g.write('\x09.string "%s"\n' % BEGIN_TAG)
    for args in args_lists:
        suffix = ""
##        all = instr.as_all_suffixes
##        for m, extra in args:
##            if m in (i386.MODRM, i386.MODRM8) or all:
##                suffix = suffixes[sizes[m]] + suffix
        if argmodes:
            suffix = 'l'
        
        following = ""
        if False:   # instr.indirect:
            suffix = ""
            if args[-1][0] == i386.REL32: #in (i386.REL8,i386.REL32):
                labelcount += 1
                following = "\nL%d:" % labelcount
            elif args[-1][0] in (i386.IMM8,i386.IMM32):
                args = list(args)
                args[-1] = ("%d", args[-1][1])  # no '$' sign
            else:
                suffix += " *"
            k = -1
        else:
            k = len(args)
        #for m, extra in args[:k]:
        #    assert m != i386.REL32  #not in (i386.REL8,i386.REL32)
        ops = []
        for mode, v in zip(argmodes, args):
            ops.append(assembler_operand[mode](v))
        ops.reverse()
        op = '\t%s%s %s%s' % (instrname.lower(), suffix,
                              ', '.join(ops), following)
        g.write('%s\n' % op)
        oplist.append(op)
    g.write('\t.string "%s"\n' % END_TAG)
    g.close()
    os.system('as "%s" -o "%s"' % (INPUTNAME % methname, FILENAME % methname))
    try:
        f = open(FILENAME % methname, 'rb')
    except IOError:
        raise Exception("Assembler error")
    data = f.read()
    f.close()
    i = data.find(BEGIN_TAG)
    assert i>=0
    j = data.find(END_TAG, i)
    assert j>=0
    as_code = data[i+len(BEGIN_TAG)+1:j]
    return oplist, as_code

def make_all_tests(methname, modes, args=[]):
    if modes:
        m = modes[0]
        lst = tests[m]()
        random.shuffle(lst)
        result = []
        for v in lst:
            result += make_all_tests(methname, modes[1:], args+[v])
        return result
    else:
        # special cases
        if methname in ('ADD_ri', 'AND_ri', 'CMP_ri', 'OR_ri',
                        'SUB_ri', 'XOR_ri'):
            if args[0] == ri386.eax:
                return []     # ADD EAX, constant: there is a special encoding
##        if methname == "MOV_":
####            if args[0] == args[1]:
####                return []   # MOV reg, same reg
##            if ((args[0][1] in (i386.eax, i386.al))
##                and args[1][1].assembler().lstrip('-').isdigit()):
##                return []   # MOV accum, [constant-address]
##            if ((args[1][1] in (i386.eax, i386.al))
##                and args[0][1].assembler().lstrip('-').isdigit()):
##                return []   # MOV [constant-address], accum
##        if instrname == "MOV16":
##            return []   # skipped
##        if instrname == "LEA":
##            if (args[1][1].__class__ != i386.MODRM or
##                args[1][1].is_register()):
##                return []
##        if instrname == "INT":
##            if args[0][1].value == 3:
##                return []
##        if instrname in ('SHL', 'SHR', 'SAR'):
##            if args[1][1].assembler() == '$1':
##                return []
##        if instrname in ('MOVZX', 'MOVSX'):
##            if args[1][1].width == 4:
##                return []
##        if instrname == "TEST":
##            if (args[0] != args[1] and
##                isinstance(args[0][1], i386.REG) and
##                isinstance(args[1][1], i386.REG)):
##                return []   # TEST reg1, reg2  <=>  TEST reg2, reg1
##        if instrname.endswith('cond'):
##            return []
        return [args]

def hexdump(s):
    return ' '.join(["%02X" % ord(c) for c in s])


class CodeChecker(ri386.I386CodeBuilder):
    
    def __init__(self, expected):
        self.expected = expected
        self.index = 0

    def begin(self, op):
        self.op = op
        self.instrindex = self.index

    def writechar(self, char):
        if char != self.expected[self.index:self.index+1]:
            print self.op
            print "\x09from ri386.py:", hexdump(self.expected[self.instrindex:self.index] + char)+"..."
            print "\x09from 'as':    ", hexdump(self.expected[self.instrindex:self.index+1])+"..."
            raise Exception("Differs")
        self.index += 1

    def done(self):
        assert len(self.expected) == self.index


def complete_test(methname):
    if '_' in methname:
        instrname, argmodes = methname.split('_')
    else:
        instrname, argmodes = methname, ''
    print "Testing %s with argmodes=%r" % (instrname, argmodes)
    ilist = make_all_tests(methname, argmodes)
    oplist, as_code = run_test(methname, instrname, argmodes, ilist)
    cc = CodeChecker(as_code)
    for op, args in zip(oplist, ilist):
        if op:
            cc.begin(op)
            getattr(cc, methname)(*args)
    cc.done()

def test_auto():
    import os
    g = os.popen('as -version </dev/null -o /dev/null 2>&1')
    data = g.read()
    g.close()
    if not data.startswith('GNU assembler'):
        py.test.skip("full tests require the GNU 'as' assembler")

    def do_test(name):
        if name in ('CMOVPE', 'CMOVPO'):
            py.test.skip("why doesn't 'as' know about CMOVPE/CMOVPO?")
        if name.split('_')[0][-1].isdigit():
            print "artificial instruction: %r" % (name,)
            return
        complete_test(name)

    for name in ri386.all_instructions:
        yield do_test, name
