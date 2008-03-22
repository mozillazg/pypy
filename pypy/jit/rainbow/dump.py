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

    def getjitcode(self):
        return self.jitcode

    def load_2byte(self):
        return self.get(int, 2)

    def load_bool(self):
        return self.get(bool, 1)

    def get_greenarg(self):
        i = self.load_2byte()
        if i % 2:
            return self.jitcode.constants[i // 2]
        return CustomRepr('g%d' % (i // 2))

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
        if keydescnum == 0:
            return None
        else:
            keydesc = self.jitcode.keydescs[keydescnum - 1]
            return keydesc

    def load_4byte(self):     # for jump targets
        tlbl = self.get(codewriter.tlabel, 4)
        return 'pc: %d' % self.labelpos[tlbl.name]

    def red_result(self, val):
        pass

    def green_result(self, val):
        pass

    def green_result_from_red(self, val):
        pass


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

            args = []
            def wrapper_callback(src, *newargs):
                args.extend(newargs)
            opimpl.argspec(wrapper_callback)(src)

            args = map(str, args)

            comments = []
            while (not src.finished() and isinstance(src.peek(), str)
                   and src.peek().startswith('#')):
                # comment, used to tell where the result of the previous
                # operation goes
                comments.append(src.get(str, 0)[1:].strip())

            if startpc == 0:
                startpc = 'pc: 0'
            line = '%5s |  %-20s %-16s %s' % (startpc, opname,
                                              ', '.join(args),
                                              ', '.join(comments))
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
