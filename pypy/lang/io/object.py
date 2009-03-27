from pypy.lang.io.register import register_method
from pypy.lang.io.model import W_ImmutableSequence

@register_method('Object', 'setSlot')
def w_object_set_slot(w_target, w_message, w_context):
    w_name = w_message.arguments[0].eval(w_context)
    w_value = w_message.arguments[1].eval(w_context)
    assert isinstance(w_name, W_ImmutableSequence)
    w_target.slots[w_name.value] = w_value

# def w_object_get_slot(w_target, w_message, w_context):
#     pass