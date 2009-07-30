from pypy.lang.io.register import register_method
from pypy.lang.io.model import W_Message, W_ImmutableSequence

@register_method('Message', 'argAt', unwrap_spec=[object, int])
def message_arg_at(space, w_message, arg_num):
    if arg_num < len(w_message.arguments):
        return w_message.arguments[arg_num]
    return space.w_nil

@register_method('Message', 'arguments')
def message_arguments(space, w_receiver, w_message, w_context):
  return space.w_list.clone_and_init(space, w_receiver.arguments)
 
@register_method('Message', 'name')
def message_name(space, w_receiver, w_message, w_context):
    return space.w_immutable_sequence.clone_and_init(w_receiver.name)

@register_method('Message', 'argsEvaluatedIn')
def message_argsEvaluatedIn(space, w_target, w_message, w_context):
    w_in = w_message.arguments[0].eval(space, w_context, w_context)
    w_arguments = [arg.eval(space, w_in, w_in) for arg in w_target.arguments]
    return space.w_list.clone_and_init(space, w_arguments)
    
    
# @register_method('Message', 'setIsActivatable', unwrap_spec=[object, bool])
# def message_setIsActivatable(space, w_target, setting):
#     w_target.activateable = setting
#     return w_target