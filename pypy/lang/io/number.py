from pypy.lang.io.register import register_method
from pypy.lang.io.model import W_Number

@register_method("Number", '+', unwrap_spec=[float, float])
def w_number_add(space, target, argument):
    return W_Number(space, target + argument)
    
@register_method("Number", '-', unwrap_spec=[float, float])
def w_number_minus(space, target, argument):
    return W_Number(space, target - argument)