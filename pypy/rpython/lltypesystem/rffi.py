
from pypy.rpython.lltypesystem import lltype
from pypy.rpython.lltypesystem.lloperation import llop

def llexternal(name, args, result, sources=[], includes=[]):
    ext_type = lltype.FuncType(args, result)
    return lltype.functionptr(ext_type, name, external='C',
                              sources=tuple(sources),
                              includes=tuple(includes))

def cstruct(name, *fields, **kwds):
    """ A small helper to create external C structure, not the
    pypy one
    """
    if 'hints' not in kwds:
        kwds['hints'] = {}
    kwds['hints']['external'] = 'C'
    kwds['hints']['c_name'] = name
    # XXX obscure hack, stolen for unknown reason from ctypes,
    # probably because of _ attributes
    c_fields = [('c_' + key, value) for key, value in fields]
    return lltype.Ptr(lltype.Struct(name, *c_fields, **kwds))

# char *
CCHARP = lltype.Ptr(lltype.Array(lltype.Char, hints={'nolength': True}))

# various type mapping
def str2charp(s):
    """ str -> char*
    """
    array = lltype.malloc(CCHARP.TO, len(s) + 1, flavor='raw')
    for i in range(len(s)):
        array[i] = s[i]
    array[len(s)] = '\x00'
    return array

# char**
CCHARPP = lltype.Ptr(lltype.Array(CCHARP, hints={'nolength': True}))

def liststr2charpp(l):
    """ list[str] -> char**, NULL terminated
    """
    array = lltype.malloc(CCHARPP.TO, len(l) + 1, flavor='raw')
    for i in range(len(l)):
        array[i] = str2charp(l[i])
    array[len(l)] = lltype.nullptr(CCHARP.TO)
    return array

def free_charpp(ref):
    """ frees list of char**, NULL terminated
    """
    next = ref
    i = 0
    while next[i]:
        lltype.free(next[i], flavor='raw')
        i += 1
    lltype.free(ref, flavor='raw')

