
#class _JavaObject(object):
#    def __init__(self, class_name, full_name):
#        self._class_name = class_name
#        self._full_name = full_name

def make_java_class(full_name, inst_methods, inst_fields, static_methods, static_fields):
    class_name = full_name.split('.')[-1]

    members = {}

    def make_method(name):
        def method(self):
            return 'This was method %s' % name
        return method

    for method_name in inst_methods:
        members[method_name] = make_method(method_name)

    cls = type('Java' + class_name, (object,), members)

    def __init__(self, obj):
        self._wrapped = obj


    cls.__init__ = __init__

    return cls
