from _ctypes.dummy import Union, Array
from _ctypes.dummy import ArgumentError, addressof
from _ctypes.dummy import resize
from _ctypes.dummy import _memmove_addr, _memset_addr, _string_at_addr
from _ctypes.dummy import _cast_addr

from _ctypes.basics import _CData, sizeof, alignment, byref
from _ctypes.primitive import _SimpleCData
from _ctypes.pointer import _Pointer
from _ctypes.function import CFuncPtr
from _ctypes.dll import dlopen
from _ctypes.structure import Structure


__version__ = '1.0.2'
#XXX platform dependant?
RTLD_LOCAL = 0
RTLD_GLOBAL = 256
FUNCFLAG_CDECL = 1
FUNCFLAG_PYTHONAPI = 4
