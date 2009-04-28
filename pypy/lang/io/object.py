from pypy.lang.io.register import register_method
from pypy.lang.io.model import W_ImmutableSequence, W_Block

@register_method('Object', 'setSlot')
def w_object_set_slot(space, w_target, w_message, w_context):
    w_name = w_message.arguments[0].eval(space, w_context, w_context)
    w_value = w_message.arguments[1].eval(space, w_context, w_context)
    assert isinstance(w_name, W_ImmutableSequence)
    w_target.slots[w_name.value] = w_value
    return w_value
    
@register_method('Object', 'method')
def w_object_method(space, w_target, w_message, w_context):
    w_body = w_message.arguments[-1]
    w_arguments = w_message.arguments[:-1]
    names = [x.name for x in w_arguments]
    return W_Block(space, names, w_body)

@register_method('Object', 'clone')
def w_object_clone(space, w_target, w_message, w_context):
    assert w_message.name == 'clone'
    return w_target.clone()
# def w_object_get_slot(w_target, w_message, w_context):
#     pass