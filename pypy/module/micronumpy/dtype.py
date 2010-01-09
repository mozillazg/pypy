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

def result_mapping(space, w_types):
    types = {
            (space.w_int, space.w_int): space.w_int,
            (space.w_int, space.w_float): space.w_float,
            (space.w_float, space.w_int): space.w_float,
            (space.w_float, space.w_float): space.w_float
            }
    return types[w_types]

def iterable_type(space, w_xs):
    xs = space.fixedview(w_xs)
    result_type = space.w_int
    for i in range(len(xs)):
        result_type = result_mapping(space, (result_type, space.type(xs[i])))
    return result_type
