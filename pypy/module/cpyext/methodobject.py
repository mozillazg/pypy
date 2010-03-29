from pypy.interpreter.baseobjspace import Wrappable, W_Root
from pypy.interpreter.typedef import TypeDef
from pypy.interpreter.gateway import ObjSpace, W_Root
from pypy.interpreter.argument import Arguments
from pypy.interpreter.typedef import interp_attrproperty, interp_attrproperty_w
from pypy.interpreter.gateway import interp2app, unwrap_spec
from pypy.interpreter.error import OperationError, operationerrfmt
from pypy.interpreter.function import BuiltinFunction, Method
from pypy.rpython.lltypesystem import rffi, lltype
from pypy.module.cpyext.api import PyObject, from_ref, \
        make_ref, generic_cpy_call
from pypy.module.cpyext.state import State
from pypy.module.cpyext.pyerrors import PyErr_Occurred
from pypy.rlib.objectmodel import we_are_translated


class W_PyCFunctionObject(Wrappable):
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
        pyo = rffi.cast(PyObject, pto)
        self.w_objclass = from_ref(space, pyo)

    def __repr__(self):
        return "<method %r of %r objects>" % (self.name, self.w_objclass.getname(self.space, '?'))

    def descr_method_repr(self):
        return self.space.wrap(self.__repr__())


class W_PyCWrapperObject(Wrappable):
    def __init__(self, space, pto, method_name, wrapper_func, wrapper_func_kwds,
            doc, func):
        self.space = space
        self.method_name = method_name
        self.wrapper_func = wrapper_func
        self.wrapper_func_kwds = wrapper_func_kwds
        self.doc = doc
        self.func = func
        pyo = rffi.cast(PyObject, pto)
        self.w_objclass = from_ref(space, pyo)

    def call(self, w_self, w_args, w_kw):
        if self.wrapper_func is None:
            assert self.wrapper_func_kwds is not None
            return self.wrapper_func_kwds(self.space, w_self, w_args, self.func, w_kw)
        if self.space.is_true(w_kw):
            raise operationerrfmt(self.space.w_TypeError,
                                 "wrapper %s doesn't take any keyword arguments",
                                 self.method_name)
        return self.wrapper_func(self.space, w_self, w_args, self.func)

    def descr_method_repr(self):
        return self.space.wrap("<slot wrapper %r of %r objects>" % (self.method_name,
            self.w_objclass.getname(self.space, '?')))

@unwrap_spec(ObjSpace, W_Root, Arguments)
def cwrapper_descr_call(space, w_self, __args__):
    self = space.interp_w(W_PyCWrapperObject, w_self)
    args_w, kw_w = __args__.unpack()
    w_args = space.newtuple(args_w[1:])
    w_self = args_w[0]
    w_kw = space.newdict()
    for key, w_obj in kw_w.items():
        space.setitem(w_kw, space.wrap(key), w_obj)
    return self.call(w_self, w_args, w_kw)


@unwrap_spec(ObjSpace, W_Root, Arguments)
def cfunction_descr_call(space, w_self, __args__):
    self = space.interp_w(W_PyCFunctionObject, w_self)
    args_w, kw_w = __args__.unpack()
    w_args = space.newtuple(args_w)
    if kw_w:
        raise OperationError(space.w_TypeError,
                             space.wrap("keywords not yet supported"))
    ret = self.call(None, w_args)
    return ret

@unwrap_spec(ObjSpace, W_Root, Arguments)
def cmethod_descr_call(space, w_self, __args__):
    self = space.interp_w(W_PyCFunctionObject, w_self)
    args_w, kw_w = __args__.unpack()
    w_instance = args_w[0]
    w_args = space.newtuple(args_w[1:])
    if kw_w:
        raise OperationError(space.w_TypeError,
                             space.wrap("keywords not yet supported"))
    ret = self.call(w_instance, w_args)
    return ret

def cmethod_descr_get(space, w_function, w_obj, w_cls=None):
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
W_PyCFunctionObject.typedef.acceptable_as_base_class = False

W_PyCMethodObject.typedef = TypeDef(
    'method',
    __get__ = interp2app(cmethod_descr_get),
    __call__ = interp2app(cmethod_descr_call),
    __name__ = interp_attrproperty('name', cls=W_PyCMethodObject),
    __objclass__ = interp_attrproperty_w('w_objclass', cls=W_PyCMethodObject),
    __repr__ = interp2app(W_PyCMethodObject.descr_method_repr),
    )
W_PyCMethodObject.typedef.acceptable_as_base_class = False


W_PyCWrapperObject.typedef = TypeDef(
    'wrapper_descriptor',
    __call__ = interp2app(cwrapper_descr_call),
    __get__ = interp2app(cmethod_descr_get),
    __name__ = interp_attrproperty('method_name', cls=W_PyCWrapperObject),
    __doc__ = interp_attrproperty('doc', cls=W_PyCWrapperObject),
    __objclass__ = interp_attrproperty_w('w_objclass', cls=W_PyCWrapperObject),
    __repr__ = interp2app(W_PyCWrapperObject.descr_method_repr),
    # XXX missing: __getattribute__, __repr__
    )
W_PyCWrapperObject.typedef.acceptable_as_base_class = False


def PyCFunction_NewEx(space, ml, w_self): # not exactly the API sig
    return space.wrap(W_PyCFunctionObject(space, ml, w_self))


def PyDescr_NewMethod(space, pto, method):
    return space.wrap(W_PyCMethodObject(space, method, pto))

def PyDescr_NewWrapper(space, pto, method_name, wrapper_func, doc, flags, func):
    # not exactly the API sig
    return space.wrap(W_PyCWrapperObject(space, pto, method_name,
        wrapper_func, doc, flags, func))
