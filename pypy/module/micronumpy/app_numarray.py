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

def array(xs, dtype=None):
    import numpy
    arrays = {
              int: numpy.IntArray,
              float: numpy.FloatArray,
              #complex: ComplexNumArray,
             }
    #type = lowest_common_type(xs)
    #return arrays[type](xs)
    return numpy.zeros(len(xs), dtype=int) #FIXME
