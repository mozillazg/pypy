
def index(space, w_a):
    return space.index(w_a)

def abs(space, w_obj):
    'abs(a) -- Same as abs(a).'
    return space.abs(w_obj)

__abs__ = abs
