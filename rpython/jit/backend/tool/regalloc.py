#! /usr/bin/env python
"""
    Prints information about the live range of a trace recorded in the specified logfiles.
    It aggregates the information over all traces in the logfiles.

    ./regalloc.py [--histogram] logfile1 [logfile2 ...]
"""

import new
import operator
import os
import py
import re
import sys
import subprocess
from bisect import bisect_left

from rpython.jit.tool.oparser import OpParser, parse
from rpython.jit.metainterp.history import Box, ConstInt
from rpython.jit.metainterp.resoperation import rop, ResOperation, opname
from rpython.tool.jitlogparser.parser import SimpleParser
from rpython.jit.backend.llsupport.regalloc import compute_vars_longevity

class RegallocParser(SimpleParser):

    use_mock_model = False

    def __init__(self, text):
        SimpleParser.__init__(self, text, None, {}, 'lltype', None, nonstrict=True)

    def box_for_var(self, res):
        if res[0] in ('i','p','f'):
            arg = OpParser.box_for_var(self, res)
            assert isinstance(arg, Box), "is box" + str(arg)
            return arg
        try:
            return ConstInt(int(res))
        except ValueError:
            return res

    def create_op(self, opnum, args, res, descr, fail_args):
        if isinstance(descr, str):
            descr = None
        for i in range(len(args)):
            if isinstance(args[i], str):
                args[i] = self.box_for_var(args[i])
        op = ResOperation(opnum, args, res, descr)
        if op.is_guard():
            op.setfailargs(fail_args)
        return op

def normalize_lr(lr):
    """ if the last entry is None set is as list """
    if lr[2] is None:
        s = lr[0]
        e = lr[1]
        return (s,e,[s,e])
    return lr

class LiveRange(object):
    def __init__(self, arg, lr):
        self.name = str(arg)
        self.arg = arg
        self.start = lr[0]
        self.end = lr[1]
        self.uses = lr[2]

class LoopLiveRanges(object):

    def __init__(self, inputargs, operations):
        self.entries = {}
        self.inputargs = inputargs
        self.operations = operations
        self.longevity = None
        longevity, last_real_use = compute_vars_longevity(inputargs, operations)
        self._check_longevity(operations, longevity)
        self.consider(longevity, last_real_use)

    def _check_longevity(self, operations, longevity):
        return
        for i,op in enumerate(operations):
            if op.result:
                assert op.result in longevity
            for arg in [a for a in op.getarglist() if isinstance(a, Box)]:
                assert arg in longevity
                uses = longevity[arg][2]
                if uses is not None:
                    assert i in longevity[arg][2]

    def ranges(self, at):
        lrs = self.lr_active[at]
        return lrs

    def found_live_range(self, typedescr, arg, lr):
        typename = typedescr
        if not isinstance(typedescr,str):
            typename = typedescr[0]
        lrt = self.entries.setdefault(typename,[])
        lrt.append((self.operations, lr))

    def active_live_ranges(self, position):
        active = []
        for arg, lr in self.longevity.items():
            (start, end, uses) = lr = normalize_lr(lr)
            if start <= position <= end:
                active.append(LiveRange(arg,lr))
        return sorted(active, key=lambda x: x.name)

    def consider(self, longevity, last_real_use):
        self.longevity = longevity
        loop_start = 0
        loop_end = len(self.operations)-1
        self.lr_active = [0] * loop_end
        self.lr_active_max = -1
        self.lr_active_min = sys.maxint
        for i in range(loop_end):
            self.lr_active[i] = lra = self.active_live_ranges(i)
            self.lr_active_max = max(self.lr_active_max, len(lra))
            self.lr_active_min = min(self.lr_active_min, len(lra))

        for arg, lr in longevity.items():
            (start, end, uses) = lr = normalize_lr(lr)
            if start == loop_start and end == loop_end:
                self.found_live_range(LR.WHOLE, arg, lr)
                self.find_fail_type(LR.WHOLE, arg, lr)
            elif start == loop_start and end != loop_end:
                self.found_live_range(LR.ENTER, arg, lr)
                self.find_fail_type(LR.ENTER, arg, lr)
            elif end == loop_end and start != loop_start:
                self.found_live_range(LR.EXIT, arg, lr)
                self.find_fail_type(LR.EXIT, arg, lr)
            elif end != loop_end and start != loop_start:
                self.found_live_range(LR.VOLATILE, arg, lr)
                self.find_fail_type(LR.VOLATILE, arg, lr)
        self._check()

    def find_fail_type(self, typedescr, arg, lr):
        typename = typedescr[0]
        (start, end, uses) = lr

        used_in_guard = 0
        for pos in uses[1:]:
            op = self.operations[pos]
            if op.getfailargs() is None or arg not in op.getfailargs():
                continue
            used_in_guard += 1
        if used_in_guard == 0:
            self.found_live_range(typename + '-' + LR.NO_FAIL[0], arg, lr)
        else:
            self.found_live_range(typename + '-' + LR.FAIL[0], arg, lr)
            op = self.operations[uses[-1]]
            if op.getfailargs() is not None and arg in op.getfailargs():
                self.found_live_range('-'.join((typename, LR.FAIL[0], LR.END_FAIL[0])), arg, lr)
            if len(uses) - 1 == used_in_guard:
                self.found_live_range('-'.join((typename, LR.FAIL[0], LR.ONLY_FAIL[0])), arg, lr)

    def count(self, typedescr):
        return len(self.entries.get(typedescr[0],[]))

    def _check(self):
        total_ranges = len(self.longevity)
        assert self.count(LR.WHOLE) + self.count(LR.ENTER) + \
               self.count(LR.EXIT) + self.count(LR.VOLATILE) == total_ranges

class LR(object):

    WHOLE = ('whole', """
    a live range that spans over the whole trace, used x times. (x > 0)
    """)
    ENTER = ('enter', """
    a live range that spans from the label to an operation (but not jump/label)
    """)
    EXIT = ('exit', """
    a live range that starts at operation X (not at a label) and exits the trace in a jump
    """)
    VOLATILE = ('volatile', """
    a live range that starts at operation X (not a label) and ends at operation Y (not a jump/label)
    """)
    ALL_TYPES = [WHOLE, ENTER, EXIT, VOLATILE]

    ONLY_FAIL = ('only failarg', """
    a live range that is used only as fail arguments
    """)
    FAIL = ('used as failargs', """
    a live range that is used in a guard exit as fail argument
    """)
    END_FAIL = ('end in failargs',"""
    a live range that ends in a guard exit
    """)
    NO_FAIL = ('not in any failargs', """
    a live range that is not used as a fail argument
    """)

    FAIL_TYPES = [FAIL, NO_FAIL]

    def __init__(self):
        self.loops = []

    def show(self, name, arg, indent=0):
        if isinstance(name, tuple):
            name = name[0]
        try:
            rindex = name.rindex('-')
            name = name[rindex+1:]
        except ValueError:
            pass
        print (' ' + ' ' * (indent*2) + (name + ":")).ljust(30, ' '), arg

    def header(self, name):
        print name

    def print_stats(self, histogram=False):
        print
        self.header("STATS")
        normal = [l for l in self.loops if l.type == 'normal']
        loop_count = len(normal)
        peeled = [l for l in self.loops if l.type == 'peeled']
        bridges = [l for l in self.loops if l.type == 'bridge']
        peeled_count = len(peeled)
        self.show("loop count", loop_count)
        self.show("peeled count", peeled_count)
        self.show("bridge count", len(bridges))

        self.header("")
        self.header("BRIDGES")
        self.print_for_loops(bridges, hist=histogram)

        self.header("")
        self.header("SHELL LOOPS (loop that are not unrolled or enter a peeled loop)")
        self.print_for_loops(normal, hist=histogram)

        self.header("")
        self.header("PEELED LOOPS")
        self.print_for_loops(peeled, hist=histogram)


    def show_help(self, help, descr, indent):
        if help:
            print " " * (indent * 2), "%s: %s" % (descr[0], descr[1].lstrip().rstrip())

    def print_for_loops(self, loops, help=True, hist=True):
        lr_counts = []
        for loop in loops:
            lr_counts.append(len(loop.longevity))
        self.show_help(True, ('lr (overlap) max', 'the max number of live ranges that overlap in a trace'), 0)
        self.show_cmv('lr (overlap) max', map(lambda x: getattr(x, 'lr_active_max'), loops), histogram=hist, integer=True)
        self.show_help(True, ('lr (overlap) min', 'the min number of live ranges that overlap in a trace'), 0)
        self.show_cmv('lr (overlap) min', map(lambda x: getattr(x, 'lr_active_min'), loops), histogram=False, integer=True)
        self.show_help(True, ('lr count', 'the live range count'), 0)
        self.show_cmv('lr count', lr_counts, histogram=hist, integer=True)
        for typedescr in LR.ALL_TYPES:
            typename = typedescr[0]
            lrs = self.all_entries(loops, typename)
            self.show_help(help, typedescr, 0)
            self.show_cmv(typename, lrs, 0, histogram=hist)
            #
            for failtypedescr in LR.FAIL_TYPES:
                failtypename = typename + '-' + failtypedescr[0]
                lrs = self.all_entries(loops, failtypename)
                self.show_help(help, failtypedescr, 1)
                self.show_cmv(failtypename, lrs, 1, histogram=hist)

                if failtypedescr == LR.FAIL:
                    self.show_help(help, LR.END_FAIL, 2)
                    failtypename = failtypename + '-' + LR.END_FAIL[0]
                    lrs = self.all_entries(loops, failtypename)
                    self.show_cmv(failtypename, lrs, 2, histogram=hist)

                    self.show_help(help, LR.ONLY_FAIL, 2)
                    failtypename = failtypename + '-' + LR.ONLY_FAIL[0]
                    lrs = self.all_entries(loops, failtypename)
                    self.show_cmv(failtypename, lrs, 2, histogram=hist)

    def show_cmv(self, name, loop_lrs, indent=0, histogram=True, integer=False):
        indent = " " * (indent * 2)
        if integer:
            counts = loop_lrs
        else:
            counts = map(lambda e: len(e), loop_lrs)
            use_count = []
            use_guard_count = []
            for lrs in loop_lrs:
                for ops, lr in lrs:
                    count = 0
                    gcount = 0
                    for use in lr[2][1:]:
                        op = ops[use]
                        if op.is_guard():
                            gcount += 1
                        count += 1
                    use_count.append(count)
                    use_guard_count.append(gcount)

            if len(use_count) > 0:
                print indent, " #use: mean %.2f std %.2f" % (self.mean(use_count), self.var(use_count))
            if len(use_guard_count) > 0:
                print indent, " guard #use: mean %.2f std %.2f" % (self.mean(use_guard_count), self.var(use_guard_count))

        total = len(counts)
        total_sum = sum(counts)
        min_counts = min(counts)
        max_counts = max(counts)
        print indent," mean %.2f std %.2f" % (self.mean(counts),self.var(counts))
        print indent," min %d max %d" % (min_counts,max_counts)
        if histogram:
            import numpy
            hist, bins = numpy.histogram(counts,bins=5)
            for i in range(5):
                l = bins[i]
                u = bins[i+1]
                v = hist[i]
                print indent, " [%.1f-%.1f): %d (%.1f%%)" % (l, u, int(v), (100*float(v)/len(counts)))

    def mean(self, values):
        if len(values) == 0:
            return '0'
        import numpy
        return numpy.average(values)

    def var(self, values):
        import numpy
        return numpy.std(values)

    def all_entries(self, loops, type):
        if not isinstance(type, str):
            type = type[0]
        entries = []
        for loop in loops:
            lrs = loop.entries.get(type, [])
            entries.append(lrs)
        return entries


    def examine(self, inputargs, operations, peeled=False, bridge=False):
        llr = LoopLiveRanges(inputargs, operations)
        llr.type = 'normal'
        if peeled:
            llr.type = 'peeled'
        if bridge:
            llr.type = 'bridge'
        self.loops.append(llr)

# ____________________________________________________________

if __name__ == '__main__':
    from rpython.tool import logparser
    histogram = False
    if '--histogram' in sys.argv:
        histogram = True
        sys.argv.remove('--histogram')
    lr = LR()
    skipped = []
    skipped_not_loop = []
    total_trace_count = 0
    for logfile in sys.argv[1:]:
        print "reading",logfile,"..."
        log1 = logparser.parse_log_file(logfile)
        loops = logparser.extract_category(log1, catprefix='jit-log-opt-loop')
        ns = {}
        loop_count = len(loops)
        total_trace_count += loop_count
        for j,text in enumerate(loops):
            parser = RegallocParser(text)
            loop = parser.parse()
            unrolled_label = -1
            first_label = -1
            for i,op in enumerate(loop.operations):
                if op.getopnum() == rop.LABEL:
                    if first_label == -1:
                        first_label = i
                    else:
                        unrolled_label = i

            if loop.operations[-1].getopnum() != rop.JUMP:
                assert loop.operations[-1].getopnum() == rop.FINISH
                skipped_not_loop.append(loop)
                continue

            if first_label != 0:
                if first_label == -1 and loop.operations[-1].getopnum() == rop.JUMP:
                    assert unrolled_label == -1
                    # add an artificial instruction to support the live range computation
                    #loop.operations.insert(0, ResOperation(rop.LABEL, [inputargs], None, None))
                else:
                    first_label = 0
                    #skipped.append(loop)
                    #continue

            if unrolled_label > 0:
                ops = loop.operations[first_label:unrolled_label+1]
                #    for op in ops:
                #        print op
                #    print '=' * 80
                inputargs = loop.inputargs
                lr.examine(inputargs, ops, peeled=False)
                # peeled loop
                ops = loop.operations[unrolled_label:]
                #for op in ops:
                #    print op
                label = ops[0]
                inputargs = label.getarglist()
                lr.examine(inputargs, ops, peeled=True)
                #print '-' * 80
            else:
                if first_label == -1:
                    ops = loop.operations
                    bridge = True
                else:
                    ops = loop.operations[first_label:]
                    bridge = False
                #for op in ops:
                #    print op
                #print '-' * 80
                inputargs = loop.inputargs
                lr.examine(inputargs, ops, peeled=False, bridge=bridge)
            print "\rloop %d/%d (%d%%)" % (j, loop_count, int(100.0 * j / loop_count)),
            sys.stdout.flush()
        print
    print "total trace count:", total_trace_count
    
    if len(skipped) > 0:
        print
        print "skipped %d traces, because their first instr was not a label" % len(skipped)

    if len(skipped_not_loop) > 0:
        print
        print "skipped %d traces (not loops but traces)" % len(skipped_not_loop)

    lr.print_stats(histogram)
