from pypy.interpreter.baseobjspace import Wrappable
from pypy.interpreter.error import OperationError
from pypy.interpreter.gateway import unwrap_spec
from pypy.interpreter.typedef import TypeDef
from pypy.rlib import rjvm, rstring
from pypy.rlib.rjvm import java, new_array

class W_JvmObject(Wrappable):
    __slots__ = ('b_obj',)
    typedef = TypeDef('_JvmObject')

    def __init__(self, b_obj):
        self.b_obj = b_obj

# ============== Module API ==============

@unwrap_spec(class_name=str)
def new(space, class_name, args_w):
    b_java_cls = class_for_name(space, class_name)
    args, types = get_args_types(space, args_w)

    constructor = b_java_cls.getConstructor(types)
    try:
        b_obj = constructor.newInstance(args)
    except rjvm.ReflectionException:
        raise raise_runtime_error(space, "Error running constructor")

    w_obj = space.wrap(W_JvmObject(b_obj))

    return w_obj


@unwrap_spec(class_name=str)
def get_methods(space, class_name):
    b_java_cls = class_for_name(space, class_name)
    result = _get_methods(b_java_cls, static=False)
    return wrap_get_methods_result(space, result)


@unwrap_spec(class_name=str)
def get_static_methods(space, class_name):
    b_java_cls = class_for_name(space, class_name)
    result = _get_methods(b_java_cls, static=True)
    return wrap_get_methods_result(space, result)


def _get_fields(space, class_name, static):
    b_java_cls = class_for_name(space, class_name)
    res = []
    fields = b_java_cls.getFields()
    for i in xrange(len(fields)):
        f = fields[i]
        if not is_public(f.getModifiers()): continue
        if static:
            if not is_static(f.getModifiers()): continue
        else:
            if is_static(f.getModifiers()): continue
        res.append(space.wrap(str(f.getName())))
    return space.newtuple(res)


@unwrap_spec(class_name=str)
def get_fields(space, class_name):
    return _get_fields(space, class_name, static=False)

@unwrap_spec(class_name=str)
def get_static_fields(space, class_name):
    return _get_fields(space, class_name, static=True)

@unwrap_spec(class_name=str)
def get_constructors(space, class_name):
    res = []
    b_java_class = class_for_name(space, class_name)

    constructors = b_java_class.getConstructors()
    for i in xrange(len(constructors)):
        c = constructors[i]
        arg_types_names = []
        types = c.getParameterTypes()
        for j in xrange(len(types)):
            arg_types_names.append(space.wrap(get_type_name(types[j])))
        res.append(space.newtuple(arg_types_names))

    return space.newtuple(res)

@unwrap_spec(method_name=str, jvm_obj=W_JvmObject)
def call_method(space, jvm_obj, method_name, args_w):
    b_obj = jvm_obj.b_obj
    args, types = get_args_types(space, args_w)

    b_java_class = b_obj.getClass()

    try:
        b_meth = b_java_class.getMethod(method_name, types)
    except rjvm.ReflectionException:
        raise raise_type_error(space,
                         "No method called %s found in class %s" % (method_name, str(b_java_class.getName())))

    try:
        b_res = b_meth.invoke(b_obj, args)
    except rjvm.ReflectionException:
        raise raise_runtime_error(space, "Error invoking method")

    return wrap_result(space, b_res)


@unwrap_spec(class_name=str, method_name=str)
def call_static_method(space, class_name, method_name, args_w):
    b_java_class = class_for_name(space, class_name)
    args, types = get_args_types(space, args_w)

    try:
        b_meth = b_java_class.getMethod(method_name, types)
    except rjvm.ReflectionException:
        raise raise_type_error(space,
                         "No method called %s found in class %s" % (method_name, str(b_java_class.getName())))

    try:
        b_res = b_meth.invoke(b_java_class, args)
    except rjvm.ReflectionException:
        raise raise_runtime_error(space, "Error invoking method")

    return wrap_result(space, b_res)


@unwrap_spec(jvm_obj=W_JvmObject)
def unbox(space, jvm_obj):
    b_obj = jvm_obj.b_obj
    b_cls = b_obj.getClass()

    if b_cls == java.lang.String.class_:
        b_str = rjvm.downcast(java.lang.String, b_obj)
        return space.wrap(str(b_str))
    elif b_cls == java.lang.Integer.class_:
        b_integer = rjvm.downcast(java.lang.Integer, b_obj)
        return space.wrap(b_integer.intValue())
    elif b_cls == java.lang.Boolean.class_:
        b_bool = rjvm.downcast(java.lang.Boolean, b_obj)
        return space.wrap(bool(b_bool.booleanValue()))
#    elif b_cls == java.lang.Double.class_:
#        b_float = rjvm.downcast(java.lang.Double, b_obj)
#        return space.wrap(b_float.doubleValue())
    else:
        raise OperationError(space.w_TypeError,
                             space.wrap(
                                 "Don't know how to unbox objects of type %s" %
                                 str(b_cls.getName())))


def box(space, w_obj):
    if space.is_true(space.isinstance(w_obj, space.w_str)):
        s = space.str_w(w_obj)
        b_str = rjvm.native_string(s)
        return space.wrap(W_JvmObject(b_str))
    else:
        w_template = space.wrap("Don't know how to box %r")
        w_msg = space.mod(w_template, w_obj)
        raise OperationError(space.w_TypeError, w_msg)


@unwrap_spec(class_name=str)
def superclass(space, class_name):
    b_cls = class_for_name(space, class_name)
    b_superclass = b_cls.getSuperclass()
    if b_superclass:
        return space.wrap(str(b_superclass.getName()))
    else:
        return space.w_None


@unwrap_spec(jvm_obj=W_JvmObject, field_name=str)
def get_field_value(space, jvm_obj, field_name):
    b_obj = space.interp_w(W_JvmObject, jvm_obj).b_obj
    b_class = b_obj.getClass()
    return _get_field_value(space, b_class, b_obj, field_name)


@unwrap_spec(class_name=str, field_name=str)
def get_static_field_value(space, class_name, field_name):
    b_class = class_for_name(space, class_name)
    return _get_field_value(space, b_class, None, field_name)


@unwrap_spec(jvm_obj=W_JvmObject, field_name=str)
def set_field_value(space, jvm_obj, field_name, w_val):
    b_obj = space.interp_w(W_JvmObject, jvm_obj).b_obj
    b_class = b_obj.getClass()

    try:
        b_field = b_class.getField(field_name)
    except rjvm.ReflectionException:
        raise raise_type_error(space, "No field called %s in class %s" % (field_name, str(b_class.getName())))

    if space.is_true(space.isinstance(w_val, space.w_str)):
        b_val = unwrap_arg(space, w_val, 'str')
    elif space.is_true(space.isinstance(w_val, space.w_int)):
        b_val = unwrap_arg(space, w_val, 'int')
    else:
        b_val = unwrap_arg(space, w_val, "some java type hopefully")

    try:
        b_field.set(b_obj, b_val)
    except rjvm.ReflectionException:
        raise raise_runtime_error(space, "Error setting field")

    return space.w_None

@unwrap_spec(class_name=str, field_name=str)
def set_static_field_value(space, class_name, field_name, w_val):
    pass

# ============== Helper functions ==============

def _get_methods(b_java_cls, static):
    by_name_sig = {}
    methods = b_java_cls.getMethods()
    for i in xrange(len(methods)):
        method = methods[i]
        if static:
            if not is_static(method.getModifiers()): continue
        else:
            if is_static(method.getModifiers()): continue

        if not is_public(method.getReturnType().getModifiers()): continue

        if method.getName() not in by_name_sig:
            by_name_sig[method.getName()] = {}

        type_names = []
        types = method.getParameterTypes()
        for j in xrange(len(types)):
            type_names.append(str(get_type_name(types[j])))

        sig = ','.join(type_names)

        if sig not in by_name_sig[method.getName()]:
            by_name_sig[method.getName()][sig] = method
        elif method.isBridge():
            continue
        else:
            by_name_sig[method.getName()][sig] = method
    result = {}
    for name, sig_to_meth in by_name_sig.iteritems():
        if name not in result:
            result[name] = []

        for method in sig_to_meth.itervalues():
            b_return_type_name = get_type_name(method.getReturnType())
            arg_types_names = []
            types = method.getParameterTypes()
            for i in xrange(len(types)):
                arg_types_names.append(get_type_name(types[i]))
            result[name].append((b_return_type_name, arg_types_names))
    return result

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
    args_len = len(args_w)
    types = new_array(java.lang.Class, args_len)
    args = new_array(java.lang.Object, args_len)
    for i, w_arg_type in enumerate(args_w):
        w_arg, w_type = space.unpackiterable(w_arg_type, 2)
        type_name = unwrap_type(space, w_type)
        b_arg = unwrap_arg(space, w_arg, type_name)
        types[i] = type_for_name(space, type_name)
        args[i] = b_arg
    return args, types


def unwrap_type(space, w_type):
    if space.is_true(space.isinstance(w_type, space.w_str)):
        return space.str_w(w_type)
    elif space.is_w(w_type, space.w_str):
        return 'str'
    elif space.is_w(w_type, space.w_int):
        return 'int'
    elif space.is_w(w_type, space.w_bool):
        return 'bool'
#    elif space.is_w(w_type, space.w_float):
#        return 'float'
    else:
        w_template = space.wrap("Don't know how to handle type %r")
        w_msg = space.mod(w_template, w_type)
        raise OperationError(space.w_TypeError, w_msg)


def type_for_name(space, type_name):
    if type_name == 'str':
        return java.lang.String.class_
    elif type_name == 'int':
        return java.lang.Integer.TYPE
    elif type_name == 'bool':
        return java.lang.Boolean.TYPE
#    elif type_name == 'float':
#        return java.lang.Double.TYPE
    else:
        return class_for_name(space, type_name)


def unwrap_arg(space, w_arg, type_name):
    if type_name == 'int':
        return java.lang.Integer(space.int_w(w_arg))
    elif type_name == 'bool':
        return java.lang.Boolean(space.bool_w(w_arg))
#    elif type_name == 'float':
#        return java.lang.Double(space.float_w(w_arg))
    elif type_name == 'str':
        return rjvm.native_string(space.str_w(w_arg))
    else:
        return space.interp_w(W_JvmObject, w_arg).b_obj


def get_type_name(t):
    if t.isArray():
        sb = rstring.StringBuilder()
        sb.append(str(t.getComponentType().getName()))
        sb.append('[]')
        return sb.build()
    else:
        return str(t.getName())

def class_for_name(space, class_name):
    try:
        return java.lang.Class.forName(class_name)
    except rjvm.ReflectionException:
        raise OperationError(space.w_TypeError,
                             space.wrap("Class %s not found!" % class_name))


def raise_runtime_error(space, msg):
    return OperationError(space.w_RuntimeError,
                         space.wrap(msg))


def raise_type_error(space, msg):
    return OperationError(space.w_TypeError, space.wrap(msg))

def wrap_result(space, b_res):
    if b_res:
        w_type_name = space.wrap(str(b_res.getClass().getName()))
        w_res = space.wrap(W_JvmObject(b_res))
        return space.newtuple([w_res, w_type_name])
    else:
        w_type_name = space.wrap('void')
        return space.newtuple([space.w_None, w_type_name])


def _get_field_value(space, b_class, b_obj, field_name):
    try:
        b_field = b_class.getField(field_name)
    except rjvm.ReflectionException:
        raise raise_type_error(space, "No field called %s in class %s" % (
            field_name, str(b_class.getName())))
    try:
        b_res = b_field.get(b_obj)
    except rjvm.ReflectionException:
        raise raise_runtime_error(space, "Error getting field")
    return wrap_result(space, b_res)
