from pypy.interpreter.baseobjspace import Wrappable, W_Root
from pypy.interpreter.typedef import TypeDef
from pypy.interpreter.gateway import ObjSpace, W_Root
from pypy.interpreter.argument import Arguments
from pypy.interpreter.typedef import interp_attrproperty, interp_attrproperty_w
from pypy.interpreter.gateway import interp2app, unwrap_spec
from pypy.interpreter.function import BuiltinFunction, Method
from pypy.rpython.lltypesystem import rffi, lltype
from pypy.module.cpyext.api import PyObject, from_ref, NullPointerException, \
        InvalidPointerException, make_ref
from pypy.module.cpyext.state import State
from pypy.module.cpyext.macros import Py_DECREF
from pypy.rlib.objectmodel import we_are_translated


def from_ref_ex(space, result):
    try:
        ret = from_ref(space, result)
    except NullPointerException:
        state = space.fromcache(State)
        state.check_and_raise_exception()
        assert False, "NULL returned but no exception set"
    except InvalidPointerException:
        if not we_are_translated():
            import sys
            print >>sys.stderr, "Calling a C function return an invalid PyObject" \
                    " pointer."
        raise
    return ret

def generic_cpy_call(space, func, *args):
    boxed_args = []
    for arg in args: # XXX ur needed
        if isinstance(arg, W_Root) or arg is None:
            boxed_args.append(make_ref(space, arg))
        else:
            boxed_args.append(arg)
    result = func(*boxed_args)
    try:
        ret = from_ref_ex(space, result)
        Py_DECREF(space, ret)
        return ret
    finally:
        for arg in args: # XXX ur needed
            if arg is not None and isinstance(arg, W_Root):
                Py_DECREF(space, arg)

# XXX use Function as a parent class?
class W_PyCFunctionObject(Wrappable):
    acceptable_as_base_class = False
    def __init__(self, space, ml, w_self):
        self.space = space
        self.ml = ml
        self.w_self = w_self

    def call(self, w_self, args_tuple):
        space = self.space
        # Call the C function
        if w_self is None:
            w_self = self.w_self
        return generic_cpy_call(space, self.ml.c_ml_meth, w_self, args_tuple)


class W_PyCMethodObject(W_PyCFunctionObject):
    w_self = None
    def __init__(self, space, ml, pto):
        self.space = space
        self.ml = ml
        self.name = rffi.charp2str(ml.c_ml_name)
        self.w_objclass = from_ref(space, pto)

    def __repr__(self):
        return "method %r of %r objects" % (self.name, self.w_objclass.getname(self.space, '?'))

    def descr_method_repr(self):
        return self.space.wrap(self.__repr__())


@unwrap_spec(ObjSpace, W_Root, Arguments)
def cfunction_descr_call(space, w_self, __args__):
    self = space.interp_w(W_PyCFunctionObject, w_self)
    w_tuple = __args__.unpack_cpy()
    ret = self.call(None, w_tuple)
    return ret

@unwrap_spec(ObjSpace, W_Root, Arguments)
def cmethod_descr_call(space, w_self, __args__):
    self = space.interp_w(W_PyCFunctionObject, w_self)
    w_tuple = __args__.unpack_cpy(1)
    w_self = __args__.arguments_w[0]
    ret = self.call(w_self, w_tuple)
    return ret

def cmethod_descr_get(space, w_function, w_obj, w_cls=None):
    """functionobject.__get__(obj[, type]) -> method"""
    # this is not defined as a method on Function because it's generally
    # useful logic: w_function can be any callable.  It is used by Method too.
    asking_for_bound = (space.is_w(w_cls, space.w_None) or
                        not space.is_w(w_obj, space.w_None) or
                        space.is_w(w_cls, space.type(space.w_None)))
    if asking_for_bound:
        return space.wrap(Method(space, w_function, w_obj, w_cls))
    else:
        return w_function


W_PyCFunctionObject.typedef = TypeDef(
    'builtin_function_or_method',
    __call__ = interp2app(cfunction_descr_call),
    )

W_PyCMethodObject.typedef = TypeDef(
    'method',
    __get__ = interp2app(cmethod_descr_get),
    __call__ = interp2app(cmethod_descr_call),
    __name__ = interp_attrproperty('name', cls=W_PyCMethodObject),
    __objclass__ = interp_attrproperty_w('w_objclass', cls=W_PyCMethodObject),
    __repr__ = interp2app(W_PyCMethodObject.descr_method_repr),
    )


def PyCFunction_NewEx(space, ml, w_self): # not directly the API sig
    return space.wrap(W_PyCFunctionObject(space, ml, w_self))


def PyDescr_NewMethod(space, pto, method):
    return space.wrap(W_PyCMethodObject(space, method, pto))

