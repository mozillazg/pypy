"""
Bytecode handling classes and functions for use by the flow space.
"""
from rpython.tool.stdlib_opcode import host_bytecode_spec
from opcode import EXTENDED_ARG, HAVE_ARGUMENT
import opcode
from rpython.flowspace.argument import Signature
from rpython.flowspace.flowcontext import BytecodeCorruption

CO_GENERATOR = 0x0020
CO_VARARGS = 0x0004
CO_VARKEYWORDS = 0x0008

def cpython_code_signature(code):
    "([list-of-arg-names], vararg-name-or-None, kwarg-name-or-None)."
    argcount = code.co_argcount
    argnames = list(code.co_varnames[:argcount])
    if code.co_flags & CO_VARARGS:
        varargname = code.co_varnames[argcount]
        argcount += 1
    else:
        varargname = None
    if code.co_flags & CO_VARKEYWORDS:
        kwargname = code.co_varnames[argcount]
        argcount += 1
    else:
        kwargname = None
    return Signature(argnames, varargname, kwargname)

class HostCode(object):
    """
    A wrapper around a native code object of the host interpreter
    """
    opnames = host_bytecode_spec.method_names

    def __init__(self, argcount, nlocals, stacksize, flags,
                     code, consts, names, varnames, filename,
                     name, firstlineno, lnotab, freevars):
        """Initialize a new code object"""
        assert nlocals >= 0
        self.co_argcount = argcount
        self.co_nlocals = nlocals
        self.co_stacksize = stacksize
        self.co_flags = flags
        self.co_code = code
        self.consts = consts
        self.names = names
        self.co_varnames = varnames
        self.co_freevars = freevars
        self.co_filename = filename
        self.co_name = name
        self.co_firstlineno = firstlineno
        self.co_lnotab = lnotab
        self.signature = cpython_code_signature(self)
        self.build_flow()

    def disassemble(self):
        contents = []
        offsets = []
        jumps = {}
        pos = 0
        i = 0
        while pos < len(self.co_code):
            offsets.append(pos)
            next_pos, op = self.decode(pos)
            contents.append(op)
            if op.has_jump():
                jumps[pos] = op.arg
            pos = next_pos
            i += 1
        return contents, offsets, jumps

    def build_flow(self):
        next_pos = pos = 0
        contents, offsets, jumps = self.disassemble()
        self.contents = zip(offsets, contents)
        self.pos_index = dict((offset, i) for i, offset in enumerate(offsets))
        # add end marker
        self.contents.append((len(self.co_code), None))


    @classmethod
    def _from_code(cls, code):
        """Initialize the code object from a real (CPython) one.
        """
        return cls(code.co_argcount,
                      code.co_nlocals,
                      code.co_stacksize,
                      code.co_flags,
                      code.co_code,
                      list(code.co_consts),
                      list(code.co_names),
                      list(code.co_varnames),
                      code.co_filename,
                      code.co_name,
                      code.co_firstlineno,
                      code.co_lnotab,
                      list(code.co_freevars))

    @property
    def formalargcount(self):
        """Total number of arguments passed into the frame, including *vararg
        and **varkwarg, if they exist."""
        return self.signature.scope_length()

    def read(self, pos):
        i = self.pos_index[pos]
        op = self.contents[i][1]
        next_pos = self.contents[i+1][0]
        return next_pos, op


    def decode(self, pos):
        """
        Decode the instruction starting at position ``next_instr``.

        Returns (next_instr, op).
        """
        co_code = self.co_code
        opnum = ord(co_code[pos])
        next_instr = pos + 1

        if opnum >= HAVE_ARGUMENT:
            lo = ord(co_code[next_instr])
            hi = ord(co_code[next_instr+1])
            next_instr += 2
            oparg = (hi * 256) | lo
        else:
            oparg = 0

        while opnum == EXTENDED_ARG:
            opnum = ord(co_code[next_instr])
            if opnum < HAVE_ARGUMENT:
                raise BytecodeCorruption
            lo = ord(co_code[next_instr+1])
            hi = ord(co_code[next_instr+2])
            next_instr += 3
            oparg = (oparg * 65536) | (hi * 256) | lo

        if opnum in opcode.hasjrel:
            oparg += next_instr
        elif opnum in opcode.hasname:
            oparg = self.names[oparg]
        try:
            op = Opcode.num2op[opnum].decode(oparg, pos, self)
        except KeyError:
            op = Opcode(opnum, oparg, pos)
        return next_instr, op

    @property
    def is_generator(self):
        return bool(self.co_flags & CO_GENERATOR)

OPNAMES = host_bytecode_spec.method_names

class Opcode(object):
    num2op = {}
    def __init__(self, opcode, arg, offset=-1):
        self.name = OPNAMES[opcode]
        self.num = opcode
        self.arg = arg
        self.offset = offset

    @classmethod
    def decode(cls, arg, offset, code):
        return cls(arg, offset)

    def eval(self, frame):
        return getattr(frame, self.name)(self.arg)

    @classmethod
    def register_name(cls, name, op_class):
        try:
            num = OPNAMES.index(name)
            cls.num2op[num] = op_class
            return num
        except ValueError:
            return -1

    def has_jump(self):
        return self.num in opcode.hasjrel or self.num in opcode.hasjabs

    def __repr__(self):
        return "%s(%d)" % (self.name, self.arg)

def register_opcode(cls):
    """Class decorator: register opcode class as real Python opcode"""
    name = cls.__name__
    cls.name = name
    cls.num = Opcode.register_name(name, cls)
    return cls

@register_opcode
class LOAD_CONST(Opcode):
    def __init__(self, arg, offset=-1):
        self.arg = arg
        self.offset = offset

    @staticmethod
    def decode(arg, offset, code):
        return LOAD_CONST(code.consts[arg], offset)
