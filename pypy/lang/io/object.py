from pypy.lang.io.register import register_method
from pypy.lang.io.model import W_ImmutableSequence, W_Block, W_Number

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

@register_method('Object', 'hasSlot', unwrap_spec=[object, str])
def w_object_has_slot(space, w_target, name):
    if w_target.lookup(name) is None:
        return space.w_false
    return space.w_true

@register_method('Object', '?')
def w_object_question_mark(space, w_target, w_message, w_context):
    name = w_message.arguments[0].name
    if w_object_has_slot(space, w_target, name) is space.w_false:
        return space.w_nil
    return w_message.arguments[0].eval(space, w_target, w_context)
    
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
    w_message.arguments[0].eval(space, w_target, w_target)
    return w_target
    
@register_method('Object', '', unwrap_spec=[object, object])
def w_object_(space, w_target, w_arg):
    return w_arg


@register_method('Object', 'message')
def object_message(space, w_target, w_message, w_context):
    return w_message.arguments[0]
    
@register_method('Object', '-', unwrap_spec=[object, float])
def object_minus(space, w_target, argument):
    return W_Number(space, -argument)
    
@register_method('Object', 'debugger')
def object_message(space, w_target, w_message, w_context):
    import pdb
    pdb.set_trace()
    return w_target

@register_method('Object', 'for')
def object_for(space, w_target, w_message, w_context):
   argcount = len(w_message.arguments)
   assert argcount >= 4 and argcount <=5

   body = w_message.arguments[-1]
   start = w_message.arguments[1].eval(space, w_target, w_context).value
   stop = w_message.arguments[2].eval(space, w_target, w_context).value
   if argcount == 4:
      step = 1
   else:
      step = w_message.arguments[3].eval(space, w_message, w_context).value
   
      
   key = w_message.arguments[0].name
   
   for i in range(start, stop, step):
      w_context.slots[key] = W_Number(space, i)
      t = body.eval(space, w_context, w_context)
   return t