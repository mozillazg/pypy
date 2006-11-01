
""" Some transparent helpers, put here because
of cyclic imports
"""

from pypy.objspace.std.model import W_ANY

def create_mm_names(classname, mm, is_local):
    s = ""
    if is_local:
        s += "list_"
    s += mm.name + "__"
    s += "_".join([classname] + ["ANY"] * (mm.arity - 1))
    if '__' + mm.name + '__' in mm.specialnames:
        return s, '__' + mm.name + '__'
    return s, mm.name

def install_mm_trampoline(type_, mm, is_local):
    classname = type_.__name__[2:]
    mm_name, op_name = create_mm_names(classname, mm, is_local)
    def function(space, w_transparent_list, *args_w):
        return space.call_function(w_transparent_list.controller, space.wrap\
            (op_name), *args_w)
    function.func_name = mm_name
    mm.register(function, type_, *([W_ANY] * (mm.arity - 1)))

def register_type(type_):
    from pypy.objspace.std.stdtypedef import multimethods_defined_on
    
    for mm, is_local in multimethods_defined_on(type_.original):
        if not mm.name.startswith('__'):
            install_mm_trampoline(type_, mm, is_local)
