# NOT_RPYTHON
types_list = [object, complex, float, int]

def lowest_type(x):
    result = object
    for type in types_list:
        if isinstance(x, type):
            result = type
    return result

def lowest_common_type(xs):
    types = [type(x) for x in xs]
    result = int
    for t in types:
        if types_list.index(t) < types_list.index(result):
            result = t
    return result

#FIXME: move me to interplevel
def array(xs, dtype=None):
    import numpy
    result = numpy.zeros(len(xs), dtype=dtype if dtype else lowest_common_type(xs))
    for i, x in enumerate(xs):
        result[i] = x
    return result

