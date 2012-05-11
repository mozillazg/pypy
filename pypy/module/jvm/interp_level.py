import os
from pypy.interpreter.baseobjspace import Wrappable
from pypy.interpreter.error import OperationError
from pypy.interpreter.gateway import ApplevelClass, unwrap_spec
from pypy.interpreter.typedef import TypeDef
from pypy.rlib import rjvm
from pypy.rlib.rjvm import java, new_array

class W_JvmObject(Wrappable):

    typedef = TypeDef('_JvmObject')

    def __init__(self, space, b_obj):
        self.space = space
        self.b_obj = b_obj


@unwrap_spec(class_name=str)
def new(space, class_name, args_w):
    b_java_cls = java.lang.Class.forName(class_name)
    args, types = get_args_types(space, args_w)

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

@unwrap_spec(method_name=str, jvm_obj=W_JvmObject)
def call_method(space, jvm_obj, method_name, args_w):
    b_obj = jvm_obj.b_obj
    args, types = get_args_types(space, args_w)

    b_java_class = b_obj.getClass()
    b_meth = b_java_class.getMethod(method_name, types)
    b_res = b_meth.invoke(b_obj, args)
    w_type_name = space.wrap(str(b_res.getClass().getName()))
    w_res = space.wrap(W_JvmObject(space, b_res))

    return space.newtuple([w_res, w_type_name])

@unwrap_spec(jvm_obj=W_JvmObject)
def unbox(space, jvm_obj):
    #TODO compare classes not names
    b_obj = jvm_obj.b_obj
    class_name = str(b_obj.getClass().getName())

    if class_name == 'java.lang.String':
        b_str = rjvm.downcast(java.lang.String, b_obj)
        return space.wrap(str(b_str))
    elif class_name == 'java.lang.Integer':
        b_integer = rjvm.downcast(java.lang.Integer, b_obj)
        return space.wrap(b_integer.intValue())
    else:
        raise OperationError(space.w_TypeError,
                             space.wrap("Don't know how to unbox objects of type %s" %
                                        class_name))

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

def get_args_types(space, args_w):
    args_len = len(args_w)
    types = new_array(java.lang.Class, args_len)
    args = new_array(java.lang.Object, args_len)
    for i, w_arg_type in enumerate(args_w):
        w_arg, w_type = space.unpackiterable(w_arg_type, 2)
        type_name = space.str_w(w_type)
        b_arg = space.interp_w(W_JvmObject, w_arg).b_obj
        types[i] = java.lang.Class.forName(type_name)
        args[i] = b_arg
    return args, types
