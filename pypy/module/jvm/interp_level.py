import os
from pypy.interpreter.gateway import ApplevelClass, unwrap_spec
from pypy.rlib.rjvm import java

path, _ = os.path.split(__file__)
app_level_file = os.path.join(path, 'app_level_private.py')
app_level = ApplevelClass(file(app_level_file).read())
del path, app_level_file

w_make_java_class = app_level.interphook('make_java_class')

def wrap_list_of_strings(space, lst):
    list_w = [space.wrap(s) for s in lst]
    return space.newlist(list_w)

@unwrap_spec(class_name=str)
def make_instance(space, class_name):
    java_cls = java.lang.Class.forName(class_name)
    method_names = {m.getName() for m in java_cls.getMethods()}
    empty = space.newlist([])
    w_cls = w_make_java_class(space, space.wrap(class_name),
        wrap_list_of_strings(space, method_names), empty, empty, empty)

    new_name = 'Java' + class_name.split('.')[-1]

    space.setattr(space.builtin, space.wrap(new_name), w_cls)

    w_obj = space.call(w_cls, empty)
    return w_obj
