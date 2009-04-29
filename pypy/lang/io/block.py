from pypy.lang.io.register import register_method
from pypy.lang.io.model import W_Block

@register_method('Block', 'call')
def w_block_call(space, w_target, w_message, w_context):
    return w_target.call(space, w_target, w_message, w_context)

    