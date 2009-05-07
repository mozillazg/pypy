from pypy.lang.io.register import register_method
from pypy.lang.io.model import W_Number
@register_method('List', 'append')
def list_append(space, w_target, w_message, w_context):
    assert w_message.arguments,  'requires at least one argument'
    w_items = [x.eval(space, w_target, w_context) for x in w_message.arguments]
    w_target.append(w_items)
    return w_target

@register_method('List', 'at', unwrap_spec=[object, int])
def list_at(space, target, argument):
    return target[argument]