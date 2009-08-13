from pypy.lang.io.register import register_method
from pypy.lang.io.model import W_Message, W_ImmutableSequence

@register_method('Sequence', '..', unwrap_spec=[object, str])
def sequence_append(space, w_sequence, w_append_seq):
    s = space.w_sequence.clone()
    s.value = w_sequence.value + w_append_seq
    return s
    
@register_method('Sequence', 'asCapitalized')
def sequence_as_capitalized(space, w_target, w_message, w_context):
    s = space.w_sequence.clone()
    s.value = w_target.value.capitalize()
    return s 