from pypy.lang.io.register import register_method

@register_method('Map', 'atPut', unwrap_spec=[object, object, object])
def map_at_put(space, target, key, value):
    target.items[key] = value
    return target