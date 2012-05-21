from pypy.interpreter.error import OperationError
from pypy.interpreter.gateway import unwrap_spec
from pypy.module.jvm import interp_helpers as helpers
from pypy.module.jvm.interp_helpers import W_JvmObject
from pypy.rlib import rjvm
from pypy.rlib.rjvm import java

# ============== Interp-level module API ==============

@unwrap_spec(class_name=str)
def new(space, class_name, args_w):
    """
    Create an instance of the specified class. Pass any arguments to the
    constructor. Format of the arguments is the same as in call_method.

    Returns the instance wrapped in W_JvmObject.
    """
    b_java_cls = helpers.class_for_name(space, class_name)
    args, types = helpers.get_args_types(space, args_w)

    constructor = b_java_cls.getConstructor(types)
    try:
        b_obj = constructor.newInstance(args)
    except rjvm.ReflectionException:
        raise helpers.raise_runtime_error(space, "Error running constructor")

    w_obj = space.wrap(W_JvmObject(b_obj))

    return w_obj


@unwrap_spec(class_name=str)
def get_methods(space, class_name):
    """
    Returns a (wrapped) dict with one entry for every instance method name.
    Each value is a tuple which consists of the name of the result and a tuple
    of argument types names.
    """
    b_java_cls = helpers.class_for_name(space, class_name)
    result = _get_methods(b_java_cls, static=False)
    return helpers.wrap_get_methods_result(space, result)


@unwrap_spec(class_name=str)
def get_static_methods(space, class_name):
    """
    The equivalent of get_methods for static methods.
    """
    b_java_cls = helpers.class_for_name(space, class_name)
    result = _get_methods(b_java_cls, static=True)
    return helpers.wrap_get_methods_result(space, result)


@unwrap_spec(class_name=str)
def get_fields(space, class_name):
    """
    Returns a wrapped list of instance fields names.
    """
    return _get_fields(space, class_name, static=False)


@unwrap_spec(class_name=str)
def get_static_fields(space, class_name):
    """
    Returns a wrapped list of static fields names.
    """
    return _get_fields(space, class_name, static=True)


@unwrap_spec(class_name=str)
def get_constructors(space, class_name):
    """
    Returns a wrapped tuple of overloaded constructor versions for the given
    class name. Each version is described as a tuple of argument types names.
    """
    res = []
    b_java_class = helpers.class_for_name(space, class_name)

    constructors = b_java_class.getConstructors()
    for i in xrange(len(constructors)):
        c = constructors[i]
        arg_types_names = []
        types = c.getParameterTypes()
        for j in xrange(len(types)):
            arg_types_names.append(space.wrap(helpers.get_type_name(types[j])))
        res.append(space.newtuple(arg_types_names))

    return space.newtuple(res)


@unwrap_spec(class_name=str, method_name=str, jvm_obj=W_JvmObject)
def call_method(space, jvm_obj, class_name, method_name, args_w):
    """
    Calls method with the given name on the given object, which should be a
    W_JvmObject. Any arguments should be of the form (arg, type) where arg is
    either a W_JvmObject or a 'primitive' value (str, int, bool, float), and
    type is either one of (str, int, bool, float) or a string with a JVM class
    name. The types have to match one of the overloaded versions exactly.

    Returns the result and a string with the result type name. JVM primitives
    are returned boxed. Use jvm.unbox() on them.
    """
    b_obj = jvm_obj.b_obj
    args, types = helpers.get_args_types(space, args_w)

    b_java_class = helpers.class_for_name(space, class_name)

    try:
        b_meth = b_java_class.getMethod(method_name, types)
    except rjvm.ReflectionException:
        raise helpers.raise_type_error(space,
                         "No method called %s found in class %s" % (method_name, str(b_java_class.getName())))

    try:
        b_res = b_meth.invoke(b_obj, args)
    except rjvm.ReflectionException:
        raise helpers.raise_runtime_error(space, "Error invoking method")

    return helpers.wrap_result(space, b_res, b_meth.getReturnType())


@unwrap_spec(class_name=str, method_name=str)
def call_static_method(space, class_name, method_name, args_w):
    """
    Equivalent of call_method for static methods.
    """
    b_java_class = helpers.class_for_name(space, class_name)
    args, types = helpers.get_args_types(space, args_w)

    try:
        b_meth = b_java_class.getMethod(method_name, types)
    except rjvm.ReflectionException:
        raise helpers.raise_type_error(space,
                         "No method called %s found in class %s" % (method_name, str(b_java_class.getName())))

    try:
        b_res = b_meth.invoke(b_java_class, args)
    except rjvm.ReflectionException:
        raise helpers.raise_runtime_error(space, "Error invoking method")

    return helpers.wrap_result(space, b_res, b_meth.getReturnType())


@unwrap_spec(jvm_obj=W_JvmObject)
def unbox(space, jvm_obj):
    """
    Unbox an JVM instance. Returns an app-level primitive value.
    """
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
        # JPype returns booleans as 0 and 1, so use bool() here. This is a no-op
        # after compilation.
        return space.wrap(bool(b_bool.booleanValue()))
    elif b_cls == java.lang.Double.class_:
        b_float = rjvm.downcast(java.lang.Double, b_obj)
        return space.wrap(b_float.doubleValue())
    else:
        msg = "Don't know how to unbox objects of type %s" % str(b_cls.getName())
        raise OperationError(space.w_TypeError, space.wrap(msg))


def box(space, w_obj):
    """
    Returns the boxed value wrapped in a W_JvmObject.
    """
    if isinstance(w_obj, W_JvmObject):
        raise OperationError(space.w_TypeError, space.wrap("This object is already boxed!"))

    b_obj = helpers.unwrap_arg(space, w_obj)
    return space.wrap(W_JvmObject(b_obj))


@unwrap_spec(class_name=str)
def superclass(space, class_name):
    """
    Given name of a class return a name of its superclass or None when there
    is none.
    """
    b_cls = helpers.class_for_name(space, class_name)
    b_superclass = b_cls.getSuperclass()
    if b_superclass:
        return space.wrap(str(b_superclass.getName()))
    elif b_cls.isInterface():
        return space.wrap('java.lang.Object')
    else:
        return space.w_None


@unwrap_spec(jvm_obj=W_JvmObject, field_name=str)
def get_field_value(space, jvm_obj, field_name):
    """
    Fetch the value of the given field from the given object. Returns the
    result in the same format as call_method.
    """
    b_obj = space.interp_w(W_JvmObject, jvm_obj).b_obj
    b_class = b_obj.getClass()
    return _get_field_value(space, b_class, b_obj, field_name)


@unwrap_spec(class_name=str, field_name=str)
def get_static_field_value(space, class_name, field_name):
    """
    Equivalent of get_field_value for static fields.
    """
    b_class = helpers.class_for_name(space, class_name)
    return _get_field_value(space, b_class, b_class, field_name)


@unwrap_spec(jvm_obj=W_JvmObject, field_name=str)
def set_field_value(space, jvm_obj, field_name, w_val):
    """
    Sets the value of a given field on a given object to a given value.
    Returns None.
    """
    b_obj = space.interp_w(W_JvmObject, jvm_obj).b_obj
    _set_field_value(space, b_obj.getClass(), b_obj, field_name, w_val)


@unwrap_spec(class_name=str, field_name=str)
def set_static_field_value(space, class_name, field_name, w_val):
    """
    Equivalent of set_field_value for static fields.
    """
    b_class = helpers.class_for_name(space, class_name)
    _set_field_value(space, b_class, b_class, field_name, w_val)

# ============== Common code for some of the functions above ==============

def _get_fields(space, class_name, static):
    """
    The logic behind get_(static)_fields.
    """
    b_java_cls = helpers.class_for_name(space, class_name)
    res = []
    fields = b_java_cls.getFields()
    for i in xrange(len(fields)):
        f = fields[i]
        if not helpers.is_public(f.getModifiers()): continue
        if static:
            if not helpers.is_static(f.getModifiers()): continue
        else:
            if helpers.is_static(f.getModifiers()): continue
        res.append(space.wrap(str(f.getName())))
    return space.newtuple(res)


def _get_methods(b_java_cls, static):
    """
    The logic behind get_(static)_methods. Discards non-public methods and
    bridge versions on overloaded methods. The result is unwrapped and has
    to be passed to wrap_get_methods_result().
    """
    by_name_sig = {}
    methods = b_java_cls.getMethods()

    # Hide non-public or bridge methods.
    for i in xrange(len(methods)):
        method = methods[i]
        if static:
            if not helpers.is_static(method.getModifiers()): continue
        else:
            if helpers.is_static(method.getModifiers()): continue

        if not helpers.is_public(method.getReturnType().getModifiers()): continue

        if method.getName() not in by_name_sig:
            by_name_sig[method.getName()] = {}

        type_names = []
        types = method.getParameterTypes()
        for j in xrange(len(types)):
            type_names.append(str(helpers.get_type_name(types[j])))

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
            b_return_type_name = helpers.get_type_name(method.getReturnType())
            arg_types_names = []
            types = method.getParameterTypes()
            for i in xrange(len(types)):
                arg_types_names.append(helpers.get_type_name(types[i]))
            result[name].append((b_return_type_name, arg_types_names))
    return result


def _get_field_value(space, b_class, b_obj, field_name):
    """
    The logic behind get_(static)_field_value.
    """
    try:
        b_field = b_class.getField(field_name)
    except rjvm.ReflectionException:
        raise helpers.raise_type_error(space, "No field called %s in class %s" % (
            field_name, str(b_class.getName())))
    try:
        b_res = b_field.get(b_obj)
    except rjvm.ReflectionException:
        raise helpers.raise_runtime_error(space, "Error getting field")
    return helpers.wrap_result(space, b_res, b_field.getType())


def _set_field_value(space, b_class, b_obj, field_name, w_val):
    """
    The logic behind set_(static)_field_value.
    """
    try:
        b_field = b_class.getField(field_name)
    except rjvm.ReflectionException:
        msg = "No field called %s in class %s" % (field_name, str(b_class.getName()))
        raise helpers.raise_type_error(space, msg)

    b_val = helpers.unwrap_arg(space, w_val)

    try:
        b_field.set(b_obj, b_val)
    except rjvm.ReflectionException:
        raise helpers.raise_runtime_error(space, "Error setting field")
