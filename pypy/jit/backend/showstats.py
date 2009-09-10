#!/usr/bin/env python
import sys, py
from pypy.jit.metainterp.test.oparser import parse
from pypy.rpython.lltypesystem import lltype, llmemory

class AllDict(dict):
    def __getitem__(self, item):
        return lltype.nullptr(llmemory.GCREF.TO)

alldict = AllDict()

def main(argv):
    lst = py.path.local(argv[0]).read().split("[")
    lst = ['[' + i for i in lst if i]
    for oplist in lst:
        print len(parse(oplist, namespace=alldict).operations)

if __name__ == '__main__':
    main(sys.argv[1:])
