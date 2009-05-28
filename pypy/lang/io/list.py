from pypy.lang.io.register import register_method
from pypy.lang.io.model import W_Number
@register_method('List', 'append')
def list_append(space, w_target, w_message, w_context):
    assert w_message.arguments,  'requires at least one argument'
    items_w = [x.eval(space, w_target, w_context) for x in w_message.arguments]
    w_target.extend(items_w)
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
    
@register_method('List', 'with')
def list_with(space, w_target, w_message, w_context):
    new_w_list = w_target.clone()
    items_w = [x.eval(space, w_target, w_context) for x in w_message.arguments]
    new_w_list.extend(items_w)
    return new_w_list
    
# TODO: Not sure if this is rpython
@register_method('List', 'indexOf', unwrap_spec=[object, object])
def list_index_of(space, w_target, item):
    try:
        return W_Number(space, w_target.items.index(item))
    except ValueError, e:
        return space.w_nil

# TODO: Not sure if this is rpython
@register_method('List', 'contains', unwrap_spec=[object, object])
def list_contains(space, w_target, item):
    if item in w_target.items:
        return space.w_true
    return space.w_false
    
@register_method('List', 'size')
def list_size(space, w_target, w_message, w_context):
    return W_Number(space, len(w_target.items))
    
@register_method('List', 'first')
def list_size(space, w_target, w_message, w_context):
    if len(w_message.arguments) != 0:
        t = w_message.arguments[0].eval(space, w_target, w_context)
        assert isinstance(t, W_Number)
        nfirst = t.value
    else:
        nfirst = 1
    
    if len(w_target.items) == 0 and nfirst == 1:
        return space.w_nil

    flist_w = w_target.clone()
    if nfirst < 1:
        flist_w.items = []
    else:
        flist_w.items = flist_w.items[0:nfirst]
    return flist_w