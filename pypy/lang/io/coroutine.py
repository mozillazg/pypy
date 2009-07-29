from pypy.lang.io.register import register_method
from pypy.lang.io.model import W_Object
from pypy.lang.io.coroutinemodel import W_Coroutine


@register_method('Coroutine', 'currentCoroutine')
def coroutine_get_current(space, w_target, w_message, w_context):
    return W_Coroutine.w_getcurrent(space)
    
@register_method('Coroutine', 'isCurrent')
def coroutine_is_current(space, w_target, w_message, w_context):
    return space.newbool(w_target is W_Coroutine.w_getcurrent(space))