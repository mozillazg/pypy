from pypy.lang.io.register import register_method
from pypy.lang.io.model import W_Message

@register_method('Call', 'argAt')
def call_arg_at(space, w_target, w_message, w_context):
    return space.w_message.slots['argAt'].apply(
                                        space, 
                                        w_target.slots['message'], 
                                        w_message, w_context)
                                        
                                        
@register_method('Call', 'evalArgAt')
def call_eval_arg_at(space, w_target, w_message, w_context):
    return call_arg_at(space, w_target, w_message, w_context).eval(space, w_context, w_context)