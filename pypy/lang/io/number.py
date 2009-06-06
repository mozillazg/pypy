from math import ceil, floor
from pypy.lang.io.register import register_method
from pypy.lang.io.model import W_Number

@register_method("Number", '+', unwrap_spec=[float, float])
def w_number_add(space, target, argument):
    return W_Number(space, target + argument)
    
@register_method("Number", '-', unwrap_spec=[float, float])
def w_number_minus(space, target, argument):
    return W_Number(space, target - argument)
    
@register_method('Number', '%', unwrap_spec=[float, float], alias=['mod'])
def w_number_modulo(space, target, argument):
    argument = abs(argument)
    return W_Number(space, target % argument)

@register_method('Number', '**', unwrap_spec=[float, float], alias=['pow'])
def w_number_modulo(space, target, argument):
    return W_Number(space, target ** argument)

@register_method('Number', 'ceil', unwrap_spec=[float])
def w_number_modulo(space, target):
    return W_Number(space, ceil(target))
    
@register_method('Number', 'floor', unwrap_spec=[float])
def w_number_modulo(space, target):
    return W_Number(space, floor(target))

@register_method('Number', 'round', unwrap_spec=[float])
def w_number_modulo(space, target):
    if target < 0:
        n = ceil(target - 0.5)
    else:
        n = floor(target + 0.5)

    return W_Number(space, n)

@register_method('Number', 'asNumber', unwrap_spec=[object])
def w_number_as_number(space, w_target):
    return w_target
    
@register_method('Number', '/', unwrap_spec=[float, float])
def w_number_divide(space, dividend, divisor):
    nan = False
    inf = False
    try:
        value = dividend/float(divisor)
    except ZeroDivisionError, e:
        value = 0
        if dividend == 0:
            nan = True
        else:
            inf = True
    finally:
        return W_Number(space, value, nan=nan, inf=inf)
    
@register_method('Number', '*', unwrap_spec=[float, float])
def w_number_multiply(space, a, b):
    return W_Number(space, a*b)