import os
from pypy.interpreter.baseobjspace import Wrappable
from pypy.interpreter.gateway import ApplevelClass, unwrap_spec
from pypy.interpreter.typedef import TypeDef
from pypy.rlib.rjvm import java, new_array

class W_JvmObject(Wrappable):

    typedef = TypeDef('_JvmObject')

    def __init__(self, space, b_obj):
        self.space = space
        self.b_obj = b_obj


@unwrap_spec(class_name=str)
def new(space, class_name, args_w):
    b_java_cls = java.lang.Class.forName(class_name)
    args_len = len(args_w)
    types = new_array(java.lang.Class, args_len)
    args = new_array(java.lang.Object, args_len)

    for i, w_arg_type in enumerate(args_w):
        w_arg, w_type = space.unpackiterable(w_arg_type, 2)
        type_name = space.str_w(w_type)
        b_arg = space.interp_w(W_JvmObject, w_arg).b_obj
        types[i] = java.lang.Class.forName(type_name)
        args[i] = b_arg

    constructor = b_java_cls.getConstructor(types)

    b_obj = constructor.newInstance(args)
    w_obj = space.wrap(W_JvmObject(space, b_obj))

    return w_obj


def is_static(m):
    return java.lang.reflect.Modifier.isStatic(m.getModifiers())

path, _ = os.path.split(__file__)
app_level_file = os.path.join(path, 'app_level_private.py')
app_level = ApplevelClass(file(app_level_file).read())
del path, app_level_file

w_make_java_class = app_level.interphook('make_java_class')
