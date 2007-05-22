
from pypy.rpython.lltypesystem.lltype import functionptr, FuncType

def llexternal(name, args, result, sources=[], includes=[]):
    ext_type = FuncType(args, result)
    return functionptr(ext_type, name, external='C', sources=tuple(sources),
                       includes=tuple(includes))


