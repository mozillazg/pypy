
from ctypes import cast, c_void_p, c_int, c_double, POINTER
from pypy.rpython.lltypesystem import lltype, llmemory

# XXX I'm sure we've got 1000 such mappings...
ctypes_mapping = {lltype.Signed: c_int, lltype.Float:c_double,
                  llmemory.Address: c_int, lltype.Void:None}
