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
    
@register_method('List', 'foreach')
def list_foreach(space, w_target, w_message, w_context):
    argcount = len(w_message.arguments)
    assert argcount > 0
    
    body = w_message.arguments[-1]
    if argcount == 3:
        key = w_message.arguments[0].name
        value = w_message.arguments[1].name

        for i in range(len(w_target.items)):
            w_context.slots[key] = W_Number(space, i)
            w_context.slots[value] = w_target.items[i]
            t = body.eval(space, w_context, w_context)
    elif argcount == 2:
        value = w_message.arguments[0].name

        for i in range(len(w_target.items)):
            w_context.slots[value] = w_target.items[i]
            t = body.eval(space, w_context, w_context)
    
    elif argcount == 1:
        for i in range(len(w_target.items)):
            t = body.eval(space, w_context, w_context)

    return t 