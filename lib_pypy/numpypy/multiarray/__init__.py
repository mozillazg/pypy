

typeinfo = {}
import _numpypy as ndarray
import _numpypy as array

from _numpypy import *
def bad_func(*args, **kwargs):
    raise ValueError('bad_func called')
def nop(*args, **kwargs):
    pass
if 0:
    setattr(_numpypy, 'datetime_data', bad_func)
    setattr(_numpypy, 'datetime_as_string', bad_func)
    setattr(_numpypy, 'busday_offset', bad_func)
    setattr(_numpypy, 'busday_count', bad_func)
    setattr(_numpypy, 'is_busday', bad_func)
    setattr(_numpypy, 'busdaycalendar', bad_func)
    setattr(_numpypy, 'set_typeDict', nop)
def set_typeDict(*args, **kwargs):
    pass

datetime_data = bad_func
CLIP = 0
WRAP = 0
RAISE = 0
MAXDIMS = 0
ALLOW_THREADS = 0
BUFSIZE = 0


