import _rawffi
import ctypes

_c = ctypes.CDLL(_rawffi.libc_name)

open_osfhandle = _c._open_osfhandle
open_osfhandle.argtypes = [ctypes.c_int, ctypes.c_int]
open_osfhandle.restype = ctypes.c_int

get_osfhandle = _c._get_osfhandle
get_osfhandle.argtypes = [ctypes.c_int]
open_osfhandle.restype = ctypes.c_int

del ctypes
