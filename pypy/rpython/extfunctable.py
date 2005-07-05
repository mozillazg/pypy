"""
information table about external functions for annotation/ rtyping and backends
"""
import os
import types

class ExtFuncInfo:
    def __init__(self, func, annotation, ll_function, ll_annotable):
        self.func = func
        self.annotation = annotation
        self.ll_function = ll_function
        self.ll_annotable = ll_annotable

table = {}
def declare(func, annotation, ll_function, ll_annotable=True):
    # annotation can be a function computing the annotation
    # or a simple python type from which an annotation will be construcuted
    global table
    if not isinstance(annotation, types.FunctionType):
        typ = annotation
        def annotation(*args_s):
            from pypy.annotation import bookkeeper
            return bookkeeper.getbookkeeper().valueoftype(typ)
    table[func] = ExtFuncInfo(func, annotation, ll_function, ll_annotable)

# low-level helpers representing the external functions
def ll_os_getuid():
    return 1 #return os.getuid()

def ll_os_dup(fd):
    return 999

# external function declarations
declare(os.getuid, int, ll_os_getuid, ll_annotable=True)
declare(os.dup, int, ll_os_dup, ll_annotable=True)
