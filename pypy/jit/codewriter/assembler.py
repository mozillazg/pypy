from pypy.jit.metainterp import history
from pypy.jit.codewriter.flatten import Register, Label, TLabel
from pypy.objspace.flow.model import Constant
from pypy.jit.metainterp.history import ConstInt


class JitCode(history.AbstractValue):
    empty_list = []

    def __init__(self, name, cfnptr=None, calldescr=None, called_from=None,
                 graph=None):
        self.name = name
        self.cfnptr = cfnptr
        self.calldescr = calldescr
        self.called_from = called_from
        self.graph = graph

    def setup(self, code, constants):
        self.code = code
        self.constants = constants or self.empty_list    # share the empty list


class Assembler(object):

    def __init__(self):
        self.insns = {}

    def assemble(self, ssarepr):
        code = []
        constants_dict = {}
        constants_rev = []
        label_positions = {}
        tlabel_positions = []
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
                    code.append(chr(x.index))
                    argcodes.append('i')
                elif isinstance(x, Constant):
                    if -128 <= x.value <= 127:
                        code.append(chr(x.value & 0xFF))
                        argcodes.append('c')
                    else:
                        if x not in constants_dict:
                            constants_rev.append(ConstInt(x.value))
                            constants_dict[x] = 256 - len(constants_rev)
                        code.append(chr(constants_dict[x]))
                        argcodes.append('i')
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
        jitcode = JitCode(ssarepr.name)
        jitcode.setup(''.join(code), constants_rev[::-1])
        return jitcode
