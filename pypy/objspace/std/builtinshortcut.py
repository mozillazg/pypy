from pypy.interpreter.baseobjspace import ObjSpace
from pypy.objspace.descroperation import DescrOperation
from pypy.objspace.std.multimethod import FailedToImplement
from pypy.tool.sourcetools import func_with_new_name


METHODS_WITH_SHORTCUT = dict.fromkeys(
    ['add', 'sub', 'mul', 'truediv', 'floordiv', 'div',
     'mod', 'lshift', 'rshift', 'and_', 'or_', 'xor',
     'lt', 'le', 'eq', 'ne', 'gt', 'ge',
     ])
# XXX inplace_
# XXX unary ops


def install(space, mm):
    name = mm.name
    if name not in METHODS_WITH_SHORTCUT:
        return
    print 'shortcut for:', name
    assert hasattr(DescrOperation, name)

    base_method = getattr(space.__class__, name)
    assert name not in space.__dict__

    # Basic idea: we first try to dispatch the operation using purely
    # the multimethod.  If this is done naively, subclassing a built-in
    # type like 'int' and overriding a special method like '__add__'
    # doesn't work any more, because the multimethod will accept the int
    # subclass and compute the result in the built-in way.  To avoid
    # this issue, we tweak the shortcut multimethods so that these ones
    # (and only these ones) never match the interp-level subclasses
    # built in pypy.interpreter.typedef.get_unique_interplevel_subclass.
    expanded_order = space.model.get_typeorder_with_empty_usersubcls()
    shortcut_method = mm.install_not_sliced(expanded_order)

    def operate(*args_w):
        try:
            w_result = shortcut_method(space, *args_w)
            #print 'shortcut:', name, args_w
            return w_result
        except FailedToImplement:
            pass
        return base_method(space, *args_w)

    setattr(space, name, func_with_new_name(operate, name))
