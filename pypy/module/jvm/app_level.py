import jvm

unboxable_types = {'java.lang.String', 'java.lang.Integer', 'java.lang.Boolean'}
type_mapping = {'int': int, 'boolean': bool, 'java.lang.String': str}


class JvmMethodWrapper(object):
    __slots__ = ('meth_name', 'overloads')

    def __init__(self, meth_name, overloads):
        self.meth_name = meth_name
        self.overloads = overloads

    def __get__(self, obj, _):
        if obj is None:
            raise TypeError("No unbound methods for now...")
        else:
            return JvmBoundMethod(self.meth_name, self.overloads, obj)

class JvmFieldWrapper(object):
    __slots__ = ('field_name', 'is_static')

    def __init__(self, field_name, is_static):
        self.field_name = field_name
        self.is_static = is_static

    def __get__(self, obj, _):
        if obj is None and not self.is_static:
            raise TypeError("No static fields for now...")
        else:
            res, tpe = jvm.get_field(obj._inst, self.field_name)
            return handle_result(res, tpe)

class JvmBoundMethod(object):
    __slots__ = ('im_name', 'im_self', 'overloads')

    def __init__(self, im_name, overloads, im_self):
        self.im_name = im_name
        self.im_self = im_self
        self.overloads = overloads

    def __call__(self, *args):
        args_with_types = self.__find_overload(args)
        (res, tpe) = jvm.call_method(self.im_self._inst, self.im_name, *args_with_types)
        return handle_result(res, tpe)

    def __repr__(self):
        return '<bound JVM method %s.%s of %s>' % (self.im_self._class_name,
                                                   self.im_name,
                                                   self.im_self)

    def __find_overload(self, args):
        matches = set()

        for ret_tpe, version in self.overloads:
            if self.__exact_match(version, args):
                return self.__add_types(version, args)
            elif self.__matches(version, args):
                matches.add(version)

        assert len(matches) > 0, "No overloads found!"
        assert len(matches) == 1, "Bad overloading, please use explicit casts."
        match, = matches
        return self.__add_types(match, args)

    def __exact_match(self, types, args):
        if len(types) != len(args):
            return False

        if not types:
            return True

        for tpe_name, arg in zip(types, args):
            if isinstance(arg, _JavaObjectWrapper) and arg._class_name != tpe_name:
                return False
            else:
                return type(arg) is type_mapping.get(tpe_name)

    def __matches(self, types, args):
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

    def __add_types(self, version, args):
        res = []
        for arg, name in zip(args, version):
            tpe = type_mapping.get(name, name)

            if isinstance(arg, _JavaObjectWrapper):
                arg = arg._inst
            elif isinstance(arg, str) and name != 'java.lang.String':
                arg = jvm.box(arg)

            res.append((arg, tpe))

        return res


def is_subclass(c1, c2):
    """
    Returns True iff c1 is a subclass of c2. c1 and c2 are represented as strings
    containing names of the classes.
    """
    while c2 is not None and c1 != c2:
        c2 = jvm.superclass(c2)

    return c1 == c2

class _JavaObjectWrapper(object):
    pass

def make_app_class(class_name):
    methods = jvm.get_methods(class_name)
    fields = jvm.get_fields(class_name)

    dct = {}
    for method_name, versions in methods.iteritems():
        dct[method_name] = JvmMethodWrapper(method_name, versions)

    for field_name in fields:
        dct[field_name] = JvmFieldWrapper(field_name, is_static=False)

    def make_init(class_name):
        def init(self, inst=None):
            if inst is None:
                inst = jvm.new(class_name)
            self._inst = inst
            self._class_name = class_name

        return init

    dct['__init__'] = make_init(class_name)

    cls = type('Java' + class_name.split('.')[-1], (_JavaObjectWrapper,), dct)

    return cls

classes = {}
packages = {}

def get_class(class_name):
    if class_name not in classes:
        classes[class_name] = make_app_class(class_name)
    return classes[class_name]

def handle_result(res, tpe):
    if tpe in unboxable_types:
        return jvm.unbox(res)
    elif tpe == 'void':
        assert res is None
        return None
    else:
        cls = get_class(tpe)
        return cls(res)

class JvmPackageWrapper(object):
    def __init__(self, name):
        self.__name = name

    def __getattr__(self, attr):
        new_name = '{0}.{1}'.format(self.__name, attr)
        if attr[0].isupper():
            return get_class(new_name)
        else:
            if new_name not in packages:
                packages[new_name] = JvmPackageWrapper(new_name)
            return packages[new_name]


java = JvmPackageWrapper('java')
