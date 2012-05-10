import os
from pypy.interpreter.baseobjspace import Wrappable
from pypy.interpreter.error import OperationError
from pypy.interpreter.gateway import ApplevelClass, unwrap_spec
from pypy.interpreter.typedef import TypeDef
from pypy.rlib.rjvm import java, new_array

class W_JvmObject(Wrappable):

    typedef = TypeDef('_JvmObject')

    def __init__(self, space, b_obj):
        self.space = space
        self.b_obj = b_obj


@unwrap_spec(class_name=str)
def new(space, class_name):
    b_java_cls = java.lang.Class.forName('java.awt.Point')

    types = new_array(java.lang.Class, 1)
    args = new_array(java.lang.Object, 1)

    types[0] = java.lang.Class.forName('java.awt.Point')
    args[0] = java.awt.Point()

    b_constructor = b_java_cls.getConstructor(types)
    b_point_as_object = b_constructor.newInstance(args)

    return space.wrap(str(b_point_as_object.toString()))

#    i = 0
#    for w_arg_type in args_w:
#        w_arg, w_type = space.unpacktuple(w_arg_type)
#        type_name = space.str_w(w_type)
#        arg = unwrap_arg(space, w_arg, type_name)
#        types[i] = type_for_name(type_name)
#        args[i] = arg
#        i += 1
#
#    constructor = java_cls.getConstructor(types)
#    b_obj = constructor.newInstance(args)
#
#    return space.wrap(W_JvmObject(space, b_obj))


def wrap_jvm_obj(space, b_obj, class_name, java_cls):
    #method_names = {str(m.getName()) for m in java_cls.getMethods() if not is_static(m)}

#    w_method_names = space.newset()
#    for m in java_cls.getMethods():
#        if not is_static(m):
#            w_name = space.wrap(m.getName())
#            space.call_method(w_method_names, 'add', w_name)

    method_names = {}
    for m in java_cls.getMethods():
        if not is_static(m):
            method_names[m.getName()] = True

    empty = space.newlist([])
    w_cls = w_make_java_class(space,
        space.wrap(class_name),
        wrap_list_of_strings(space, method_names.keys()),
        empty, empty, empty)

    space.setattr(space.builtin, space.wrap('JavaObject'), w_cls)

    w_obj = space.wrap(W_JvmObject(space, b_obj))
    res = space.call_function(w_cls, w_obj)

    return res




def is_static(m):
    return java.lang.reflect.Modifier.isStatic(m.getModifiers())

path, _ = os.path.split(__file__)
app_level_file = os.path.join(path, 'app_level_private.py')
app_level = ApplevelClass(file(app_level_file).read())
del path, app_level_file

w_make_java_class = app_level.interphook('make_java_class')
