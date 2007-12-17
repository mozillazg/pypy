from _ctypes.dummy import Union, Structure, Array, _Pointer, CFuncPtr
from _ctypes.dummy import ArgumentError, dlopen, sizeof, byref, addressof
from _ctypes.dummy import alignment, resize, _SimpleCData
from _ctypes.dummy import _memmove_addr, _memset_addr, _string_at_addr
from _ctypes.dummy import _cast_addr



__version__ = '1.0.2'
#XXX platform dependant?
RTLD_LOCAL = 0
RTLD_GLOBAL = 256
FUNCFLAG_CDECL = 1
FUNCFLAG_PYTHONAPI = 4
