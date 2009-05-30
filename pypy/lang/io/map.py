from pypy.lang.io.register import register_method
from pypy.lang.io.model import W_ImmutableSequence
@register_method('Map', 'atPut', unwrap_spec=[object, object, object])
def map_at_put(space, w_target, w_key, w_value):
    assert isinstance(w_key, W_ImmutableSequence)
    w_target.at_put(w_key, w_value)
    return w_target
    
@register_method('Map', 'at', unwrap_spec=[object, object])
def map_at(space, w_target, w_key):
    assert isinstance(w_key, W_ImmutableSequence)
    return w_target.at(w_key)