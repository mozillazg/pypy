from pypy.jit.metainterp.history import AbstractValue, getkind
from pypy.jit.codewriter.flatten import Register, Label, TLabel, KINDS
from pypy.jit.codewriter.flatten import ListOfKind
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
        self.setup()
        for insn in ssarepr.insns:
            self.write_insn(insn)
        self.fix_labels()
        self.check_result()
        return self.make_jitcode(ssarepr.name)

    def setup(self):
        self.code = []
        self.constants_dict = {}
        self.constants_i = []
        self.constants_r = []
        self.constants_f = []
        self.label_positions = {}
        self.tlabel_positions = []
        self.highest_regs = dict.fromkeys(KINDS, 0)

    def emit_reg(self, reg):
        if reg.index > self.highest_regs[reg.kind]:
            self.highest_regs[reg.kind] = reg.index
        self.code.append(chr(reg.index))

    def emit_const(self, const, kind):
        if const not in self.constants_dict:
            if kind == 'int':
                constants = self.constants_i
            elif kind == 'ref':
                constants = self.constants_r
            elif kind == 'float':
                constants = self.constants_f
            else:
                raise NotImplementedError(const)
            constants.append(const.value)
            self.constants_dict[const] = 256 - len(constants)
        self.code.append(chr(self.constants_dict[const]))

    def write_insn(self, insn):
        if isinstance(insn[0], Label):
            self.label_positions[insn[0].name] = len(self.code)
            return
        startposition = len(self.code)
        self.code.append("temporary placeholder")
        #
        argcodes = []
        for x in insn[1:]:
            if isinstance(x, Register):
                self.emit_reg(x)
                argcodes.append(x.kind[0])
            elif isinstance(x, Constant):
                kind = getkind(x.concretetype)
                if kind == 'int' and -128 <= x.value <= 127:
                    self.code.append(chr(x.value & 0xFF))
                    argcodes.append('c')
                else:
                    self.emit_const(x, kind)
                    argcodes.append(kind[0])
            elif isinstance(x, TLabel):
                self.tlabel_positions.append((x.name, len(self.code)))
                self.code.append("temp 1")
                self.code.append("temp 2")
                argcodes.append('L')
            elif isinstance(x, ListOfKind):
                itemkind = x.kind
                lst = list(x)
                assert len(lst) <= 255, "list too long!"
                self.code.append(chr(len(lst)))
                for item in lst:
                    if isinstance(item, Register):
                        assert itemkind == item.kind
                        self.emit_reg(item)
                    elif isinstance(item, Constant):
                        assert itemkind == getkind(item.concretetype)
                        self.emit_const(item, itemkind)
                    else:
                        raise NotImplementedError("found in ListOfKind(): %r"
                                                  % (item,))
                argcodes.append(itemkind[0].upper())
            else:
                raise NotImplementedError(x)
        #
        key = insn[0] + '/' + ''.join(argcodes)
        num = self.insns.setdefault(key, len(self.insns))
        self.code[startposition] = chr(num)

    def fix_labels(self):
        for name, pos in self.tlabel_positions:
            assert self.code[pos  ] == "temp 1"
            assert self.code[pos+1] == "temp 2"
            target = self.label_positions[name]
            assert 0 <= target <= 0xFFFF
            self.code[pos  ] = chr(target & 0xFF)
            self.code[pos+1] = chr(target >> 8)

    def check_result(self):
        # Limitation of the number of registers, from the single-byte encoding
        assert self.highest_regs['int'] + len(self.constants_i) <= 256
        assert self.highest_regs['ref'] + len(self.constants_r) <= 256
        assert self.highest_regs['float'] + len(self.constants_f) <= 256

    def make_jitcode(self, name):
        jitcode = JitCode(name)
        jitcode.setup(''.join(self.code),
                      self.constants_i,
                      self.constants_r,
                      self.constants_f)
        return jitcode
