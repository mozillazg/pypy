
from pypy.rpython.lltypesystem import lltype, rffi

CHUNK_SIZE = 100

TP = rffi.CArray(lltype.Float)

class Chunk(object):
    def __init__(self, basesize):
        self.ll_array = lltype.malloc(TP, basesize, flavor='raw')
        self.size = 0

class ListOfFloats(object):
    def __init__(self, basesize=CHUNK_SIZE):
        self.basesize = basesize
        self.chunks = []
        self.size = 0
        self.dict = {}

    def length(self):
        return self.size

    def append(self, item):
        size = self.size
        if not size % self.basesize:
            self.chunks.append(Chunk(self.basesize))
        self.chunks[-1].ll_array[size % self.basesize] = item
        self.size = size + 1
        return size

    def getitem(self, index):
        mod = index % self.basesize
        return self.chunks[index // self.basesize].ll_array[mod]

    def get(self, item):
        index = self.dict.get(item, -1)
        if index == -1:
            index = self.append(item)
            self.dict[item] = index
        return index

    def getaddr(self, item):
        index = self.get(item)
        base = self.chunks[index // self.basesize].ll_array
        baseaddr = rffi.cast(lltype.Signed, base)
        return baseaddr + (index % self.basesize) * rffi.sizeof(lltype.Float)
