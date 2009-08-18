from pypy.lang.io.register import register_method
from pypy.lang.io.model import W_Object
from pypy.lang.io.coroutinemodel import W_Coroutine

@register_method('Coroutine', 'currentCoroutine')
def coroutine_get_current(space, w_target, w_message, w_context):
    return W_Coroutine.w_getcurrent(space)
    
@register_method('Coroutine', 'isCurrent')
def coroutine_is_current(space, w_target, w_message, w_context):
    return space.newbool(w_target is W_Coroutine.w_getcurrent(space))
    
@register_method('Coroutine', 'setRunMessage', unwrap_spec=[object, object])
def coroutine_setRunMessage(space, w_coroutine, w_message):
    w_coroutine.slots['runMessage'] = w_message
    return w_coroutine
    
@register_method('Coroutine', 'run')
def coroutine_run(space, w_target, w_message, w_context):
    w_target.run(space, w_target, w_context)
    return w_target
    
# @register_method('Coroutine', 'setResult', unwrap_spec=[object, object])
# def coroutine_set_result(space, w_coro, w_result):
#     print w_result
#     w_coro.slots['result'] = w_result
#     return w_coro
#     

@register_method('Coroutine', 'resume')
def coroutine_switch(space, w_target, w_message, w_context):
    w_target.switch()