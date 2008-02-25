from pypy.jit.rainbow import codewriter


class SourceIterator:

    def __init__(self, jitcode, source, interpreter, labelpos):
        self.jitcode = jitcode
        self.source = source
        self.interpreter = interpreter
        self.labelpos = labelpos
        self.index = 0
        self.pc = 0

    def finished(self):
        return self.index == len(self.source)

    def peek(self):
        return self.source[self.index]

    def get(self, expected_type, bytes_count):
        arg = self.source[self.index]
        assert isinstance(arg, expected_type)
        self.index += 1
        self.pc += bytes_count
        return arg

    def get_opname(self):
        return self.get(str, 2)

    def load_2byte(self):
        return self.get(int, 2)

    def load_bool(self):
        return self.get(bool, 1)

    def get_greenarg(self):
        i = self.load_2byte()
        if i < 0:
            return self.jitcode.constants[~i]
        return CustomRepr('g%d' % i)

    def get_green_varargs(self):
        greenargs = []
        num = self.load_2byte()
        for i in range(num):
            greenargs.append(self.get_greenarg())
        return greenargs

    def get_red_varargs(self):
        redargs = []
        num = self.load_2byte()
        for i in range(num):
            redargs.append(self.get_redarg())
        return redargs

    def get_redarg(self):
        return CustomRepr('r%d' % self.get(int, 2))

    def get_greenkey(self):
        keydescnum = self.load_2byte()
        if keydescnum == -1:
            return None
        else:
            keydesc = self.jitcode.keydescs[keydescnum]
            return keydesc

    def load_jumptarget(self):
        tlbl = self.get(codewriter.tlabel, 4)
        return self.labelpos[tlbl.name]


class CustomRepr:
    def __init__(self, s):
        self.s = s
    def __repr__(self):
        return self.s


def dump_bytecode(jitcode, file=None):
    # XXX this is not really a disassembler, but just a pretty-printer
    # for the '_source' attribute that codewriter.py attaches
    source = jitcode._source
    interpreter = jitcode._interpreter
    labelpos = jitcode._labelpos
    print >> file, 'JITCODE %r' % (jitcode.name,)

    src = SourceIterator(jitcode, source, interpreter, labelpos)
    noblankline = {0: True}
    while not src.finished():
        arg = src.peek()
        if isinstance(arg, str):
            startpc = src.pc
            opname = src.get_opname()
            opcode = interpreter.find_opcode(opname)
            opimpl = interpreter.opcode_implementations[opcode]
            argtypes = opimpl.argspec
            resulttype = opimpl.resultspec
            args = []

            for argspec in argtypes:
                if argspec == "red":
                    args.append(src.get_redarg())
                elif argspec == "green":
                    args.append(src.get_greenarg())
                elif argspec == "kind":
                    args.append(jitcode.typekinds[src.load_2byte()])
                elif argspec == "jumptarget":
                    args.append(src.load_jumptarget())
                elif argspec == "bool":
                    args.append(src.load_bool())
                elif argspec == "redboxcls":
                    args.append(jitcode.redboxclasses[src.load_2byte()])
                elif argspec == "2byte":
                    args.append(src.load_2byte())
                elif argspec == "greenkey":
                    args.append(src.get_greenkey())
                elif argspec == "promotiondesc":
                    promotiondescnum = src.load_2byte()
                    promotiondesc = jitcode.promotiondescs[promotiondescnum]
                    args.append(promotiondesc)
                elif argspec == "green_varargs":
                    args.append(src.get_green_varargs())
                elif argspec == "red_varargs":
                    args.append(src.get_red_varargs())
                elif argspec == "bytecode":
                    bytecodenum = src.load_2byte()
                    called_bytecode = jitcode.called_bytecodes[bytecodenum]
                    args.append(called_bytecode.name)
                elif argspec == "calldesc":
                    index = src.load_2byte()
                    function = jitcode.calldescs[index]
                    args.append(function)
                elif argspec == "oopspec":
                    oopspecindex = src.load_2byte()
                    oopspec = jitcode.oopspecdescs[oopspecindex]
                    args.append(oopspec)
                elif argspec == "structtypedesc":
                    td = jitcode.structtypedescs[src.load_2byte()]
                    args.append(td)
                elif argspec == "arraydesc":
                    td = jitcode.arrayfielddescs[src.load_2byte()]
                    args.append(td)
                elif argspec == "fielddesc":
                    d = jitcode.fielddescs[src.load_2byte()]
                    args.append(d)
                elif argspec == "interiordesc":
                    d = jitcode.interiordescs[src.load_2byte()]
                    args.append(d)
                else:
                    assert 0, "unknown argtype declaration"

            args = map(str, args)
            # XXX we should print the result from resultspec too,
            # but it's not obvious how to do that
            line = '%5d |  %-20s %s' % (startpc, opname, ', '.join(args))
            print >> file, line.rstrip()
        elif isinstance(arg, codewriter.label):
            if src.pc not in noblankline:    # no duplicate blank lines
                print >> file, '%5s |' % ''
                noblankline[src.pc] = True
            src.index += 1
        else:
            assert 0, "unexpected object: %r" % (arg,)

    if src.pc != len(jitcode.code):
        print >> file, 'WARNING: the pc column is bogus! fix dump.py!'
