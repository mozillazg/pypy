class BaseNumArray(object):
    pass

def iterable_type(space, w_xs):
    xs = space.fixedview(w_xs)
    type = int
    for i in range(len(xs)):
        type = result_types[type, xs[i]]
    return type

def mul_operation():
    def mul(x, y): return x * y
    return mul

def div_operation():
    def div(x, y): return x / y
    return div

def add_operation():
    def add(x, y): return x + y
    return add

def sub_operation():
    def sub(x, y): return x - y
    return sub

def copy_operation():
    def copy(x, y): return x #XXX: I sure hope GCC can optimize this
    return copy

def app_mul_operation():
    def mul(space, x, y):
        return space.mul(x, y)
    return mul

def app_div_operation():
    def div(space, x, y):
        return space.div(x, y)
    return div

def app_add_operation():
    def add(space, x, y):
        return space.add(x, y)
    return add

def app_sub_operation():
    def sub(space, x, y):
        return space.sub(x, y)
    return sub
