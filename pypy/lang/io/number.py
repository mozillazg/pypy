from pypy.lang.io.register import register_method
from pypy.lang.io.model import W_Number
@register_method("Number", '+')
def w_number_add(w_target, w_message, w_context):
    w_arg = w_message.arguments[0].eval(w_context)
    return W_Number(w_target.space, w_target.value + w_arg.value)
    
@register_method("Number", '-')
def w_number_minus(w_target, w_message, w_context):
    w_arg = w_message.arguments[0].eval(w_context)
    return W_Number(w_target.space, w_target.value - w_arg.value)