#! /usr/bin/env python
import autopath

import re, sys, os, random

from pypy.translator.c.gcc.instruction import *

LABEL               = r'([a-zA-Z_$.][a-zA-Z0-9_$@.]*)'
r_functionstart_elf = re.compile(r"\t.type\s+"+LABEL+",\s*[@]function\s*$")
r_functionend_elf   = re.compile(r"\t.size\s+"+LABEL+",\s*[.]-"+LABEL+"\s*$")

# darwin
r_textstart            = re.compile(r"\t.text\s*$")
# see
# http://developer.apple.com/documentation/developertools/Reference/Assembler/040-Assembler_Directives/asm_directives.html
OTHERSECTIONS = ['section', 'zerofill',
                 'const', 'static_const', 'cstring',
                 'literal4', 'literal8', 'literal16',
                 'constructor', 'desctructor',
                 'symbol_stub',
                 'data', 'static_data',
                 'non_lazy_symbol_pointer', 'lazy_symbol_pointer',
                 'dyld', 'mod_init_func', 'mod_term_func',
                 'const_data'
                 ]
r_sectionstart         = re.compile(r"\t\.("+'|'.join(OTHERSECTIONS)+").*$")
r_functionstart_darwin = re.compile(r"_(\w+):\s*$")

OFFSET_LABELS   = 2**30

# inside functions
r_label         = re.compile(LABEL+"[:]\s*$")
r_globl         = re.compile(r"\t[.]globl\t"+LABEL+"\s*$")
r_globllabel    = re.compile(LABEL+r"=[.][+]%d\s*$"%OFFSET_LABELS)
r_insn          = re.compile(r"\t([a-z]\w*)\s")
r_jmp_switch    = re.compile(r"\tjmp\t[*]"+LABEL+"[(]")
r_jmp_source    = re.compile(r"\d*[(](%[\w]+)[,)]")
r_jmptable_item = re.compile(r"\t.long\t"+LABEL+"(-\"[A-Za-z0-9$]+\")?\s*$")
r_jmptable_end  = re.compile(r"\t.text|\t.section\s+.text|\t\.align|"+LABEL)
LOCALVAR        = r"%eax|%edx|%ecx|%ebx|%esi|%edi|%ebp|\d*[(]%esp[)]"
LOCALVARFP      = LOCALVAR + r"|-?\d*[(]%ebp[)]"
r_gcroot_marker = re.compile(r"\t/[*] GCROOT ("+LOCALVARFP+") [*]/")
r_bottom_marker = re.compile(r"\t/[*] GC_STACK_BOTTOM [*]/")
r_localvarnofp  = re.compile(LOCALVAR)
r_localvarfp    = re.compile(LOCALVARFP)
r_localvar_esp  = re.compile(r"(\d*)[(]%esp[)]")
r_localvar_ebp  = re.compile(r"(-?\d*)[(]%ebp[)]")

class FunctionGcRootTracker(object):

    @classmethod
    def init_regexp(cls):
        cls.r_unaryinsn     = re.compile(r"\t[a-z]\w*\s+("+cls.OPERAND+")\s*$")
        cls.r_unaryinsn_star= re.compile(r"\t[a-z]\w*\s+([*]"+cls.OPERAND+")\s*$")
        cls.r_binaryinsn    = re.compile(r"\t[a-z]\w*\s+(?P<source>"+cls.OPERAND+"),\s*(?P<target>"+cls.OPERAND+")\s*$")

        cls.r_jump          = re.compile(r"\tj\w+\s+"+cls.LABEL+"\s*$")

    def __init__(self, funcname, lines, filetag=0):
        self.funcname = funcname
        self.lines = lines
        self.uses_frame_pointer = False
        self.r_localvar = r_localvarnofp
        self.filetag = filetag
        # a "stack bottom" function is either main() or a callback from C code
        self.is_stack_bottom = False

    def computegcmaptable(self, verbose=0):
        self.findlabels()
        self.parse_instructions()
        try:
            if not self.list_call_insns():
                return []
            self.findframesize()
            self.fixlocalvars()
            self.trackgcroots()
            self.extend_calls_with_labels()
        finally:
            if verbose > 2:
                self.dump()
        return self.gettable()

    def gettable(self):
        """Returns a list [(label_after_call, callshape_tuple)]
        See format_callshape() for more details about callshape_tuple.
        """
        table = []
        for insn in self.list_call_insns():
            if not hasattr(insn, 'framesize'):
                continue     # calls that never end up reaching a RET
            if self.is_stack_bottom:
                retaddr = LOC_NOWHERE     # end marker for asmgcroot.py
            elif self.uses_frame_pointer:
                retaddr = frameloc(LOC_EBP_BASED, 4)
            else:
                retaddr = frameloc(LOC_ESP_BASED, insn.framesize)
            shape = [retaddr]
            # the first gcroots are always the ones corresponding to
            # the callee-saved registers
            for reg in CALLEE_SAVE_REGISTERS:
                shape.append(LOC_NOWHERE)
            gcroots = []
            for localvar, tag in insn.gcroots.items():
                if isinstance(localvar, LocalVar):
                    loc = localvar.getlocation(insn.framesize,
                                               self.uses_frame_pointer)
                else:
                    assert localvar in REG2LOC, "%s: %s" % (self.funcname,
                                                            localvar)
                    loc = REG2LOC[localvar]
                assert isinstance(loc, int)
                if tag is None:
                    gcroots.append(loc)
                else:
                    regindex = CALLEE_SAVE_REGISTERS.index(tag)
                    shape[1 + regindex] = loc
            if LOC_NOWHERE in shape and not self.is_stack_bottom:
                reg = CALLEE_SAVE_REGISTERS[shape.index(LOC_NOWHERE) - 1]
                raise AssertionError("cannot track where register %s is saved"
                                     % (reg,))
            gcroots.sort()
            shape.extend(gcroots)
            table.append((insn.global_label, tuple(shape)))
        return table

    def findlabels(self):
        self.labels = {}      # {name: Label()}
        for lineno, line in enumerate(self.lines):
            match = r_label.match(line)
            if match:
                label = match.group(1)
                assert label not in self.labels, "duplicate label"
                self.labels[label] = Label(label, lineno)

    def append_instruction(self, insn):
        # Add the instruction to the list, and link it to the previous one.
        previnsn = self.insns[-1]
        self.insns.append(insn)

        try:
            lst = insn.previous_insns
        except AttributeError:
            lst = insn.previous_insns = []
        if not isinstance(previnsn, InsnStop):
            lst.append(previnsn)

    def parse_instructions(self):
        self.insns = [InsnFunctionStart()]
        ignore_insns = False
        for lineno, line in enumerate(self.lines):
            self.currentlineno = lineno
            insn = []
            match = r_insn.match(line)
            if match:
                if not ignore_insns:
                    opname = match.group(1)
                    try:
                        meth = getattr(self, 'visit_' + opname)
                    except AttributeError:
                        self.find_missing_visit_method(opname)
                        meth = getattr(self, 'visit_' + opname)
                    line = line.rsplit(';', 1)[0]
                    insn = meth(line)
            elif r_gcroot_marker.match(line):
                insn = self._visit_gcroot_marker(line)
            elif r_bottom_marker.match(line):
                self.is_stack_bottom = True
            elif line == '\t/* ignore_in_trackgcroot */\n':
                ignore_insns = True
            elif line == '\t/* end_ignore_in_trackgcroot */\n':
                ignore_insns = False
            else:
                match = r_label.match(line)
                if match:
                    insn = self.labels[match.group(1)]

            if isinstance(insn, list):
                for i in insn:
                    self.append_instruction(i)
            else:
                self.append_instruction(insn)

            del self.currentlineno

    @classmethod
    def find_missing_visit_method(cls, opname):
        # only for operations that are no-ops as far as we are concerned
        prefix = opname
        while prefix not in cls.IGNORE_OPS_WITH_PREFIXES:
            prefix = prefix[:-1]
            if not prefix:
                raise UnrecognizedOperation(opname)
        setattr(cls, 'visit_' + opname, cls.visit_nop)

    def list_call_insns(self):
        return [insn for insn in self.insns if isinstance(insn, InsnCall)]

    def findframesize(self):
        # the 'framesize' attached to an instruction is the number of bytes
        # in the frame at this point.  This doesn't count the return address
        # which is the word immediately following the frame in memory.
        # The 'framesize' is set to an odd value if it is only an estimate
        # (see visit_andl()).

        def walker(insn, size_delta):
            check = deltas.setdefault(insn, size_delta)
            assert check == size_delta, (
                "inconsistent frame size at instruction %s" % (insn,))
            if isinstance(insn, InsnStackAdjust):
                size_delta -= insn.delta
            if not hasattr(insn, 'framesize'):
                yield size_delta   # continue walking backwards

        for insn in self.insns:
            if isinstance(insn, (InsnRet, InsnEpilogue, InsnGCROOT)):
                deltas = {}
                self.walk_instructions_backwards(walker, insn, 0)
                size_at_insn = []
                for insn1, delta1 in deltas.items():
                    if hasattr(insn1, 'framesize'):
                        size_at_insn.append(insn1.framesize + delta1)
                assert len(size_at_insn) > 0, (
                    "cannot reach the start of the function??")
                size_at_insn = size_at_insn[0]
                for insn1, delta1 in deltas.items():
                    size_at_insn1 = size_at_insn - delta1
                    if hasattr(insn1, 'framesize'):
                        assert insn1.framesize == size_at_insn1, (
                            "inconsistent frame size at instruction %s" %
                            (insn1,))
                    else:
                        insn1.framesize = size_at_insn1

    def fixlocalvars(self):
        def fixvar(localvar):
            if localvar is None:
                return None
            elif isinstance(localvar, (list, tuple)):
                return [fixvar(var) for var in localvar]

            match = r_localvar_esp.match(localvar)
            if match:
                if localvar == '0(%esp)': # for pushl and popl, by
                    hint = None           # default ebp addressing is
                else:                     # a bit nicer
                    hint = 'esp'
                ofs_from_esp = int(match.group(1) or '0')
                localvar = ofs_from_esp - insn.framesize
                assert localvar != 0    # that's the return address
                return LocalVar(localvar, hint=hint)
            elif self.uses_frame_pointer:
                match = r_localvar_ebp.match(localvar)
                if match:
                    ofs_from_ebp = int(match.group(1) or '0')
                    localvar = ofs_from_ebp - 4
                    assert localvar != 0    # that's the return address
                    return LocalVar(localvar, hint='ebp')
            return localvar

        for insn in self.insns:
            if not hasattr(insn, 'framesize'):
                continue
            for name in insn._locals_:
                localvar = getattr(insn, name)
                setattr(insn, name, fixvar(localvar))

    def trackgcroots(self):

        def walker(insn, loc):
            source = insn.source_of(loc, tag)
            if source is somenewvalue:
                pass   # done
            else:
                yield source

        for insn in self.insns:
            for loc, tag in insn.requestgcroots(self).items():
                self.walk_instructions_backwards(walker, insn, loc)

    def dump(self):
        for insn in self.insns:
            size = getattr(insn, 'framesize', '?')
            print >> sys.stderr, '%4s  %s' % (size, insn)

    def walk_instructions_backwards(self, walker, initial_insn, initial_state):
        pending = []
        seen = {}
        def schedule(insn, state):
            for previnsn in insn.previous_insns:
                key = previnsn, state
                if key not in seen:
                    seen[key] = True
                    pending.append(key)
        schedule(initial_insn, initial_state)
        while pending:
            insn, state = pending.pop()
            for prevstate in walker(insn, state):
                schedule(insn, prevstate)

    def extend_calls_with_labels(self):
        # walk backwards, because inserting the global labels in self.lines
        # is going to invalidate the lineno of all the InsnCall objects
        # after the current one.
        for call in self.list_call_insns()[::-1]:
            if hasattr(call, 'framesize'):
                self.create_global_label(call)

    def create_global_label(self, call):
        # we need a globally-declared label just after the call.
        # Reuse one if it is already there (e.g. from a previous run of this
        # script); otherwise invent a name and add the label to tracker.lines.
        label = None
        # this checks for a ".globl NAME" followed by "NAME:"
        match = r_globl.match(self.lines[call.lineno+1])
        if match:
            label1 = match.group(1)
            match = r_globllabel.match(self.lines[call.lineno+2])
            if match:
                label2 = match.group(1)
                if label1 == label2:
                    label = label2
        if label is None:
            k = call.lineno
            while 1:
                label = '__gcmap_%s__%s_%d' % (self.filetag, self.funcname, k)
                if label not in self.labels:
                    break
                k += 1
            self.labels[label] = None
            # These global symbols are not directly labels pointing to the
            # code location because such global labels in the middle of
            # functions confuse gdb.  Instead, we add to the global symbol's
            # value a big constant, which is subtracted again when we need
            # the original value for gcmaptable.s.  That's a hack.
            self.lines.insert(call.lineno+1, '%s=.+%d\n' % (label,
                                                            OFFSET_LABELS))
            self.lines.insert(call.lineno+1, '\t.globl\t%s\n' % (label,))
        call.global_label = label

    # ____________________________________________________________

    def _visit_gcroot_marker(self, line):
        match = r_gcroot_marker.match(line)
        loc = match.group(1)
        return InsnGCROOT(loc)

    def visit_nop(self, line):
        return []

    IGNORE_OPS_WITH_PREFIXES = dict.fromkeys([
        'cmp', 'test', 'set', 'sahf', 'cltd', 'cld', 'std',
        'rep', 'movs', 'lods', 'stos', 'scas', 'cwtl', 'prefetch',
        # floating-point operations cannot produce GC pointers
        'f',
        'cvt', 'ucomi', 'subs', 'subp' , 'adds', 'addp', 'xorp', 'movap',
        'movd', 'sqrtsd',
        'mins', 'minp', 'maxs', 'maxp', # sse2
        # arithmetic operations should not produce GC pointers
        'inc', 'dec', 'not', 'neg', 'or', 'and', 'sbb', 'adc',
        'shl', 'shr', 'sal', 'sar', 'rol', 'ror', 'mul', 'imul', 'div', 'idiv',
        'bswap', 'bt',
        # zero-extending moves should not produce GC pointers
        'movz',
        ])

    visit_movb = visit_nop
    visit_movw = visit_nop
    visit_addb = visit_nop
    visit_addw = visit_nop
    visit_subb = visit_nop
    visit_subw = visit_nop
    visit_xorb = visit_nop
    visit_xorw = visit_nop

    def visit_addl(self, line, sign=+1):
        match = self.r_binaryinsn.match(line)
        source = match.group("source")
        target = match.group("target")
        if target == self.ESP:
            count = self.extract_immediate(source)
            if count is None:
                # strange instruction - I've seen 'subl %eax, %esp'
                return InsnCannotFollowEsp()
            return InsnStackAdjust(sign * count)
        elif self.r_localvar.match(target):
            return InsnSetLocal(target, [source, target])
        else:
            return []

    def visit_subl(self, line):
        return self.visit_addl(line, sign=-1)

    def unary_insn(self, line):
        match = self.r_unaryinsn.match(line)
        target = match.group(1)
        if self.r_localvar.match(target):
            return InsnSetLocal(target)
        else:
            return []

    def binary_insn(self, line):
        match = self.r_binaryinsn.match(line)
        if not match:
            raise UnrecognizedOperation(line)
        source = match.group("source")
        target = match.group("target")
        if self.r_localvar.match(target):
            return InsnSetLocal(target, [source])
        elif target == self.ESP:
            raise UnrecognizedOperation(line)
        else:
            return []

    visit_xorl = binary_insn   # used in "xor reg, reg" to create a NULL GC ptr
    visit_orl = binary_insn
    visit_cmove = binary_insn
    visit_cmovne = binary_insn
    visit_cmovg = binary_insn
    visit_cmovge = binary_insn
    visit_cmovl = binary_insn
    visit_cmovle = binary_insn
    visit_cmova = binary_insn
    visit_cmovae = binary_insn
    visit_cmovb = binary_insn
    visit_cmovbe = binary_insn
    visit_cmovp = binary_insn
    visit_cmovnp = binary_insn
    visit_cmovs = binary_insn
    visit_cmovns = binary_insn
    visit_cmovo = binary_insn
    visit_cmovno = binary_insn

    def visit_andl(self, line):
        match = self.r_binaryinsn.match(line)
        target = match.group("target")
        if target == self.ESP:
            # only for  andl $-16, %esp  used to align the stack in main().
            # The exact amount of adjutment is not known yet, so we use
            # an odd-valued estimate to make sure the real value is not used
            # elsewhere by the FunctionGcRootTracker.
            return InsnCannotFollowEsp()
        else:
            return self.binary_insn(line)

    def visit_leal(self, line):
        match = self.r_binaryinsn.match(line)
        target = match.group("target")
        if target == self.ESP:
            # only for  leal -12(%ebp), %esp  in function epilogues
            source = match.group("source")
            match = r_localvar_ebp.match(source)
            if match:
                if not self.uses_frame_pointer:
                    raise UnrecognizedOperation('epilogue without prologue')
                ofs_from_ebp = int(match.group(1) or '0')
                assert ofs_from_ebp <= 0
                framesize = 4 - ofs_from_ebp
            else:
                match = r_localvar_esp.match(source)
                # leal 12(%esp), %esp
                if match:
                    return InsnStackAdjust(int(match.group(1)))

                framesize = None    # strange instruction
            return InsnEpilogue(framesize)
        else:
            return self.binary_insn(line)

    def insns_for_copy(self, source, target):
        if source == self.ESP or target == self.ESP:
            raise UnrecognizedOperation('%s -> %s' % (source, target))
        elif self.r_localvar.match(target):
            if self.r_localvar.match(source):
                return [InsnCopyLocal(source, target)]
            else:
                return [InsnSetLocal(target, [source])]
        else:
            return []

    def visit_movl(self, line):
        match = self.r_binaryinsn.match(line)
        source = match.group("source")
        target = match.group("target")
        if source == self.ESP and target == '%ebp':
            return self._visit_prologue()
        elif source == '%ebp' and target == self.ESP:
            return self._visit_epilogue()
        return self.insns_for_copy(source, target)

    def visit_pushl(self, line):
        match = self.r_unaryinsn.match(line)
        source = match.group(1)
        return [InsnStackAdjust(-4)] + self.insns_for_copy(source, '0(%esp)')

    def visit_pushw(self, line):
        return [InsnStackAdjust(-2)]   # rare but not impossible

    def _visit_pop(self, target):
        return self.insns_for_copy('0(%esp)', target) + [InsnStackAdjust(+4)]

    def visit_popl(self, line):
        match = self.r_unaryinsn.match(line)
        target = match.group(1)
        return self._visit_pop(target)

    def _visit_prologue(self):
        # for the prologue of functions that use %ebp as frame pointer
        self.uses_frame_pointer = True
        self.r_localvar = r_localvarfp
        return [InsnPrologue()]

    def _visit_epilogue(self):
        if not self.uses_frame_pointer:
            raise UnrecognizedOperation('epilogue without prologue')
        return [InsnEpilogue(4)]

    def visit_leave(self, line):
        return self._visit_epilogue() + self._visit_pop('%ebp')

    def visit_ret(self, line):
        return InsnRet()

    def visit_jmp(self, line):
        tablelabels = []
        match = r_jmp_switch.match(line)
        if match:
            # this is a jmp *Label(%index), used for table-based switches.
            # Assume that the table is just a list of lines looking like
            # .long LABEL or .long 0, ending in a .text or .section .text.hot.
            tablelabels.append(match.group(1))
        elif self.r_unaryinsn_star.match(line):
            # maybe a jmp similar to the above, but stored in a
            # registry:
            #     movl L9341(%eax), %eax
            #     jmp *%eax
            operand = self.r_unaryinsn_star.match(line).group(1)[1:]
            def walker(insn, locs):
                sources = []
                for loc in locs:
                    for s in insn.all_sources_of(loc):
                        # if the source looks like 8(%eax,%edx,4)
                        # %eax is the real source, %edx is an offset.
                        match = r_jmp_source.match(s)
                        if match and not r_localvar_esp.match(s):
                            sources.append(match.group(1))
                        else:
                            sources.append(s)
                for source in sources:
                    label_match = re.compile(LABEL).match(source)
                    if label_match:
                        tablelabels.append(label_match.group(0))
                        return
                yield tuple(sources)
            insn = InsnStop()
            insn.previous_insns = [self.insns[-1]]
            self.walk_instructions_backwards(walker, insn, (operand,))

            # Remove probable tail-calls
            tablelabels = [label for label in tablelabels
                           if label in self.labels]
        assert len(tablelabels) <= 1
        if tablelabels:
            tablelin = self.labels[tablelabels[0]].lineno + 1
            while not r_jmptable_end.match(self.lines[tablelin]):
                match = r_jmptable_item.match(self.lines[tablelin])
                if not match:
                    raise NoPatternMatch(self.lines[tablelin])
                label = match.group(1)
                if label != '0':
                    self.register_jump_to(label)
                tablelin += 1
            return InsnStop()
        if self.r_unaryinsn_star.match(line):
            # that looks like an indirect tail-call.
            # tail-calls are equivalent to RET for us
            return InsnRet()
        try:
            self.conditional_jump(line)
        except KeyError:
            # label not found: check if it's a tail-call turned into a jump
            match = self.r_unaryinsn.match(line)
            target = match.group(1)
            assert not target.startswith('.')
            # tail-calls are equivalent to RET for us
            return InsnRet()
        return InsnStop()

    def register_jump_to(self, label):
        self.labels[label].previous_insns.append(self.insns[-1])

    def conditional_jump(self, line):
        match = self.r_jump.match(line)
        if not match:
            raise UnrecognizedOperation(line)
        label = match.group(1)
        self.register_jump_to(label)
        return []

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
    visit_jc = conditional_jump
    visit_jnc = conditional_jump

    def visit_xchgl(self, line):
        # only support the format used in VALGRIND_DISCARD_TRANSLATIONS
        # which is to use a marker no-op "xchgl %ebx, %ebx"
        match = self.r_binaryinsn.match(line)
        source = match.group("source")
        target = match.group("target")
        if source == target:
            return []
        raise UnrecognizedOperation(line)

    def visit_call(self, line):
        match = self.r_unaryinsn.match(line)
        if match is None:
            assert self.r_unaryinsn_star.match(line)   # indirect call
        else:
            target = match.group(1)
            if target in FUNCTIONS_NOT_RETURNING:
                return InsnStop()
            if sys.platform == 'win32' and target == '__alloca':
                # in functions with large stack requirements, windows
                # needs a call to _alloca(), to turn reserved pages
                # into committed memory.
                # With mingw32 gcc at least, %esp is not used before
                # this call.  So we don't bother to compute the exact
                # stack effect.
                return [InsnCannotFollowEsp()]
            if target in self.labels:
                lineoffset = self.labels[target].lineno - self.currentlineno
                if lineoffset >= 0:
                    assert  lineoffset in (1,2)
                    return [InsnStackAdjust(-4)]
        insns = [InsnCall(self.currentlineno),
                 InsnSetLocal('%eax')]      # the result is there
        if sys.platform == 'win32':
            # handle __stdcall calling convention:
            # Stack cleanup is performed by the called function,
            # Function name is decorated with "@N" where N is the stack size
            if match and '@' in target:
                insns.append(InsnStackAdjust(int(target.split('@')[1])))
        return insns


class ElfFunctionGcRootTracker(FunctionGcRootTracker):
    format = 'elf'

    ESP      = '%esp'
    OPERAND  = r'(?:[-\w$%+.:@"]+(?:[(][\w%,]+[)])?|[(][\w%,]+[)])'
    LABEL    = r'([a-zA-Z_$.][a-zA-Z0-9_$@.]*)'

    def __init__(self, lines, filetag=0):
        match = r_functionstart_elf.match(lines[0])
        funcname = match.group(1)
        match = r_functionend_elf.match(lines[-1])
        assert funcname == match.group(1)
        assert funcname == match.group(2)
        super(ElfFunctionGcRootTracker, self).__init__(
            funcname, lines, filetag)

    def extract_immediate(self, value):
        if not value.startswith('$'):
            return None
        return int(value[1:])

ElfFunctionGcRootTracker.init_regexp()

class DarwinFunctionGcRootTracker(ElfFunctionGcRootTracker):
    format = 'darwin'

    def __init__(self, lines, filetag=0):
        match = r_functionstart_darwin.match(lines[0])
        funcname = '_'+match.group(1)
        FunctionGcRootTracker.__init__(self, funcname, lines, filetag)

class Mingw32FunctionGcRootTracker(DarwinFunctionGcRootTracker):
    format = 'mingw32'

class MsvcFunctionGcRootTracker(FunctionGcRootTracker):
    format = 'msvc'

    r_functionstart = re.compile(r"PUBLIC\t"+LABEL+"$")

    ESP = 'esp'

    OPERAND  = r'(?:\w+|(?:DWORD PTR )?[_\w$]*\[[-+\w0-9]+\])'
    LABEL    = r'([a-zA-Z_$.][a-zA-Z0-9_$@.]*)'

    @classmethod
    def init_regexp(cls):
        super(MsvcFunctionGcRootTracker, cls).init_regexp()
        cls.r_binaryinsn    = re.compile(r"\t[a-z]\w*\s+(?P<target>"+cls.OPERAND+"),\s*(?P<source>"+cls.OPERAND+")\s*(?:;.+)?$")
        cls.r_jump = re.compile(r"\tj\w+\s+(?:SHORT )?"+LABEL+"\s*$")

    def __init__(self, lines, filetag=0):
        match = self.r_functionstart.match(lines[0])
        funcname = match.group(1)
        super(MsvcFunctionGcRootTracker, self).__init__(
            funcname, lines, filetag)

    for name in '''
        push pop mov lea
        xor sub add
        '''.split():
        locals()['visit_' + name] = getattr(FunctionGcRootTracker,
                                            'visit_' + name + 'l')

    def extract_immediate(self, value):
        try:
            return int(value)
        except ValueError:
            return None

MsvcFunctionGcRootTracker.init_regexp()

class AssemblerParser(object):
    def __init__(self, verbose=0, shuffle=False):
        self.verbose = verbose
        self.shuffle = shuffle
        self.gcmaptable = []
        self.seen_main = False

    def process(self, iterlines, newfile, entrypoint='main', filename='?'):
        for in_function, lines in self.find_functions(iterlines):
            if in_function:
                lines = self.process_function(lines, entrypoint, filename)
            newfile.writelines(lines)
        if self.verbose == 1:
            sys.stderr.write('\n')

    def process_function(self, lines, entrypoint, filename):
        tracker = self.FunctionGcRootTracker(
            lines, filetag=getidentifier(filename))
        is_main = tracker.funcname == entrypoint
        tracker.is_stack_bottom = is_main
        if self.verbose == 1:
            sys.stderr.write('.')
        elif self.verbose > 1:
            print >> sys.stderr, '[trackgcroot:%s] %s' % (filename,
                                                          tracker.funcname)
        table = tracker.computegcmaptable(self.verbose)
        if self.verbose > 1:
            for label, state in table:
                print >> sys.stderr, label, '\t', format_callshape(state)
        table = compress_gcmaptable(table)
        if self.shuffle and random.random() < 0.5:
            self.gcmaptable[:0] = table
        else:
            self.gcmaptable.extend(table)
        self.seen_main |= is_main
        return tracker.lines

class ElfAssemblerParser(AssemblerParser):
    format = "elf"
    FunctionGcRootTracker = ElfFunctionGcRootTracker

    @classmethod
    def find_functions(cls, iterlines):
        functionlines = []
        in_function = False
        for line in iterlines:
            if r_functionstart_elf.match(line):
                assert not in_function, (
                    "missed the end of the previous function")
                yield False, functionlines
                in_function = True
                functionlines = []
            functionlines.append(line)
            if r_functionend_elf.match(line):
                assert in_function, (
                    "missed the start of the current function")
                yield True, functionlines
                in_function = False
                functionlines = []
        assert not in_function, (
            "missed the end of the previous function")
        yield False, functionlines

class DarwinAssemblerParser(AssemblerParser):
    format = "darwin"
    FunctionGcRootTracker = DarwinFunctionGcRootTracker

    @classmethod
    def find_functions(cls, iterlines):
        functionlines = []
        in_text = False
        in_function = False
        for n, line in enumerate(iterlines):
            if r_textstart.match(line):
                assert not in_text, "unexpected repeated .text start: %d" % n
                in_text = True
            elif r_sectionstart.match(line):
                if in_function:
                    yield in_function, functionlines
                    functionlines = []
                in_text = False
                in_function = False
            elif in_text and r_functionstart_darwin.match(line):
                yield in_function, functionlines
                functionlines = []
                in_function = True
            functionlines.append(line)

        if functionlines:
            yield in_function, functionlines

    def process_function(self, lines, entrypoint, filename):
        entrypoint = '_' + entrypoint
        return super(DarwinAssemblerParser, self).process_function(
            lines, entrypoint, filename)

class Mingw32AssemblerParser(DarwinAssemblerParser):
    format = "mingw32"
    FunctionGcRootTracker = Mingw32FunctionGcRootTracker

    @classmethod
    def find_functions(cls, iterlines):
        functionlines = []
        in_text = False
        in_function = False
        for n, line in enumerate(iterlines):
            if r_textstart.match(line):
                in_text = True
            elif r_sectionstart.match(line):
                in_text = False
            elif in_text and r_functionstart_darwin.match(line):
                yield in_function, functionlines
                functionlines = []
                in_function = True
            functionlines.append(line)
        if functionlines:
            yield in_function, functionlines

class MsvcAssemblerParser(AssemblerParser):
    format = "msvc"
    FunctionGcRootTracker = MsvcFunctionGcRootTracker

PARSERS = {
    'elf': ElfAssemblerParser,
    'darwin': DarwinAssemblerParser,
    'mingw32': Mingw32AssemblerParser,
    'msvc': MsvcAssemblerParser,
    }

class GcRootTracker(object):

    def __init__(self, verbose=0, shuffle=False, format='elf'):
        self.verbose = verbose
        self.shuffle = shuffle     # to debug the sorting logic in asmgcroot.py
        self.format = format
        self.gcmaptable = []
        self.seen_main = False

    def dump_raw_table(self, output):
        print >> output, "seen_main = %d" % (self.seen_main,)
        for entry in self.gcmaptable:
            print >> output, entry

    def reload_raw_table(self, input):
        firstline = input.readline()
        assert firstline.startswith("seen_main = ")
        self.seen_main |= bool(int(firstline[len("seen_main = "):].strip()))
        for line in input:
            entry = eval(line)
            assert type(entry) is tuple
            self.gcmaptable.append(entry)

    def dump(self, output):
        assert self.seen_main
        shapes = {}
        shapelines = []
        shapeofs = 0
        def _globalname(name):
            if self.format in ('darwin', 'mingw32'):
                return '_' + name
            return name
        def _globl(name):
            print >> output, "\t.globl %s" % _globalname(name)
        def _label(name):
            print >> output, "%s:" % _globalname(name)
        def _variant(**kwargs):
            txt = kwargs[self.format]
            print >> output, "\t%s" % txt

        print >> output, "\t.text"
        _globl('pypy_asm_stackwalk')
        _variant(elf='.type pypy_asm_stackwalk, @function',
                 darwin='',
                 mingw32='')
        _label('pypy_asm_stackwalk')
        print >> output, """\
            /* See description in asmgcroot.py */
            movl   4(%esp), %edx     /* my argument, which is the callback */
            movl   %esp, %eax        /* my frame top address */
            pushl  %eax              /* ASM_FRAMEDATA[6] */
            pushl  %ebp              /* ASM_FRAMEDATA[5] */
            pushl  %edi              /* ASM_FRAMEDATA[4] */
            pushl  %esi              /* ASM_FRAMEDATA[3] */
            pushl  %ebx              /* ASM_FRAMEDATA[2] */

            /* Add this ASM_FRAMEDATA to the front of the circular linked */
            /* list.  Let's call it 'self'. */
            movl   __gcrootanchor+4, %eax  /* next = gcrootanchor->next */
            pushl  %eax                    /* self->next = next         */
            pushl  $__gcrootanchor         /* self->prev = gcrootanchor */
            movl   %esp, __gcrootanchor+4  /* gcrootanchor->next = self */
            movl   %esp, (%eax)            /* next->prev = self         */

            /* note: the Mac OS X 16 bytes aligment must be respected. */
            call   *%edx                   /* invoke the callback */

            /* Detach this ASM_FRAMEDATA from the circular linked list */
            popl   %esi                    /* prev = self->prev         */
            popl   %edi                    /* next = self->next         */
            movl   %edi, 4(%esi)           /* prev->next = next         */
            movl   %esi, (%edi)            /* next->prev = prev         */

            popl   %ebx              /* restore from ASM_FRAMEDATA[2] */
            popl   %esi              /* restore from ASM_FRAMEDATA[3] */
            popl   %edi              /* restore from ASM_FRAMEDATA[4] */
            popl   %ebp              /* restore from ASM_FRAMEDATA[5] */
            popl   %ecx              /* ignored      ASM_FRAMEDATA[6] */
            /* the return value is the one of the 'call' above, */
            /* because %eax (and possibly %edx) are unmodified  */
            ret
""".replace("__gcrootanchor", _globalname("__gcrootanchor"))
        _variant(elf='.size pypy_asm_stackwalk, .-pypy_asm_stackwalk',
                 darwin='',
                 mingw32='')
        print >> output, '\t.data'
        print >> output, '\t.align\t4'
        _globl('__gcrootanchor')
        _label('__gcrootanchor')
        print >> output, """\
            /* A circular doubly-linked list of all */
            /* the ASM_FRAMEDATAs currently alive */
            .long\t__gcrootanchor       /* prev */
            .long\t__gcrootanchor       /* next */
""".replace("__gcrootanchor", _globalname("__gcrootanchor"))
        _globl('__gcmapstart')
        _label('__gcmapstart')
        for label, state, is_range in self.gcmaptable:
            try:
                n = shapes[state]
            except KeyError:
                n = shapes[state] = shapeofs
                bytes = [str(b) for b in compress_callshape(state)]
                shapelines.append('\t/*%d*/\t.byte\t%s\n' % (
                    shapeofs,
                    ', '.join(bytes)))
                shapeofs += len(bytes)
            if is_range:
                n = ~ n
            print >> output, '\t.long\t%s-%d' % (label, OFFSET_LABELS)
            print >> output, '\t.long\t%d' % (n,)
        _globl('__gcmapend')
        _label('__gcmapend')
        _variant(elf='.section\t.rodata',
                 darwin='.const',
                 mingw32='')
        _globl('__gccallshapes')
        _label('__gccallshapes')
        output.writelines(shapelines)

    def process(self, iterlines, newfile, entrypoint='main', filename='?'):
        parser = PARSERS[format](verbose=self.verbose, shuffle=self.shuffle)
        for in_function, lines in parser.find_functions(iterlines):
            if in_function:
                lines = parser.process_function(lines, entrypoint, filename)
            newfile.writelines(lines)
        if self.verbose == 1:
            sys.stderr.write('\n')
        if self.shuffle and random.random() < 0.5:
            self.gcmaptable[:0] = parser.gcmaptable
        else:
            self.gcmaptable.extend(parser.gcmaptable)
        self.seen_main |= parser.seen_main


class UnrecognizedOperation(Exception):
    pass

class NoPatternMatch(Exception):
    pass


if sys.platform != 'win32':
    FUNCTIONS_NOT_RETURNING = {
        'abort': None,
        '_exit': None,
        '__assert_fail': None,
        '___assert_rtn': None,
        'L___assert_rtn$stub': None
        }
else:
    FUNCTIONS_NOT_RETURNING = {
        '_abort': None,
        '__exit': None,
        '__assert': None,
        '__wassert': None,
        }

# __________ debugging output __________

def format_location(loc):
    # A 'location' is a single number describing where a value is stored
    # across a call.  It can be in one of the CALLEE_SAVE_REGISTERS, or
    # in the stack frame at an address relative to either %esp or %ebp.
    # The last two bits of the location number are used to tell the cases
    # apart; see format_location().
    kind = loc & LOC_MASK
    if kind == LOC_NOWHERE:
        return '?'
    elif kind == LOC_REG:
        reg = loc >> 2
        assert 0 <= reg <= 3
        return CALLEE_SAVE_REGISTERS[reg]
    else:
        if kind == LOC_EBP_BASED:
            result = '(%ebp)'
        else:
            result = '(%esp)'
        offset = loc & ~ LOC_MASK
        if offset != 0:
            result = str(offset) + result
        return result

def format_callshape(shape):
    # A 'call shape' is a tuple of locations in the sense of format_location().
    # They describe where in a function frame interesting values are stored,
    # when this function executes a 'call' instruction.
    #
    #   shape[0] is the location that stores the fn's own return address
    #            (not the return address for the currently executing 'call')
    #   shape[1] is where the fn saved its own caller's %ebx value
    #   shape[2] is where the fn saved its own caller's %esi value
    #   shape[3] is where the fn saved its own caller's %edi value
    #   shape[4] is where the fn saved its own caller's %ebp value
    #   shape[>=5] are GC roots: where the fn has put its local GCPTR vars
    #
    assert isinstance(shape, tuple)
    assert len(shape) >= 5
    result = [format_location(loc) for loc in shape]
    return '{%s | %s | %s}' % (result[0],
                               ', '.join(result[1:5]),
                               ', '.join(result[5:]))

# __________ table compression __________

def compress_gcmaptable(table):
    # Compress ranges table[i:j] of entries with the same state
    # into a single entry whose label is the start of the range.
    # The last element in the table is never compressed in this
    # way for debugging reasons, to avoid that a random address
    # in memory gets mapped to the last element in the table
    # just because it's the closest address.
    # To be on the safe side, compress_gcmaptable() should be called
    # after each function processed -- otherwise the result depends on
    # the linker not rearranging the functions in memory, which is
    # fragile (and wrong e.g. with "make profopt").
    i = 0
    limit = len(table) - 1     # only process entries table[:limit]
    while i < len(table):
        label1, state = table[i]
        is_range = False
        j = i + 1
        while j < limit and table[j][1] == state:
            is_range = True
            j += 1
        # now all entries in table[i:j] have the same state
        yield (label1, state, is_range)
        i = j

def compress_callshape(shape):
    # For a single shape, this turns the list of integers into a list of
    # bytes and reverses the order of the entries.  The length is
    # encoded by inserting a 0 marker after the gc roots coming from
    # shape[5:] and before the 5 values coming from shape[4] to
    # shape[0].  In practice it seems that shapes contain many integers
    # whose value is up to a few thousands, which the algorithm below
    # compresses down to 2 bytes.  Very small values compress down to a
    # single byte.
    assert len(shape) >= 5
    shape = list(shape)
    assert 0 not in shape[5:]
    shape.insert(5, 0)
    result = []
    for loc in shape:
        if loc < 0:
            loc = (-loc) * 2 - 1
        else:
            loc = loc * 2
        flag = 0
        while loc >= 0x80:
            result.append(int(loc & 0x7F) | flag)
            flag = 0x80
            loc >>= 7
        result.append(int(loc) | flag)
    result.reverse()
    return result

def decompress_callshape(bytes):
    # For tests.  This logic is copied in asmgcroot.py.
    result = []
    n = 0
    while n < len(bytes):
        value = 0
        while True:
            b = bytes[n]
            n += 1
            value += b
            if b < 0x80:
                break
            value = (value - 0x80) << 7
        if value & 1:
            value = ~ value
        value = value >> 1
        result.append(value)
    result.reverse()
    assert result[5] == 0
    del result[5]
    return result

def getidentifier(s):
    def mapchar(c):
        if c.isalnum():
            return c
        else:
            return '_'
    if s.endswith('.s'):
        s = s[:-2]
    s = ''.join([mapchar(c) for c in s])
    while s.endswith('__'):
        s = s[:-1]
    return s


if __name__ == '__main__':
    verbose = 1
    shuffle = False
    output_raw_table = False
    while len(sys.argv) > 1:
        if sys.argv[1] == '-v':
            del sys.argv[1]
            verbose = sys.maxint
        elif sys.argv[1] == '-r':
            del sys.argv[1]
            shuffle = True
        elif sys.argv[1] == '-t':
            del sys.argv[1]
            output_raw_table = True
        else:
            break
    if sys.platform == 'darwin':
        format = 'darwin'
    elif sys.platform == 'win32':
        format = 'mingw32'
    else:
        format = 'elf'
    tracker = GcRootTracker(verbose=verbose, shuffle=shuffle, format=format)
    for fn in sys.argv[1:]:
        f = open(fn, 'r')
        firstline = f.readline()
        f.seek(0)
        if firstline.startswith('seen_main = '):
            tracker.reload_raw_table(f)
            f.close()
        else:
            assert fn.endswith('.s')
            lblfn = fn[:-2] + '.lbl.s'
            g = open(lblfn, 'w')
            try:
                tracker.process(f, g, filename=fn)
            except:
                g.close()
                os.unlink(lblfn)
                raise
            g.close()
            f.close()
            if output_raw_table:
                tracker.dump_raw_table(sys.stdout)
    if not output_raw_table:
        tracker.dump(sys.stdout)
