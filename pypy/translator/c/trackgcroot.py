#! /usr/bin/env python

import re, sys, os

r_functionstart = re.compile(r"\t.type\s+(\w+),\s*[@]function\s*$")
r_functionend   = re.compile(r"\t.size\s+\w+,\s*[.]-\w+\s*$")
r_label         = re.compile(r"([.]?\w+)[:]\s*$")
r_insn          = re.compile(r"\t([a-z]\w*)\s")
r_jump          = re.compile(r"\tj\w+\s+([.]?\w+)\s*$")
OPERAND         =            r"[\w$%-+]+(?:[(][\w%,]+[)])?|[(][\w%,]+[)]"
r_unaryinsn     = re.compile(r"\t[a-z]\w*\s+("+OPERAND+")\s*$")
r_binaryinsn    = re.compile(r"\t[a-z]\w*\s+("+OPERAND+"),\s*("+OPERAND+")\s*$")
r_gcroot_marker = re.compile(r"\t/[*](STORE|LOAD) GCROOT ")
r_gcroot_op     = re.compile(r"\t/[*](STORE|LOAD) GCROOT (\d*)[(]%esp[)][*]/\s*$")

# for sanity-checking, %esp should only appear as a way to access locals,
# i.e. inside parenthesis, except if explicitly recognized otherwise
r_esp_outside_paren = re.compile(r"(.+[)])?[^(]*[%]esp")


class GcRootTracker(object):

    def __init__(self):
        self.gcmaptable = []

    def dump(self, output):
        pass

    def process(self, iterlines, newfile):
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
                self.process_function(functionlines, newfile)
                functionlines = None

    def process_function(self, lines, newfile):
        tracker = FunctionGcRootTracker(lines)
        print >> sys.stderr, tracker.funcname
        self.gcmaptable.extend(tracker.computegcmaptable())
        newfile.writelines(tracker.lines)


class FunctionGcRootTracker(object):
    VISIT_OPERATION = {}

    def __init__(self, lines):
        match = r_functionstart.match(lines[0])
        self.funcname = match.group(1)
        self.lines = lines

    def computegcmaptable(self):
        self.findlabels()
        self.calls = {}         # {label_after_call: state}
        self.missing_labels_after_call = []
        self.follow_control_flow()
        for label, state in self.calls.values():
            print >> sys.stderr, label, '\t', state
        self.table = []
        #xxx
        self.extend_calls_with_labels()
        return self.table

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

    def getstate(self):
        gcroots = self.gcroots.keys()
        gcroots.sort()
        return (self.framesize,) + tuple(gcroots)

    def propagate_state_to(self, lin):
        state = self.getstate()
        if self.states[lin] is None:
            self.states[lin] = state
            self.pending.append(lin)
        else:
            assert self.states[lin] == state

    def follow_basic_block(self, lin):
        state = self.states[lin]
        self.framesize = state[0]
        self.gcroots = dict.fromkeys(state[1:])
        line = '?'
        try:
            while 1:
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
                    self.propagate_state_to(lin+1)
                    break
                elif r_gcroot_marker.match(line):
                    self.handle_gcroot_marker(line)
                lin += 1
        except LeaveBasicBlock:
            pass
        except Exception, e:
            print >> sys.stderr, '*'*60
            print >> sys.stderr, "%s while processing line:" % (
                e.__class__.__name__,)
            print >> sys.stderr, line
            raise

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

    def visit_ret(self, line):
        raise LeaveBasicBlock

    def visit_j(self, line):
        raise UnrecognizedOperation(line)

    def visit_jmp(self, line):
        try:
            self.conditional_jump(line)
        except KeyError:
            # label not found: check if it's a tail-call turned into a jump
            match = r_unaryinsn.match(line)
            target = match.group(1)
            assert not target.startswith('.')
        raise LeaveBasicBlock

    def conditional_jump(self, line):
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

    def visit_call(self, line):
        match = r_unaryinsn.match(line)
        target = match.group(1)
        if target == "abort":
            raise LeaveBasicBlock
        nextline = self.lines[self.currentlinenum+1]
        match = r_label.match(nextline)
        if match and not match.group(1).startswith('.'):
            label = match.group(1)
        else:
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


class LeaveBasicBlock(Exception):
    pass

class UnrecognizedOperation(Exception):
    pass


if __name__ == '__main__':
    tracker = GcRootTracker()
    for fn in sys.argv[1:]:
        tmpfn = fn + '.TMP'
        f = open(fn, 'r')
        g = open(tmpfn, 'w')
        tracker.process(f, g)
        f.close()
        g.close()
        os.unlink(fn)
        os.rename(tmpfn, fn)
    tracker.dump(sys.stdout)
