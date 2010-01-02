def unwrap_int(space, w_x):
    return space.int_w(w_x)
def coerce_int(space, w_x):
    return unwrap_int(space, space.int(w_x))

def unwrap_float(space, w_x):
    return space.float_w(w_x)
def coerce_float(space, w_x):
    return unwrap_float(space, space.float(w_x))

from pypy.rlib.rarithmetic import r_singlefloat as float32
def unwrap_float32(space, w_x):
    return float32(space.float_w(w_x))
def coerce_float32(space, w_x):
    return unwrap_float32(space, space.float(w_x))
