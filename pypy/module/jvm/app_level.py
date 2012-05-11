import jvm

def object_methods():
    return jvm.get_methods('java.lang.Object')

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


class JvmBoundMethod(object):
    __slots__ = ('im_name', 'im_self', 'overloads')

    def __init__(self, im_name, overloads, im_self):
        self.im_name = im_name
        self.im_self = im_self
        self.overloads = overloads

    def __call__(self, *args):
        assert len(self.overloads) == 1, "No overloaded methods for now..."

        args_with_types = [make_pair(arg) for arg in args]

        (res, tpe) = jvm.call_method(self.im_self._inst, self.im_name, *args_with_types)

        if tpe in {'java.lang.String', 'java.lang.Integer', 'java.lang.Boolean'}:
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

def make_pair(arg):
    if isinstance(arg, (str, int, bool)):
        return arg, type(arg)
    elif isinstance(arg, _JavaObjectWrapper):
        return arg._inst, arg._class_name
    else:
        raise TypeError("Don't know what type %r is." % arg)

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
