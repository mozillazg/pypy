#!/usr/bin/env python
""" Usage: loopviewer.py [-i# -n] loopfile
             -i: specifies the loop number, default to the last one
             -n: show the unoptimized loops instead of the optimized ones
"""

import autopath
import py
import sys
from getopt import gnu_getopt
from pypy.rlib.rlog_parsing import extract_sections
from pypy.jit.metainterp.test.oparser import parse
from pypy.jit.metainterp.history import ConstInt
from pypy.rpython.lltypesystem import llmemory, lltype

def main(loopfile, loopnum=-1, noopt=False):
    if noopt:
        word = 'noopt'
    else:
        word = 'opt'
    loops = list(extract_sections(loopfile, 'jit-log-%s-*' % word))
    inp = loops[loopnum]
    loop = parse(inp, no_namespace=True, enforce_fail_args=False)
    loop.show()

if __name__ == '__main__':
    options, args = gnu_getopt(sys.argv[1:], 'i:n')
    if len(args) != 1:
        print __doc__
        sys.exit(1)
    [loopfile] = args
    options = dict(options)
    loopnum = int(options.get('-i', -1))
    noopt = '-n' in options
    main(loopfile, loopnum=loopnum, noopt=noopt)
