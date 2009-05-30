from pypy.lang.io.register import register_method

@register_method('Map', 'atPut', unwrap_spec=[object, object, object])
def map_at_put(space, w_target, w_key, w_value):
    w_target.at_put(w_key, w_value)
    return w_target
    
@register_method('Map', 'at', unwrap_spec=[object, object])
def map_at(space, w_target, w_key):
    return w_target.at(w_key)