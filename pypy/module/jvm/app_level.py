import jvm

class JvmMethodWrapper(object):
    __slots__ = ('meth_name', 'overloads')

    def __init__(self, meth_name, overloads):
        self.meth_name = meth_name
        self.overloads = overloads

    def __get__(self, obj, type_):
        if obj is None:
            raise TypeError('No unbound methods for now...')
        else:
            return JvmBoundMethod(self.meth_name, self.overloads, obj)

    def __repr__(self):
        return '%s(%s)' % (self.__class__.__name__, repr(self.meth_name))

unboxable_types = {'java.lang.String', 'java.lang.Integer', 'java.lang.Boolean'}
type_mapping = {'int': int, 'boolean': bool, 'java.lang.String': str}

class JvmBoundMethod(object):
    __slots__ = ('im_name', 'im_self', 'overloads')

    def __init__(self, im_name, overloads, im_self):
        self.im_name = im_name
        self.im_self = im_self
        self.overloads = overloads

    def __call__(self, *args):
        args_with_types = self.__find_overload(args)
        (res, tpe) = jvm.call_method(self.im_self._inst, self.im_name, *args_with_types)

        if tpe in unboxable_types:
            return jvm.unbox(res)
        elif tpe == 'void':
            assert res is None
            return None
        else:
            cls = get_class(tpe)
            return cls(res)

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
                return type(arg) == type_mapping.get(tpe_name)

    def __matches(self, version, args):
        return False

    def __add_types(self, version, args):
        return [(arg, type_mapping.get(name, name)) for arg, name in zip(args, version)]


class _JavaObjectWrapper(object):
    pass

def make_app_class(class_name):
    methods = jvm.get_methods(class_name)

    dct = {}
    for method_name, versions in methods.iteritems():
        dct[method_name] = JvmMethodWrapper(method_name, versions)

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
