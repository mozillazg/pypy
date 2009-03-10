
from pypy.rpython.lltypesystem import lltype, ll2ctypes
import ctypes

def parentchain(container):
    current = container
    links = []
    while True:
        link = lltype.parentlink(current)
        if link[0] is None:
            try:
                addr = ctypes.addressof(container._storage)
                actual = ll2ctypes._parent_cache[addr]
                if len(links) < len(actual):
                    return actual
            except KeyError:
                pass
            return links
        links.append(link)
        current = link[0]

def setparentstructure(container, chain):
    current = container
    for elem in chain:
        current._setparentstructure(*elem)
        current = elem[0]
