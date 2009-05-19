from pypy.lang.io.register import register_method
from pypy.lang.io.model import W_ImmutableSequence, W_Block

@register_method('Object', 'setSlot', unwrap_spec=[object, str, object])
def w_object_set_slot(space, w_target, name, w_value):
    w_target.slots[name] = w_value
    return w_value
    
@register_method('Object', 'getSlot', unwrap_spec=[object, str])
def w_object_get_slot(space, w_target, name):
    try:
        return w_target.slots[name]
    except KeyError:
        return space.w_nil

@register_method('Object', 'method')
def w_object_method(space, w_target, w_message, w_context):
    w_body = w_message.arguments[-1]
    w_arguments = w_message.arguments[:-1]
    names = [x.name for x in w_arguments]
    return space.w_block.clone_and_init(space, names, w_body, True)

@register_method('Object', 'block')
def w_object_block(space, w_target, w_message, w_context):
    w_body = w_message.arguments[-1]
    w_arguments = w_message.arguments[:-1]
    names = [x.name for x in w_arguments]
    return space.w_block.clone_and_init(space, names, w_body, False)
    
@register_method('Object', 'clone', unwrap_spec=[object])
def w_object_clone(space, w_target):
    return w_target.clone()

@register_method('Object', 'list')
def w_object_list(space, w_target, w_message, w_context):
    w_items = [x.eval(space, w_target, w_context) for x in w_message.arguments]
    return space.w_list.clone_and_init(space, w_items)
    
@register_method('Object', 'do')
def w_object_do(space, w_target, w_message, w_context):
    w_message.arguments[0].eval(space, w_target, w_context)
    return w_target