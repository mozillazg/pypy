import os
from pypy.rpython.lltypesystem import lltype, rffi
from pypy.jit.codegen.x86_64.assembler import X86_64CodeBuilder
#from ri386 import I386CodeBuilder

modname = 'pypy.jit.codegen.i386.codebuf_' + os.name
memhandler = __import__(modname, globals(), locals(), ['__doc__'])

PTR = memhandler.PTR

class InMemoryCodeBuilder(X86_64CodeBuilder):

    def __init__(self, map_size):
        data = memhandler.alloc(map_size)
        self._data = data
        self._size = map_size
        self._pos = 0
        self._all = []

    def write(self, data):
        p = self._pos
        if p + len(data) > self._size:
            raise CodeBlockOverflow
        for c in data:
            self._data[p] = c
            p += 1
        self._all.append(data)
        self._pos = p

    def tell(self):
        baseaddr = rffi.cast(lltype.Signed, self._data)
        return baseaddr + self._pos


