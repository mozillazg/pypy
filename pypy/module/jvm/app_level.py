import jvm

# ============== App-level module API =======================

# Design of the classes below is based on rjvm.py and the clr module.

class JvmPackageWrapper(object):
    """
    getattr on packages can form new packages or create "JVM classes",
    depending on whether the first letter of the attribute is upper
    or lower case.
    """
    def __init__(self, name):
        self.__name = name

    def __getattr__(self, attr):
        new_name = '{0}.{1}'.format(self.__name, attr)
        if attr[0].isupper():
            return get_class(new_name)
        else:
            if new_name not in packages_cache:
                packages_cache[new_name] = JvmPackageWrapper(new_name)
            return packages_cache[new_name]


class JvmMethodWrapper(object):
    def __init__(self, meth_name, overloads):
        self.meth_name = meth_name
        self.overloads = overloads

    def __get__(self, obj, _):
        assert obj is not None, "No unbound methods for now..."
        return JvmBoundMethod(self.meth_name, self.overloads, obj)


class JvmBoundMethod(object):
    """
    JvmBoundMethods will invoke jvm.call_method(...) when called, handling
    method overloading and turning the result into something useful.
    """
    def __init__(self, method_name, overloads, obj):
        self.method_name = method_name
        self.obj = obj
        self.overloads = overloads

    def __call__(self, *args):
        args_with_types = find_overload(self.overloads, args)
        res, tpe = jvm.call_method(self.obj._inst, self.obj._class_name, self.method_name, *args_with_types)
        return handle_result(res, tpe)

    def __repr__(self):
        return '<bound JVM method %s.%s of %s>' % (self.obj._class_name,
                                                   self.method_name,
                                                   self.obj)


class JvmStaticMethod(object):
    """
    The static equivalent of JvmBoundMethod.
    """
    def __init__(self, class_name, method_name, overloads):
        self.class_name = class_name
        self.method_name = method_name
        self.overloads = overloads

    def __call__(self, *args):
        args_with_types = find_overload(self.overloads, args)
        res, tpe = jvm.call_static_method(self.class_name, self.method_name, *args_with_types)
        return handle_result(res, tpe)


class JvmFieldWrapper(object):
    """
    A descriptor that delegates __get__ and __set__ to the low-level jvm functions.
    """
    def __init__(self, field_name, class_name, is_static):
        self.field_name = field_name
        self.is_static = is_static
        self.class_name = class_name

    def __get__(self, obj, _):
        self.check_staticness(obj)

        if self.is_static:
            res, tpe = jvm.get_static_field_value(self.class_name, self.field_name)
        else:
            res, tpe = jvm.get_field_value(obj._inst, self.field_name)

        return handle_result(res, tpe)

    def __set__(self, obj, value):
        self.check_staticness(obj)

        if isinstance(value, _JavaObjectWrapper):
            value = value._inst

        if self.is_static:
            jvm.set_static_field_value(self.class_name, self.field_name, value)
        else:
            jvm.set_field_value(obj._inst, self.field_name, value)

    def check_staticness(self, obj):
        if obj is None and not self.is_static:
            raise TypeError("%s is not static!" % self.field_name)
        elif obj is not None and self.is_static:
            raise TypeError("%s is static!" % self.field_name)


# 'main entry point' to the jvm module
java = JvmPackageWrapper('java')


# ==================== Helper code =======================


class _JavaObjectWrapper(object):
    """
    All generated "JVM classes" derive from _JavaObjectWrapper, so you can
    do an isinstance(...) check to see if you're dealing with an JVM object.
    """
    def __init__(self, inst, class_name):
        self._inst = inst
        self._class_name = class_name

unboxable_types = {'java.lang.String', 'java.lang.Integer', 'java.lang.Boolean', 'java.lang.Double'}
type_mapping = {'int': int, 'boolean': bool, 'java.lang.String': str, 'double': float}

def is_subclass(c1, c2):
    """
    Returns True iff c2 is a subclass of c1. c1 and c2 are represented as strings
    containing names of the classes.
    """
    c = c2
    while c is not None:
        if c == c1:
            return True
        c = jvm.superclass(c)
    return False

def __make_app_class(class_name):
    """
    DON'T USE THIS DIRECTLY! Use get_class instead.

    Generates a new class for a given (fully qualified) JVM class name. The new
    class prepends "Java" to its name, so java.lang.StringBuilder becomes
    JavaStringBuilder. __dict__ of the new class contains entries for all static
    and instance fields and methods of the class (which are public).
    """
    methods = jvm.get_methods(class_name)
    static_methods = jvm.get_static_methods(class_name)
    fields = jvm.get_fields(class_name)
    static_fields = jvm.get_static_fields(class_name)

    dct = {}

    for method_name, versions in methods.iteritems():
        dct[method_name] = JvmMethodWrapper(method_name, versions)

    for method_name, versions in static_methods.iteritems():
        dct[method_name] = JvmStaticMethod(class_name, method_name, versions)

    for field_name in fields:
        dct[field_name] = JvmFieldWrapper(field_name, class_name, is_static=False)

    for field_name in static_fields:
        dct[field_name] = JvmFieldWrapper(field_name, class_name, is_static=True)

    def make_init(class_name):
        def init(self, *args, **kwargs):
            if '_inst' in kwargs:
                _inst = kwargs['_inst']
            else:
                _inst = construct(class_name, args)
            _JavaObjectWrapper.__init__(self, _inst, class_name)

        return init

    dct['__init__'] = make_init(class_name)

    cls = type('Java' + class_name.split('.')[-1], (_JavaObjectWrapper,), dct)

    return cls

classes_cache = {}
packages_cache = {}

def get_class(class_name):
    """
    This is __make_app_class with memoization. Makes sure two different JVM
    objects of the same JVM type have the same Python-level type.
    """
    if class_name not in classes_cache:
        classes_cache[class_name] = __make_app_class(class_name)
    return classes_cache[class_name]

def handle_result(res, tpe):
    """
    Wrap a bare _JvmObject in a rich wrapper (see __make_app_class). Unbox
    primitive values, turn null results into None.
    """
    if tpe in unboxable_types:
        return jvm.unbox(res)
    elif tpe == 'void':
        assert res is None
        return None
    else:
        cls = get_class(tpe)
        return cls(_inst=res)

def add_types(version, args):
    """
    Annotate args with types, according to the chosen overloaded version of
    a method. The result is suitable for use with jvm.new or jvm.call_method.
    """
    res = []
    for arg, name in zip(args, version):
        tpe = type_mapping.get(name, name)

        if isinstance(arg, _JavaObjectWrapper):
            arg = arg._inst
        elif isinstance(arg, str) and name != 'java.lang.String':
            arg = jvm.box(arg)

        res.append((arg, tpe))

    return res


def find_overload(overloads, args):
    """
    Finds the right overload based on the provided args. Return args
    annotated with proper types.
    """
    cadidates = set()
    for ret_tpe, version in overloads:
        if exact_match(version, args):
            return add_types(version, args)
        elif nonexact_match(version, args):
            cadidates.add(version)
    assert len(cadidates) > 0, "No overloads found!"
    assert len(cadidates) == 1, "Bad overloading, please use explicit casts."
    match, = cadidates
    return add_types(match, args)


def exact_match(types, args):
    """
    Check if args match the types signature exactly.
    """
    if len(types) != len(args):
        return False

    if not types:
        return True

    for tpe_name, arg in zip(types, args):
        if isinstance(arg, _JavaObjectWrapper) and arg._class_name != tpe_name:
            return False
        else:
            return type(arg) is type_mapping.get(tpe_name)


def nonexact_match(types, args):
    """
    Check if args match the types signature at all.
    """
    if len(types) != len(args):
        return False

    for tpe_name, arg in zip(types, args):
        if isinstance(arg, _JavaObjectWrapper):
            cls_name = arg._class_name
            return is_subclass(tpe_name, cls_name)
        elif isinstance(arg, str):
            cls_name = 'java.lang.String'
            return is_subclass(tpe_name, cls_name)
        else:
            return type(arg) is type_mapping.get(tpe_name)


def construct(class_name, args):
    """
    Call the class constructor with the given args. This is called from
    __init__ in the generated "JVM classes".
    """
    signatures = jvm.get_constructors(class_name)
    overloads = [(class_name, sig) for sig in signatures]
    args_with_types = find_overload(overloads, args)
    return jvm.new(class_name, *args_with_types)
