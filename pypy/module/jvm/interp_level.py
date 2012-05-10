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

#    @unwrap_spec(name=str, startfrom=int)
#    def call_method(self, name, w_args, startfrom=0):
#        return call_method(self.space, self.b_obj, self.b_obj.GetType(), name, w_args, startfrom)

@unwrap_spec(class_name=str)
def new(space, class_name):
    b_java_cls = java.lang.Class.forName(class_name)

    names = {}
    for b_method in b_java_cls.getMethods():
        names[b_method.getName()] = True

    names_w = [space.wrap(str(name)) for name in names.keys()]

    return space.newlist(names_w)

#    args_len = len(args_w)
#    types = new_array(java.lang.Class, 0)
#    args = new_array(java.lang.Object, 0)

#    i = 0
#    for w_arg_type in args_w:
#        w_arg, w_type = space.unpacktuple(w_arg_type)
#        type_name = space.str_w(w_type)
#        arg = unwrap_arg(space, w_arg, type_name)
#        types[i] = type_for_name(type_name)
#        args[i] = arg
#        i += 1

#    constructor = java_cls.getConstructor(types)
#    b_obj = constructor.newInstance(args)
#
#    return wrap_jvm_obj(space, b_obj, class_name, java_cls)

@unwrap_spec(class_name=str)
def superclass(space, class_name):
    b_cls = java.lang.Class.forName(class_name)
    b_superclass = b_cls.getSuperclass()
    return space.wrap(b_superclass.getName())


def wrap_list_of_strings(space, lst):
    list_w = [space.wrap(s) for s in lst]
    return space.newlist(list_w)


def unwrap_arg(space, w_arg, type_name):
    if type_name == 'str':
        return space.str_w(w_arg)

    raise OperationError(space.w_TypeError, space.wrap("Unknown argument type %s" % type_name))

def type_for_name(type_name):
    if type_name == 'str':
        return java.lang.String.class_
    else:
        return java.lang.Class.forName(type_name)


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
