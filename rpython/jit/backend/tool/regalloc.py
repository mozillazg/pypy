#! /usr/bin/env python
"""
    ./regalloc.py log
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
from rpython.jit.metainterp.history import Box
from rpython.jit.metainterp.resoperation import rop, ResOperation, opname
from rpython.tool.jitlogparser.parser import SimpleParser
from rpython.jit.backend.llsupport.regalloc import compute_vars_longevity

class RegallocParser(SimpleParser):
    def __init__(self, text, a, b, c, d, nonstrict=False):
        SimpleParser.__init__(self, text, a, b, c, d, nonstrict=nonstrict)
        self.opp = OpParser('', None, {}, 'lltype', None, True, nonstrict)

    def box_for_var(self, res):
        if res[0] in ('i','p','f'):
            return self.opp.box_for_var(res)
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

class LRLoop(object):

    def __init__(self, type, inputargs, operations):
        self.type = type
        self.entries = {}
        self.inputargs = inputargs
        self.operations = operations

    def found_live_range(self, typ, arg, lr):
        lrt = self.entries.setdefault(typ[0],[])
        lrt.append((arg, lr))

    def consider(self, longevity, last_real_use):
        loop_start = 0
        loop_end = len(self.operations)-1
        for arg, lr in longevity.items():
            (start, end, uses) = lr = normalize_lr(lr)
            if start == loop_start and end == loop_end and len(uses) == 2:
                self.found_live_range(LR.DUMMY, arg, lr)
            if start == loop_start and end == loop_end and len(uses) > 2:
                self.found_live_range(LR.LOOP_USE, arg, lr)
            if start == loop_start:
                all_guard_failargs = True
                used_in_guard = 0
                for pos in uses[1:]:
                    op = self.operations[pos]
                    if op.getfailargs() is None or arg not in op.getfailargs():
                        all_guard_failargs = False
                        break
                    used_in_guard += 1
                #
                if all_guard_failargs:
                    self.found_live_range(LR.GUARD_ONLY, arg, lr)
                else:
                    if end != loop_end:
                        op = self.operations[uses[-1]]
                        if op.getfailargs() is not None and arg in op.getfailargs():
                            self.found_live_range(LR.GUARD, arg, lr)
                        else:
                            if used_in_guard > 0:
                                self.found_live_range(LR.ENTER, arg, lr)
                            else:
                                self.found_live_range(LR.ENTER_NO_GUARD, arg, lr)
                            pass

class LR(object):

    DUMMY = ('dummy', """
    a live range that spans over the whole trace, but is never used
    """)
    # 
    LOOP_USE = ('loop use', """
    a live range that spans over the whole trace, use x times. (x > 0)
    """)
    GUARD_ONLY = ('guard only', """
    a live range that spans from the label to a guard exit (can be used only in guard fail args)
    """)
    GUARD = ('guard', """
    a live range that spans from the label to a guard exit may be used several times in between
    """)
    ENTER = ('enter', """
    a live range that spans from the label to an operation (not jump/label) may be used several times in between
    """)
    ENTER_NO_GUARD = ('enter no guard', """
    same as enter, but is not used in guard exit
    """)

    def __init__(self):
        self.loops = []

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

    def show(self, name, *args):
        if isinstance(name, tuple):
            name = name[0]
        print (name + ":").rjust(20, " "), 
        for arg in args:
            print arg,
        print

    def header(self, name):
        print name.rjust(5, "_").ljust(5,"_")

    def print_stats(self):
        print
        self.header("STATS")
        normal = [l for l in self.loops if l.type == 'normal']
        loop_count = len(normal)
        peeled = [l for l in self.loops if l.type == 'peeled']
        peeled_count = len(peeled)
        self.show("loop count", loop_count)
        self.show("peeled count", peeled_count)

        self.header("PEELED LOOPS")
        self.print_for_loops(peeled)

        self.header("NORMAL LOOPS")
        self.print_for_loops(normal)

    def print_for_loops(self, loops):
        for type in LR.ALL_TYPES:
            lrs = self.all_entries(loops, type)
            counts = map(lambda e: len(e), lrs)
            self.show_cmv(type, counts)

    def show_cmv(self, name, counts):
        total = sum(counts)
        self.show(name, "count %d mean %.2f var %.2f" % (total, self.mean(counts), self.var(counts)))

    def mean(self, values):
        if len(values) == 0:
            return '0'
        import numpy
        return numpy.average(values)

    def var(self, values):
        import numpy
        return numpy.std(values)

    def all_entries(self, loops, type):
        if isinstance(type, tuple):
            type = type[0]
        entries = []
        for loop in loops:
            e = loop.entries.get(type, [])
            entries.append(e)
        return entries


    def examine(self, inputargs, operations, peeled=False):
        longevity, last_real_use = compute_vars_longevity(inputargs, operations)
        self._check_longevity(operations, longevity)

        typ = 'normal'
        if peeled:
            typ = 'peeled'
        lrl = LRLoop(typ, inputargs, operations)
        lrl.consider(longevity, last_real_use)
        self.loops.append(lrl)

LR.ALL_TYPES = []
for e in dir(LR):
    if e[0].isupper() and e != 'ALL_TYPES':
        LR.ALL_TYPES.append(getattr(LR, e))


# ____________________________________________________________

if __name__ == '__main__':
    from rpython.tool import logparser
    log1 = logparser.parse_log_file(sys.argv[1])
    loops = logparser.extract_category(log1, catprefix='jit-log-compiling-loop')
    lr = LR()
    ns = {}
    loop_count = len(loops)
    print
    for j,text in enumerate(loops):
        parser = RegallocParser(text, None, {}, 'lltype', None, nonstrict=True)
        loop = parser.parse()
        unrolled_label = -1
        first_label = -1
        for i,op in enumerate(loop.operations):
            if op.getopnum() == rop.LABEL:
                if first_label == -1:
                    first_label = i
                else:
                    unrolled_label = i

        first_label = 0

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
            ops = loop.operations[first_label:]
            #for op in ops:
            #    print op
            #print '-' * 80
            inputargs = loop.inputargs
            lr.examine(inputargs, ops, peeled=False)
        print "\rloop %d/%d (%d%%)" % (j, loop_count, int(100.0 * j / loop_count)),
        sys.stdout.flush()

    lr.print_stats()
