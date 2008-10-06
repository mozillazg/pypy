from __future__ import division

from pypy.rpython.lltypesystem.lltype import typeOf, _ptr, Ptr
from pypy.rpython.lltypesystem import llmemory
from pypy.rpython.memory.lltypelayout import convert_offset_to_int

def guess_size(obj):
    TYPE = typeOf(obj)
    ptr = _ptr(Ptr(TYPE), obj)
    if TYPE._is_varsize():
        arrayfld = getattr(TYPE, '_arrayfld', None)
        if arrayfld:
            length = len(getattr(ptr, arrayfld))
        else:
            length = len(ptr)
        return convert_offset_to_int(llmemory.sizeof(TYPE, length))
    return convert_offset_to_int(llmemory.sizeof(TYPE))


def group_static_size_by_lltype(database):
    totalsize = {}
    numobjects = {}
    for node in database.globalcontainers():
        obj = node.obj
        group = typeOf(obj)
        totalsize[group] = totalsize.get(group, 0) + guess_size(obj)
        numobjects[group] = numobjects.get(group, 0) + 1
    return totalsize, numobjects

def print_static_size_by_lltype(database):
    totalsize, numobjects = group_static_size_by_lltype(database)
    l = [(size, key) for key, size in totalsize.iteritems()]
    l.sort()
    l.reverse()
    for size, key in l:
        print key, size, numobjects[key], size / numobjects[key]

