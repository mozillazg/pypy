from pypy.lang.io.register import register_method
from pypy.lang.io.model import W_Object
from pypy.lang.io.coroutinemodel import W_Coroutine

@register_method('Coroutine', 'currentCoroutine')
def coroutine_get_current(space, w_target, w_message, w_context):
    return W_Coroutine.w_getcurrent(space)
    
@register_method('Coroutine', 'isCurrent')
def coroutine_is_current(space, w_target, w_message, w_context):
    return space.newbool(w_target is W_Coroutine.w_getcurrent(space))
        
@register_method('Coroutine', 'run')
def coroutine_run(space, w_target, w_message, w_context):
    # XXX check this, because w_target.run(space, w_context, w_context) also works, maybe missing some scenarios
    w_target.run(space, w_target, w_target)
    return w_target
    
@register_method('Coroutine', 'resume')
def coroutine_switch(space, w_target, w_message, w_context):
    w_target.switch()