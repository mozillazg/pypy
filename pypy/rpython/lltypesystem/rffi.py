
from pypy.rpython.lltypesystem import lltype

def llexternal(name, args, result, sources=[], includes=[]):
    ext_type = lltype.FuncType(args, result)
    return lltype.functionptr(ext_type, name, external='C',
                              sources=tuple(sources),
                              includes=tuple(includes))

CCHARP = lltype.Array(lltype.Char, hints={'nolength': True})

# various type mapping
# str -> char*
def str2charp(s):
    array = lltype.malloc(CCHARP, len(s) + 1, flavor='raw')
    for i in range(len(s)):
        array[i] = s[i]
    array[len(s)] = chr(0)
    return array
