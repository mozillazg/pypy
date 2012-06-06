from pypy.interpreter.baseobjspace import Wrappable
from pypy.interpreter.error import OperationError
from pypy.interpreter.typedef import TypeDef
from pypy.rlib import rjvm, rstring
from pypy.rlib.rjvm import java, native_string


class W_JvmObject(Wrappable):
    """
    All 'native' objects are represented by instances of this class at
    app-level. Objects of this type have no methods or fields, so
    users have to use functions from this file to operate on them (or
    the high-level API from app-level.py).

    This is called _JvmObject at app-level.
    """
    __slots__ = ('b_obj',)
    typedef = TypeDef('_JvmObject')

    def __init__(self, b_obj):
        self.b_obj = b_obj

def wrap_get_methods_result(space, result):
    """
    Result of get_methods is a dict from method names to lists of signatures.
    Each signature is a tuple of the form (return type, arg_types) where
    arg_types is a list of type names.

    We want to wrap the whole structure.
    """
    w_result = space.newdict()

    for name, sigs in result.iteritems():
        w_key = space.wrap(str(name))
        value = []

        for b_ret_type, args_b in sigs:
            w_ret_type = space.wrap(str(b_ret_type))
            args_w = [space.wrap(str(b_arg)) for b_arg in args_b]
            w_args = space.newtuple(args_w)
            w_entry = space.newtuple([w_ret_type, w_args])
            value.append(w_entry)

        w_value = space.newlist(value)

        space.setitem(w_result, w_key, w_value)

    return w_result


def is_static(m):
    return java.lang.reflect.Modifier.isStatic(m)


def is_public(m):
    return java.lang.reflect.Modifier.isPublic(m)


def get_args_types(space, args_w):
    """
    Turn a list of wrapped tuples of the form (arg, type) into an rjvm array
    of java.lang.Objects and another of java.lang.Classes.
    """
    args_len = len(args_w)
    types = rjvm.new_array(java.lang.Class, args_len)
    args = rjvm.new_array(java.lang.Object, args_len)
    for i, w_arg_type in enumerate(args_w):
        w_arg, w_type = space.unpackiterable(w_arg_type, 2)
        types[i] = unwrap_type(space, w_type)
        args[i] = unwrap_arg(space, w_arg)
    return args, types


def unwrap_type(space, w_type):
    """
    Turn an app-level 'type description' into an instance of java.lang.Class.
    See jvm.call_method.
    """
    if space.is_true(space.isinstance(w_type, space.w_str)):
        class_name = space.str_w(w_type)
        return class_for_name(space, class_name)
    elif space.is_w(w_type, space.w_str):
        return java.lang.String.class_
    elif space.is_w(w_type, space.w_int):
        return java.lang.Integer.TYPE
    elif space.is_w(w_type, space.w_bool):
        return java.lang.Boolean.TYPE
    elif space.is_w(w_type, space.w_float):
        return java.lang.Double.TYPE
    else:
        w_template = space.wrap("Don't know how to handle type %r")
        w_msg = space.mod(w_template, w_type)
        raise OperationError(space.w_TypeError, w_msg)


def unwrap_arg(space, w_arg):
    """
    Turn an app-level object into an instance of java.lang.Object.
    """

    # watch out! isinstance(True, int) holds in Python! Check for bool *before* int.
    if space.is_true(space.isinstance(w_arg, space.w_bool)):
        return java.lang.Boolean(space.bool_w(w_arg))
    elif space.is_true(space.isinstance(w_arg, space.w_int)):
        return java.lang.Integer(space.int_w(w_arg))
    elif space.is_true(space.isinstance(w_arg, space.w_float)):
        return java.lang.Double(space.float_w(w_arg))
    elif space.is_true(space.isinstance(w_arg, space.w_str)):
        return rjvm.native_string(space.str_w(w_arg))
    elif isinstance(w_arg, W_JvmObject):
        return space.interp_w(W_JvmObject, w_arg).b_obj
    else:
        w_template = space.wrap("Don't know how to handle %r")
        w_msg = space.mod(w_template, w_arg)
        raise OperationError(space.w_TypeError, w_msg)


def get_type_name(b_type):
    if b_type.isArray():
        sb = rstring.StringBuilder()
        sb.append(str(b_type.getComponentType().getName()))
        sb.append('[]')
        return sb.build()
    else:
        return str(b_type.getName())

def class_for_name(space, class_name):
    b_class_name = native_string(class_name)
    try:
        return java.lang.Class.forName(b_class_name)
    except rjvm.ReflectionException:
        raise OperationError(space.w_TypeError,
                             space.wrap("Class %s not found!" % class_name))


def raise_runtime_error(space, msg):
    return OperationError(space.w_RuntimeError,
                          space.wrap(msg))


def raise_type_error(space, msg):
    return OperationError(space.w_TypeError, space.wrap(msg))


def wrap_result(space, b_result, b_static_result_class):
    """
    Wrap an native object in a tuple of W_JvmObject and type name as string.
    If the dynamic type of the result is public, use it. If not (for example it's
    a private implementation of an interface) use the statically known result type.
    """
    if b_result:
        b_result_class = b_result.getClass()
        if not is_public(b_result_class.getModifiers()):
            b_result_class = b_static_result_class

        w_type_name = space.wrap(str(b_result_class.getName()))
        w_res = space.wrap(W_JvmObject(b_result))
        return space.newtuple([w_res, w_type_name])
    else:
        w_type_name = space.wrap('void')
        return space.newtuple([space.w_None, w_type_name])
