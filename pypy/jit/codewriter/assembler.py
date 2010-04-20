from pypy.jit.metainterp.history import AbstractValue, getkind
from pypy.jit.codewriter.flatten import Register, Label, TLabel, KINDS
from pypy.objspace.flow.model import Constant


class JitCode(AbstractValue):
    _empty_i = []
    _empty_r = []
    _empty_f = []

    def __init__(self, name, cfnptr=None, calldescr=None, called_from=None,
                 graph=None):
        self.name = name
        self.cfnptr = cfnptr
        self.calldescr = calldescr
        self.called_from = called_from
        self.graph = graph

    def setup(self, code, constants_i=[], constants_r=[], constants_f=[]):
        self.code = code
        # if the following lists are empty, use a single shared empty list
        self.constants_i = constants_i or self._empty_i
        self.constants_r = constants_r or self._empty_r
        self.constants_f = constants_f or self._empty_f


class Assembler(object):

    def __init__(self):
        self.insns = {}

    def assemble(self, ssarepr):
        code = []
        constants_dict = {}
        constants_i = []
        constants_r = []
        constants_f = []
        label_positions = {}
        tlabel_positions = []
        highest_regs = dict.fromkeys(KINDS, 0)
        for insn in ssarepr.insns:
            if isinstance(insn[0], Label):
                label_positions[insn[0].name] = len(code)
                continue
            startposition = len(code)
            code.append("temporary placeholder")
            #
            argcodes = []
            for x in insn[1:]:
                if isinstance(x, Register):
                    if x.index > highest_regs[x.kind]:
                        highest_regs[x.kind] = x.index
                    code.append(chr(x.index))
                    argcodes.append(x.kind[0])
                elif isinstance(x, Constant):
                    kind = getkind(x.concretetype)
                    if kind == 'int' and -128 <= x.value <= 127:
                        code.append(chr(x.value & 0xFF))
                        argcodes.append('c')
                    else:
                        if x not in constants_dict:
                            if kind == 'int':
                                constants = constants_i
                            elif kind == 'ref':
                                constants = constants_r
                            elif kind == 'float':
                                constants = constants_f
                            else:
                                raise NotImplementedError(x)
                            constants.append(x.value)
                            constants_dict[x] = 256 - len(constants)
                        code.append(chr(constants_dict[x]))
                        argcodes.append(kind[0])
                elif isinstance(x, TLabel):
                    tlabel_positions.append((x.name, len(code)))
                    code.append("temp 1")
                    code.append("temp 2")
                    argcodes.append('L')
                else:
                    raise NotImplementedError(x)
            #
            key = insn[0] + '/' + ''.join(argcodes)
            num = self.insns.setdefault(key, len(self.insns))
            code[startposition] = chr(num)
        #
        for name, pos in tlabel_positions:
            assert code[pos  ] == "temp 1"
            assert code[pos+1] == "temp 2"
            target = label_positions[name]
            assert 0 <= target <= 0xFFFF
            code[pos  ] = chr(target & 0xFF)
            code[pos+1] = chr(target >> 8)
        #
        # Limitation of the number of registers, from the single-byte encoding
        assert highest_regs['int'] + len(constants_i) <= 256
        assert highest_regs['ref'] + len(constants_r) <= 256
        assert highest_regs['float'] + len(constants_f) <= 256
        #
        jitcode = JitCode(ssarepr.name)
        jitcode.setup(''.join(code), constants_i, constants_r, constants_f)
        return jitcode
