import os
from pypy.interpreter.baseobjspace import Wrappable
from pypy.interpreter.gateway import ApplevelClass, unwrap_spec
from pypy.interpreter.typedef import TypeDef
from pypy.rlib.rjvm import java, new_array

class W_JvmObject(Wrappable):

    typedef = TypeDef('_JvmObject')

    def __init__(self, space, b_obj):
        self.space = space
        self.b_obj = b_obj


@unwrap_spec(class_name=str)
def new(space, class_name, args_w):
    b_java_cls = java.lang.Class.forName(class_name)
    args_len = len(args_w)
    types = new_array(java.lang.Class, args_len)
    args = new_array(java.lang.Object, args_len)

    for i, w_arg_type in enumerate(args_w):
        w_arg, w_type = space.unpackiterable(w_arg_type, 2)
        type_name = space.str_w(w_type)
        b_arg = space.interp_w(W_JvmObject, w_arg).b_obj
        types[i] = java.lang.Class.forName(type_name)
        args[i] = b_arg

    constructor = b_java_cls.getConstructor(types)

    b_obj = constructor.newInstance(args)
    w_obj = space.wrap(W_JvmObject(space, b_obj))

    return w_obj

@unwrap_spec(class_name=str)
def get_methods(space, class_name):
    b_java_cls = java.lang.Class.forName(class_name)
    result = {}

    for method in b_java_cls.getMethods():
        if is_static(method): continue
        if not is_public(method.getReturnType()): continue

        if method.getName() not in result:
            result[method.getName()] = []

        b_return_type_name = method.getReturnType().getName()
        arg_types_names_b = [t.getName() for t in method.getParameterTypes()]

        result[method.getName()].append((b_return_type_name, arg_types_names_b))

    return wrap_get_methods_result(space, result)

def wrap_get_methods_result(space, result):
    """
    Result of get_methods is a dict from method names to lists of signatures.
    Each signature is a tuple of the form (return type, arg_types) where
    arg_types is a list of type names.

    We want to wrap the whole structure. All strings are 'native' and have
    to be cast to str.
    """
    w_result = space.newdict()

    for name, sigs in result.iteritems():
        w_key = space.wrap(str(name))
        value = []

        for b_ret_type, args_b in sigs:
            w_ret_type = space.wrap(str(b_ret_type))
            args_w = [space.wrap(str(b_arg)) for b_arg in args_b]
            w_args = space.newlist(args_w)
            w_entry = space.newtuple([w_ret_type, w_args])
            value.append(w_entry)

        w_value = space.newlist(value)

        space.setitem(w_result, w_key, w_value)

    return w_result

def is_static(method):
    return java.lang.reflect.Modifier.isStatic(method.getModifiers())

def is_public(cls):
    return java.lang.reflect.Modifier.isPublic(cls.getModifiers())

