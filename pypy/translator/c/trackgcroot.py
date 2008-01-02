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
r_gcroot_marker = re.compile(r"\t/[*](STORE|LOAD) GCROOT ")
r_gcroot_op     = re.compile(r"\t/[*](STORE|LOAD) GCROOT (\d*)[(]%esp[)][*]/\s*$")

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
    VISIT_OPERATION = {}

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
        try:
            self.calls = {}         # {label_after_call: state}
            self.ignore_calls = {}
            self.missing_labels_after_call = []
            self.follow_control_flow()
        except ReflowCompletely:
            return self.computegcmaptable()
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
        match = r_gcroot_op.match(line)
        op = match.group(1)
        position = int(match.group(2) or '0')
        assert position % 4 == 0
        if op == 'STORE':
            assert position not in self.gcroots
            self.gcroots[position] = None
        elif op == 'LOAD':
            assert position in self.gcroots
            del self.gcroots[position]
        else:
            raise UnrecognizedOperation(line)

    def find_visitor(self, insn):
        opname = insn
        while 1:
            try:
                meth = getattr(self.__class__, 'visit_' + opname)
                break
            except AttributeError:
                assert opname
                opname = opname[:-1]
        self.VISIT_OPERATION[insn] = meth
        return meth

    def visit_(self, line):
        # fallback for all operations.  By default, ignore the operation,
        # unless it appears to do something with %esp
        if not self.can_use_frame_pointer:
            if r_esp_outside_paren.match(line):
                raise UnrecognizedOperation(line)

    def visit_push(self, line):
        raise UnrecognizedOperation(line)

    def visit_pushl(self, line):
        self.framesize += 4

    def visit_pop(self, line):
        raise UnrecognizedOperation(line)

    def visit_popl(self, line):
        self.framesize -= 4
        assert self.framesize >= 0, "stack underflow"

    def visit_subl(self, line):
        match = r_binaryinsn.match(line)
        if match.group(2) == '%esp':
            count = match.group(1)
            assert count.startswith('$')
            count = int(count[1:])
            assert count % 4 == 0
            self.framesize += count

    def visit_addl(self, line):
        match = r_binaryinsn.match(line)
        if match.group(2) == '%esp':
            count = match.group(1)
            assert count.startswith('$')
            count = int(count[1:])
            assert count % 4 == 0
            self.framesize -= count
            assert self.framesize >= 0, "stack underflow"

    def visit_movl(self, line):
        match = r_binaryinsn.match(line)
        if match.group(1) == '%esp':
            # only for movl %esp, %ebp
            if match.group(2) != '%ebp':
                raise UnrecognizedOperation(line)
            assert self.can_use_frame_pointer # only if we can have a frame ptr
            assert self.framesize == 4      # only %ebp should have been pushed
        elif match.group(2) == '%esp':
            raise UnrecognizedOperation(line)

    def visit_ret(self, line):
        raise LeaveBasicBlock

    def visit_j(self, line):
        raise UnrecognizedOperation(line)

    def visit_jmp(self, line):
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
        if self.in_APP:
            self.ignore_calls[self.currentlinenum] = None
            return       # ignore calls inside a #APP/#NO_APP block
        match = r_unaryinsn.match(line)
        if match is None:
            assert r_unaryinsn_star.match(line)   # indirect call
        else:
            target = match.group(1)
            if target in FUNCTIONS_NOT_RETURNING:
                self.ignore_calls[self.currentlinenum] = None
                raise LeaveBasicBlock
        # we need a globally-declared label just after the call.
        # Reuse one if it is already there (e.g. from a previous run of this
        # script); otherwise invent a name and schedule the line insertion.
        label = None
        # this checks for a ".globl NAME" followed by "NAME:"
        match = r_globl.match(self.lines[self.currentlinenum+1])
        if match:
            label1 = match.group(1)
            match = r_label.match(self.lines[self.currentlinenum+2])
            if match:
                label2 = match.group(1)
                if label1 == label2:
                    label = label2
        if label is None:
            k = 0
            while 1:
                label = '__gcmap_IN_%s_%d' % (self.funcname, k)
                if label not in self.labels:
                    break
                k += 1
            self.labels[label] = self.currentlinenum+1
            self.missing_labels_after_call.append(
                (self.currentlinenum+1, label))
        self.calls[self.currentlinenum] = label, self.getstate()

    def visit_pypygetframeaddress(self, line):
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


class LeaveBasicBlock(Exception):
    pass

class UnrecognizedOperation(Exception):
    pass

class ReflowCompletely(Exception):
    pass

class BogusObject(object):
    pass
Bogus = BogusObject()

FUNCTIONS_NOT_RETURNING = {
    'abort': None,
    '_exit': None,
    '__assert_fail': None,
    }


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
