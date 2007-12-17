from _ctypes.dummy import Union, Structure, Array, _Pointer, CFuncPtr
from _ctypes.dummy import ArgumentError, dlopen, sizeof, byref, addressof
from _ctypes.dummy import alignment, resize
from _ctypes.dummy import _memmove_addr, _memset_addr, _string_at_addr
from _ctypes.dummy import _cast_addr

from _ctypes.primitive import _SimpleCData


__version__ = '1.0.2'
#XXX platform dependant?
RTLD_LOCAL = 0
RTLD_GLOBAL = 256
FUNCFLAG_CDECL = 1
FUNCFLAG_PYTHONAPI = 4
