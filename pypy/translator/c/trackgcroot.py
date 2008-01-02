#! /usr/bin/env python

import re, sys, os

r_functionstart = re.compile(r"\t.type\s+(\w+),\s*[@]function\s*$")
r_functionend   = re.compile(r"\t.size\s+(\w+),\s*[.]-(\w+)\s*$")
r_label         = re.compile(r"([.]?\w+)[:]\s*$")
r_globl         = re.compile(r"\t[.]globl\t(\w+)\s*$")
r_insn          = re.compile(r"\t([a-z]\w*)\s")
r_jump          = re.compile(r"\tj\w+\s+([.]?\w+)\s*$")
OPERAND         =            r"[-\w$%+.:@]+(?:[(][\w%,]+[)])?|[(][\w%,]+[)]"
r_unaryinsn     = re.compile(r"\t[a-z]\w*\s+("+OPERAND+")\s*$")
r_unaryinsn_star= re.compile(r"\t[a-z]\w*\s+([*]"+OPERAND+")\s*$")
r_jmp_switch    = re.compile(r"\tjmp\t[*]([.]?\w+)[(]")
r_jmptable_item = re.compile(r"\t.long\t([.]?\w+)\s*$")
r_jmptable_end  = re.compile(r"\t.text\s*$")
r_binaryinsn    = re.compile(r"\t[a-z]\w*\s+("+OPERAND+"),\s*("+OPERAND+")\s*$")
LOCALVAR        = r"%eax|%edx|%ecx|%ebx|%esi|%edi|%ebp|\d*[(]%esp[)]"
r_gcroot_marker = re.compile(r"\t/[*] GCROOT ("+LOCALVAR+") [*]/")
r_localvar      = re.compile(LOCALVAR)
r_localvar_esp  = re.compile(r"(\d*)[(]%esp[)]")

# for sanity-checking, %esp should only appear as a way to access locals,
# i.e. inside parenthesis, except if explicitly recognized otherwise
r_esp_outside_paren = re.compile(r"(.+[)])?[^(]*[%]esp")


class GcRootTracker(object):

    def __init__(self, verbose=False):
        self.gcmaptable = []
        self.verbose = verbose

    def dump(self, output):
        shapes = {}
        print >> output, '\t.data'
        print >> output, '\t.align\t4'
        print >> output, '\t.globl\t__gcmapstart'
        print >> output, '__gcmapstart:'
        for label, state in self.gcmaptable:
            if state not in shapes:
                lst = ['__gcmap_shape']
                for n in state:
                    if n < 0:
                        n = 'minus%d' % (-n,)
                    lst.append(str(n))
                shapes[state] = '_'.join(lst)
            print >> output, '\t.long\t%s' % (label,)
            print >> output, '\t.long\t%s' % (shapes[state],)
        print >> output, '\t.globl\t__gcmapend'
        print >> output, '__gcmapend:'
        print >> output, '\t.section\t.rodata'
        print >> output, '\t.align\t4'
        keys = shapes.keys()
        keys.sort()
        for state in keys:
            print >> output, '%s:' % (shapes[state],)
            print >> output, '\t.long\t%d' % (state[0],)      # frame size
            print >> output, '\t.long\t%d' % (len(state)-1,)  # gcroot count
            for p in state[1:]:
                print >> output, '\t.long\t%d' % (p,)         # gcroots

    def process(self, iterlines, newfile, entrypoint='main', filename='?'):
        functionlines = None
        for line in iterlines:
            if r_functionstart.match(line):
                assert functionlines is None, (
                    "missed the end of the previous function")
                functionlines = []
            if functionlines is not None:
                functionlines.append(line)
            else:
                newfile.write(line)
            if r_functionend.match(line):
                assert functionlines is not None, (
                    "missed the start of the current function")
                self.process_function(functionlines, newfile, entrypoint,
                                      filename)
                functionlines = None

    def process_function(self, lines, newfile, entrypoint, filename):
        tracker = FunctionGcRootTracker(lines)
        if tracker.funcname == entrypoint:
            tracker.can_use_frame_pointer = True
        if self.verbose:
            print >> sys.stderr, '[trackgcroot:%s] %s' % (filename,
                                                          tracker.funcname)
        table = tracker.computegcmaptable()
        #if self.verbose:
        #    for label, state in table:
        #        print >> sys.stderr, label, '\t', state
        if tracker.can_use_frame_pointer:
            # XXX for now we have no logic to track the gc roots of
            # functions using %ebp
            for label, state in table:
                assert len(state) == 1, (
                    "XXX for now the entry point should not have any gc roots")
        if tracker.funcname == entrypoint:
            table = [(label, (-1,)) for label, _ in table]
            # ^^^ we set the framesize of the entry point to -1 as a marker
            # (the code in llvmgcroot.py actually takes any odd-valued number
            # as marker.)
        self.gcmaptable.extend(table)
        newfile.writelines(tracker.lines)


class FunctionGcRootTracker(object):

    def __init__(self, lines):
        match = r_functionstart.match(lines[0])
        self.funcname = match.group(1)
        match = r_functionend.match(lines[-1])
        assert self.funcname == match.group(1)
        assert self.funcname == match.group(2)
        self.lines = lines
        self.inconsistent_state = {}
        self.can_use_frame_pointer = False      # unless changed by caller

    def computegcmaptable(self):
        self.findlabels()
        self.parse_instructions()
        self.findframesize()
        self.fixlocalvars()
        self.trackgcroots()
        self.dump()
        xxx
        self.follow_control_flow()
        table = self.gettable()
        self.extend_calls_with_labels()
        return table

    def gettable(self):
        "Returns a list [(label_after_call, (framesize, gcroot0, gcroot1,..))]"
        table = self.calls.items()
        table.sort()   # by line number
        table = [value for key, value in table]
        return table

    def findlabels(self):
        self.labels = {}
        for i, line in enumerate(self.lines):
            match = r_label.match(line)
            if match:
                label = match.group(1)
                assert label not in self.labels, "duplicate label"
                self.labels[label] = i

    def extend_calls_with_labels(self):
        self.missing_labels_after_call.sort()
        self.missing_labels_after_call.reverse()
        for linenum, label in self.missing_labels_after_call:
            self.lines.insert(linenum, '%s:\n' % (label,))
            self.lines.insert(linenum, '\t.globl\t%s\n' % (label,))

    def parse_instructions(self):
        self.insns = [InsnFunctionStart()]
        self.linenum = 0
        in_APP = False
        for lin in range(1, len(self.lines)):
            self.linenum = lin
            insn = no_op
            line = self.lines[lin]
            match = r_insn.match(line)
            if match:
                if not in_APP:
                    insn = match.group(1)
                    meth = getattr(self, 'visit_' + insn)
                    insn = meth(line)
            elif r_gcroot_marker.match(line):
                insn = self.handle_gcroot_marker(line)
            elif line == '#APP\n':
                in_APP = True
            elif line == '#NO_APP\n':
                in_APP = False
            self.insns.append(insn)
        del self.linenum

    def findframesize(self):
        self.framesize = {0: 0}

        def walker(lin, insn, size_delta):
            check = deltas.setdefault(lin, size_delta)
            assert check == size_delta, (
                "inconsistent frame size at function line %d" % (lin,))
            if isinstance(insn, InsnStackAdjust):
                size_delta -= insn.delta
            if lin not in self.framesize:
                yield size_delta   # continue walking backwards

        for lin, insn in enumerate(self.insns):
            if insn.requestgcroots():
                deltas = {}
                self.walk_instructions_backwards(walker, lin, 0)
                size_at_insn = []
                for n in deltas:
                    if n in self.framesize:
                        size_at_insn.append(self.framesize[n] + deltas[n])
                assert len(size_at_insn) > 0, (
                    "cannot reach the start of the function??")
                size_at_insn = size_at_insn[0]
                for n in deltas:
                    size_at_n = size_at_insn - deltas[n]
                    check = self.framesize.setdefault(n, size_at_n)
                    assert check == size_at_n, (
                        "inconsistent frame size at function line %d" % (n,))

    def fixlocalvars(self):
        for lin, insn in enumerate(self.insns):
            if lin in self.framesize:
                for name in insn._locals_:
                    localvar = getattr(insn, name)
                    match = r_localvar_esp.match(localvar)
                    if match:
                        ofs_from_esp = int(match.group(1) or '0')
                        localvar = ofs_from_esp - self.framesize[lin]
                        assert localvar != 0    # that's the return address
                        setattr(insn, name, localvar)

    def trackgcroots(self):

        def walker(lin, insn, loc):
            source = insn.source_of(loc, tag)
            if isinstance(source, Value):
                pass   # done
            else:
                yield source

        for lin, insn in enumerate(self.insns):
            for loc, tag in insn.requestgcroots().items():
                self.walk_instructions_backwards(walker, lin, loc)

    def dump(self):
        for n, insn in enumerate(self.insns):
            try:
                size = self.framesize[n]
            except (AttributeError, KeyError):
                size = '?'
            print '%4s  %s' % (size, insn)

    def walk_instructions_backwards(self, walker, initial_line, initial_state):
        pending = []
        seen = {}
        def schedule(line, state):
            assert 0 <= line < len(self.insns)
            key = line, state
            if key not in seen:
                seen[key] = True
                pending.append(key)
        schedule(initial_line, initial_state)
        while pending:
            line, state = pending.pop()
            for prevstate in walker(line, self.insns[line], state):
                schedule(line - 1, prevstate)

    def follow_control_flow(self):
        # 'states' is a list [(framesize, gcroot0, gcroot1, gcroot2...)]
        self.states = [None] * len(self.lines)
        self.pending = []
        self.framesize = 0
        self.gcroots = {}
        self.propagate_state_to(1)
        while self.pending:
            lin = self.pending.pop()
            self.follow_basic_block(lin)
        self.check_all_calls_seen()

    def getstate(self):
        if self.gcroots is Bogus:
            gcroots = ()
        else:
            gcroots = self.gcroots.keys()
            gcroots.sort()
        return (self.framesize,) + tuple(gcroots)

    def propagate_state_to(self, lin):
        state = self.getstate()
        if self.states[lin] is None:
            self.states[lin] = state
            self.pending.append(lin)
        elif self.states[lin] != state:
            if lin not in self.inconsistent_state:
                self.inconsistent_state[lin] = (self.states[lin], state)
                raise ReflowCompletely

    def follow_basic_block(self, lin):
        state = self.states[lin]
        self.framesize = state[0]
        self.gcroots = dict.fromkeys(state[1:])
        if lin in self.inconsistent_state:  # in case of inconsistent gcroots,
            self.framesize = Bogus          # assume that we're about to leave
        if self.framesize is Bogus:         # the function or fail an assert
            self.gcroots = Bogus
        line = '?'
        self.in_APP = False
        while 1:
            try:
                self.currentlinenum = lin
                line = self.lines[lin]
                match = r_insn.match(line)
                if match:
                    insn = match.group(1)
                    try:
                        meth = self.VISIT_OPERATION[insn]
                    except KeyError:
                        meth = self.find_visitor(insn)
                    meth(self, line)
                elif r_label.match(line):
                    if not self.in_APP:    # ignore labels inside #APP/#NO_APP
                        self.propagate_state_to(lin+1)
                    break
                elif r_gcroot_marker.match(line):
                    self.handle_gcroot_marker(line)
                elif line == '#APP\n':
                    self.in_APP = True
                elif line == '#NO_APP\n':
                    self.in_APP = False
                lin += 1
            except LeaveBasicBlock:
                if self.in_APP:  # ignore control flow inside #APP/#NO_APP
                    lin += 1
                    continue
                break
            except UnrecognizedOperation:
                if self.in_APP:  # ignore strange ops inside #APP/#NO_APP
                    lin += 1
                    continue
                raise
            except ReflowCompletely:
                raise
            except Exception, e:
                print >> sys.stderr, '*'*60
                print >> sys.stderr, "%s while processing line:" % (
                    e.__class__.__name__,)
                print >> sys.stderr, line
                raise

    def check_all_calls_seen(self):
        for i, line in enumerate(self.lines):
            match = r_insn.match(line)
            if match:
                insn = match.group(1)
                if insn == 'call':
                    assert i in self.calls or i in self.ignore_calls, (
                        "unreachable call!" + line)

    def handle_gcroot_marker(self, line):
        match = r_gcroot_marker.match(line)
        loc = match.group(1)
        return InsnGCROOT(loc)

    def visit_addl(self, line, sign=+1):
        match = r_binaryinsn.match(line)
        target = match.group(2)
        if target == '%esp':
            count = match.group(1)
            assert count.startswith('$')
            return InsnStackAdjust(sign * int(count[1:]))
        elif r_localvar.match(target):
            return InsnSetLocal(Value(), target)
        else:
            raise UnrecognizedOperation(line)

    def visit_subl(self, line):
        return self.visit_addl(line, sign=-1)

    def visit_movl(self, line):
        match = r_binaryinsn.match(line)
        source = match.group(1)
        target = match.group(2)
        if r_localvar.match(target):
            if r_localvar.match(source):
                return InsnCopyLocal(source, target)
            else:
                return InsnSetLocal(Value(), target)
        elif target == '%esp':
            raise UnrecognizedOperation
        else:
            return no_op

    def visit_ret(self, line):
        return InsnRet()

    def visit_jmp(self, line):
        xxx
        if self.in_APP:
            return       # ignore jumps inside a #APP/#NO_APP block
        match = r_jmp_switch.match(line)
        if match:
            # this is a jmp *Label(%index), used for table-based switches.
            # Assume that the table is just a list of lines looking like
            # .long LABEL or .long 0, ending in a .text.
            tablelabel = match.group(1)
            tablelin = self.labels[tablelabel] + 1
            while not r_jmptable_end.match(self.lines[tablelin]):
                match = r_jmptable_item.match(self.lines[tablelin])
                label = match.group(1)
                if label != '0':
                    targetlin = self.labels[label]
                    self.propagate_state_to(targetlin)
                tablelin += 1
            raise LeaveBasicBlock
        if r_unaryinsn_star.match(line):
            # that looks like an indirect tail-call.
            raise LeaveBasicBlock
        try:
            self.conditional_jump(line)
        except KeyError:
            # label not found: check if it's a tail-call turned into a jump
            match = r_unaryinsn.match(line)
            target = match.group(1)
            assert not target.startswith('.')
        raise LeaveBasicBlock

    def conditional_jump(self, line):
        xxx
        if self.in_APP:
            return       # ignore jumps inside a #APP/#NO_APP block
        match = r_jump.match(line)
        label = match.group(1)
        targetlin = self.labels[label]
        self.propagate_state_to(targetlin)

    visit_je = conditional_jump
    visit_jne = conditional_jump
    visit_jg = conditional_jump
    visit_jge = conditional_jump
    visit_jl = conditional_jump
    visit_jle = conditional_jump
    visit_ja = conditional_jump
    visit_jae = conditional_jump
    visit_jb = conditional_jump
    visit_jbe = conditional_jump
    visit_jp = conditional_jump
    visit_jnp = conditional_jump
    visit_js = conditional_jump
    visit_jns = conditional_jump
    visit_jo = conditional_jump
    visit_jno = conditional_jump

    def visit_call(self, line):
        match = r_unaryinsn.match(line)
        if match is None:
            assert r_unaryinsn_star.match(line)   # indirect call
        else:
            target = match.group(1)
            if target in FUNCTIONS_NOT_RETURNING:
                return InsnStop()
        return InsnCall()

    def visit_pypygetframeaddress(self, line):
        xxx
        # this is a pseudo-instruction that is emitted to find the first
        # frame address on the stack.  We cannot just use
        # __builtin_frame_address(0) - apparently, gcc thinks it can
        # return %ebp even if -fomit-frame-pointer is specified, which
        # doesn't work.
        match = r_unaryinsn.match(line)
        reg = match.group(1)
        newline = '\tleal\t%d(%%esp), %s\t/* pypygetframeaddress */\n' % (
            self.framesize-4, reg)
        self.lines[self.currentlinenum] = newline


class UnrecognizedOperation(Exception):
    pass


class Value(object):
    Count = 0
    def __repr__(self):
        try:
            n = self.n
        except AttributeError:
            n = self.n = Value.Count
            Value.Count += 1
        return '<Value %d>' % n

class Insn(object):
    _args_ = []
    _locals_ = []
    def __repr__(self):
        return '%s(%s)' % (self.__class__.__name__,
                           ', '.join([str(getattr(self, name))
                                      for name in self._args_]))
    def requestgcroots(self):
        return {}

    def source_of(self, localvar, tag):
        return localvar

class InsnFunctionStart(Insn):
    def __init__(self):
        self.arguments = {}
        for reg in CALLEE_SAVE_REGISTERS:
            self.arguments[reg] = Value()
    def source_of(self, localvar, tag):
        if localvar not in self.arguments:
            assert isinstance(localvar, int) and localvar > 0, (
                "must come from an argument to the function, got %r" %
                (localvar,))
            self.arguments[localvar] = Value()
        return self.arguments[localvar]

class NoOp(Insn):
    pass
no_op = NoOp()

class InsnSetLocal(Insn):
    _args_ = ['value', 'target']
    _locals_ = ['target']
    def __init__(self, value, target):
        assert value is None or isinstance(value, Value)
        self.value = value
        self.target = target
    def source_of(self, localvar, tag):
        if localvar == self.target:
            return self.value
        return localvar

class InsnCopyLocal(Insn):
    _args_ = ['source', 'target']
    _locals_ = ['source', 'target']
    def __init__(self, source, target):
        self.source = source
        self.target = target
    def source_of(self, localvar, tag):
        if localvar == self.target:
            return self.source
        return localvar

class InsnStackAdjust(Insn):
    _args_ = ['delta']
    def __init__(self, delta):
        assert delta % 4 == 0
        self.delta = delta

class InsnStop(Insn):
    pass

class InsnRet(InsnStop):
    def requestgcroots(self):
        return dict(zip(CALLEE_SAVE_REGISTERS, CALLEE_SAVE_REGISTERS))

class InsnCall(Insn):
    _args_ = ['gcroots']
    def __init__(self):
        # 'gcroots' is a dict built by side-effect during the call to
        # FunctionGcRootTracker.trackgcroots().  Its meaning is as follows:
        # the keys are the location that contain gc roots (either register
        # names like '%esi', or negative integer offsets relative to the end
        # of the function frame).  The value corresponding to a key is the
        # "tag", which is None for a normal gc root, or else the name of a
        # callee-saved register.  In the latter case it means that this is
        # only a gc root if the corresponding register in the caller was
        # really containing a gc pointer.  A typical example:
        #
        #     InsnCall({'%ebp': '%ebp', -8: '%ebx', '%esi': None})
        #
        # means that %esi is a gc root across this call; that %ebp is a
        # gc root if it was in the caller (typically because %ebp is not
        # modified at all in the current function); and that the word at 8
        # bytes before the end of the current stack frame is a gc root if
        # %ebx was a gc root in the caller (typically because the current
        # function saves and restores %ebx from there in the prologue and
        # epilogue).
        #
        self.gcroots = {}
    def source_of(self, localvar, tag):
        self.gcroots[localvar] = tag
        return localvar

class InsnGCROOT(Insn):
    _args_ = ['loc']
    def __init__(self, loc):
        self.loc = loc
    def requestgcroots(self):
        return {self.loc: None}


FUNCTIONS_NOT_RETURNING = {
    'abort': None,
    '_exit': None,
    '__assert_fail': None,
    }

CALLEE_SAVE_REGISTERS = ['%ebx', '%esi', '%edi', '%ebp']


if __name__ == '__main__':
    tracker = GcRootTracker(verbose=True)
    for fn in sys.argv[1:]:
        tmpfn = fn + '.TMP'
        f = open(fn, 'r')
        g = open(tmpfn, 'w')
        tracker.process(f, g, filename=fn)
        f.close()
        g.close()
        os.unlink(fn)
        os.rename(tmpfn, fn)
    tracker.dump(sys.stdout)
