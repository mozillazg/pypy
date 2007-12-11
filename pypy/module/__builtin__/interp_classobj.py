from pypy.interpreter.error import OperationError
from pypy.interpreter.gateway import ObjSpace, W_Root, NoneNotWrapped, applevel
from pypy.interpreter.gateway import interp2app, ObjSpace
from pypy.interpreter.typedef import TypeDef, GetSetProperty
from pypy.interpreter.argument import Arguments
from pypy.interpreter.baseobjspace import Wrappable
from pypy.rlib.rarithmetic import r_uint, intmask


def descr_classobj_new(space, w_subtype, w_name, w_bases, w_dict):
    if not space.is_true(space.isinstance(w_bases, space.w_tuple)):
        raise_type_err(space, 'bases', 'tuple', w_bases)
    
    if not space.is_true(space.isinstance(w_dict, space.w_dict)):
        raise_type_err(space, 'bases', 'tuple', w_bases)

    if not space.is_true(space.contains(w_dict, space.wrap("__doc__"))):
        space.setitem(w_dict, space.wrap("__doc__"), space.w_None)

    # XXX missing: lengthy and obscure logic about "__module__"
        
    for w_base in space.unpackiterable(w_bases):
        if not isinstance(w_base, W_ClassObject):
            w_metaclass = space.type(w_base)
            if space.is_true(space.callable(w_metaclass)):
                return space.call_function(w_metaclass, w_name,
                                           w_bases, w_dic)
            raise OperationError(space.w_TypeError,
                                 space.wrap("base must be class"))

    return W_ClassObject(space, w_name, w_bases, w_dict)

class W_ClassObject(Wrappable):
    def __init__(self, space, w_name, w_bases, w_dict):
        self.name = space.str_w(w_name)
        self.bases_w = space.unpackiterable(w_bases)
        self.w_dict = w_dict

    def getdict(self):
        return self.w_dict

    def setdict(self, space, w_dict):
        if not space.is_true(space.isinstance(w_dict, space.w_dict)):
            raise OperationError(
                space.w_TypeError,
                space.wrap("__dict__ must be a dictionary object"))
        self.w_dict = w_dict

    def fget_dict(space, self):
        return self.w_dict

    def fset_dict(space, self, w_dict):
        self.setdict(space, w_dict)

    def fdel_dict(space, self):
        raise OperationError(
            space.w_TypeError,
            space.wrap("__dict__ must be a dictionary object"))

    def fget_name(space, self):
        return space.wrap(self.name)

    def fset_name(space, self, w_newname):
        if not space.is_true(space.isinstance(w_newname, space.w_str)):
            raise OperationError(
                    space.w_TypeError,
                    space.wrap("__name__ must be a string object"))
        self.name = space.str_w(w_newname)

    def fdel_name(space, self):
        raise OperationError(
                space.w_TypeError,
                space.wrap("__name__ must be a string object"))


    def fget_bases(space, self):
        return space.wrap(self.bases_w)

    def fset_bases(space, self, w_bases):
        # XXX in theory, this misses a check against inheritance cycles
        # although on pypy we don't get a segfault for infinite
        # recursion anyway 
        if not space.is_true(space.isinstance(w_bases, space.w_tuple)):
            raise OperationError(
                    space.w_TypeError,
                    space.wrap("__bases__ must be a tuple object"))
        bases_w = space.unpackiterable(w_bases)
        for w_base in bases_w:
            if not isinstance(w_base, W_ClassObject):
                raise OperationError(space.w_TypeError,
                                     space.wrap("__bases__ items must be classes"))
        self.bases_w = bases_w

    def fdel_bases(space, self):
        raise OperationError(
                space.w_TypeError,
                space.wrap("__bases__ must be a tuple object"))

    def lookup(self, space, w_attr):
        # returns w_value or interplevel None
        w_result = space.finditem(self.w_dict, w_attr)
        if w_result is not None:
            return w_result
        for base in self.bases_w:
            w_result = base.lookup(space, w_attr)
            if w_result is not None:
                return w_result
        return None

    def descr_getattribute(self, space, w_attr):
        try:
            name = space.str_w(w_attr)
        except OperationError, e:
            if not e.match(space, space.w_TypeError):
                raise
        else:
            if name == "__dict__":
                return self.w_dict
            elif name == "__name__":
                return space.wrap(self.name)
            elif name == "__bases__":
                return space.newtuple(self.bases_w)
        w_value = self.lookup(space, w_attr)
        if w_value is None:
            raise OperationError(
                space.w_AttributeError,
                space.wrap("class %s has no attribute %s" % (
                    self.name, space.str_w(space.str(w_attr)))))

        w_descr_get = space.lookup(w_value, '__get__')
        if w_descr_get is None:
            return w_value
        return space.call_function(w_descr_get, w_value, space.w_None, self)
        
    # XXX missing: str, repr

    def descr_call(self, space, __args__):
        w_inst = W_InstanceObject(space, self)
        w_init = w_inst.getattr(space, space.wrap('__init__'), False)
        if w_init is not None:
            w_result = space.call_args(w_init, __args__)
            if not space.is_w(w_result, space.w_None):
                raise OperationError(
                    space.w_TypeError,
                    space.wrap("__init__() should return None"))
        elif __args__.num_args() or __args__.num_kwds():
            raise OperationError(
                    space.w_TypeError,
                    space.wrap("this constructor takes no arguments"))
        return w_inst

W_ClassObject.typedef = TypeDef("classobj",
    __new__ = interp2app(descr_classobj_new),
    __dict__ = GetSetProperty(W_ClassObject.fget_dict, W_ClassObject.fset_dict,
                              W_ClassObject.fdel_dict),
    __name__ = GetSetProperty(W_ClassObject.fget_name, W_ClassObject.fset_name,
                              W_ClassObject.fdel_name),
    __bases__ = GetSetProperty(W_ClassObject.fget_bases,
                               W_ClassObject.fset_bases,
                               W_ClassObject.fdel_bases),
    __call__ = interp2app(W_ClassObject.descr_call,
                          unwrap_spec=['self', ObjSpace, Arguments]),
    __getattribute__ = interp2app(W_ClassObject.descr_getattribute,
                             unwrap_spec=['self', ObjSpace, W_Root]),
)
W_ClassObject.typedef.acceptable_as_base_class = False

class W_InstanceObject(Wrappable):
    def __init__(self, space, w_class, w_dict=None):
        if w_dict is None:
            w_dict = space.newdict()
        self.w_class = w_class
        self.w_dict = w_dict

    def getdict(self):
        return self.w_dict

    def setdict(self, space, w_dict):
        if not space.is_true(space.isinstance(w_dict, space.w_dict)):
            raise OperationError(
                space.w_TypeError,
                space.wrap("__dict__ must be a dictionary object"))
        self.w_dict = w_dict

    def fget_dict(space, self):
        return self.w_dict

    def fset_dict(space, self, w_dict):
        self.setdict(space, w_dict)

    def fget_class(space, self):
        return self.w_class

    def fset_class(space, self, w_class):
        if not isinstance(w_class, W_ClassObject):
            raise OperationError(
                space.w_TypeError,
                space.wrap("instance() first arg must be class"))
        self.w_class = w_class

    def descr_new(space, w_type, w_class, w_dict=None):
        # typ is not used at all
        if not isinstance(w_class, W_ClassObject):
            raise OperationError(
                space.w_TypeError,
                space.wrap("instance() first arg must be class"))
        if w_dict is None:
            w_dict = space.newdict()
        elif not space.is_true(space.isinstance(w_dict, space.w_dict)):
            raise TypeError("instance() second arg must be dictionary or None")
        return W_InstanceObject(space, w_class, w_dict)

    def retrieve(self, space, w_attr, exc=True):
        w_result = space.finditem(self.w_dict, w_attr)
        if w_result is not None:
            return w_result
        if exc:
            raise OperationError(
                space.w_AttributeError, w_attr)
        return None

    def getattr(self, space, w_name, exc=True):
        name = space.str_w(w_name)
        if name == "__dict__":
            return self.w_dict
        elif name == "__class__":
            return self.w_class
        w_result = self.retrieve(space, w_name, False)
        if w_result is not None:
            return w_result
        w_value = self.w_class.lookup(space, w_name)
        if w_value is None:
            if exc:
                raise OperationError(
                    space.w_AttributeError,
                    space.wrap("%s instance has no attribute %s" % (
                        self.w_class.name, name)))
            else:
                return None
        w_descr_get = space.lookup(w_value, '__get__')
        if w_descr_get is None:
            return w_value
        return space.call_function(w_descr_get, w_value, self, self.w_class)

    def descr_getattribute(self, space, w_attr):
        #import pdb; pdb.set_trace()
        return self.getattr(space, w_attr)

    def descr_len(self, space):
        w_meth = self.getattr(space, space.wrap('__len__'))
        w_result = space.call_function(w_meth)
        if space.is_true(space.isinstance(w_result, space.w_int)):
            if space.is_true(space.lt(w_result, space.wrap(0))):
                raise OperationError(
                    space.w_ValueError,
                    space.wrap("__len__() should return >= 0"))
            return w_result
        raise OperationError(
            space.w_TypeError,
            space.wrap("__len__() should return an int"))

    def descr_getitem(self, space, w_key):
        w_meth = self.getattr(space, space.wrap('__getitem__'))
        return space.call_function(w_meth, w_key)

    def descr_setitem(self, space, w_key, w_value):
        w_meth = self.getattr(space, space.wrap('__setitem__'))
        space.call_function(w_meth, w_key, w_value)

    def descr_delitem(self, space, w_key):
        w_meth = self.getattr(space, space.wrap('__delitem__'))
        space.call_function(w_meth, w_key)

    def descr_call(self, space, __args__):
        w_meth = self.getattr(space, space.wrap('__call__'))
        return space.call_args(w_meth, __args__)

    def descr_nonzero(self, space):
        w_func = self.getattr(space, space.wrap('__nonzero__'), False)
        if w_func is None:
            w_func = self.getattr(space, space.wrap('__len__'), False)
            if w_func is None:
                return space.w_True
        w_result = space.call_function(w_func)
        if space.is_true(space.isinstance(w_result, space.w_int)):
            if space.is_true(space.lt(w_result, space.wrap(0))):
                raise OperationError(
                    space.w_ValueError,
                    space.wrap("__nonzero__() should return >= 0"))
            return w_result
        raise OperationError(
            space.w_TypeError,
            space.wrap("__nonzero__() should return an int"))

W_InstanceObject.typedef = TypeDef("instance",
    __new__ = interp2app(W_InstanceObject.descr_new),
    __dict__ = GetSetProperty(W_InstanceObject.fget_dict,
                              W_InstanceObject.fset_dict),
    __class__ = GetSetProperty(W_InstanceObject.fget_class,
                               W_InstanceObject.fset_class),
    __getattribute__ = interp2app(W_InstanceObject.descr_getattribute,
                                  unwrap_spec=['self', ObjSpace, W_Root]),
    __len__ = interp2app(W_InstanceObject.descr_len,
                         unwrap_spec=['self', ObjSpace]),
    __getitem__ = interp2app(W_InstanceObject.descr_getitem,
                             unwrap_spec=['self', ObjSpace, W_Root]),
    __setitem__ = interp2app(W_InstanceObject.descr_setitem,
                             unwrap_spec=['self', ObjSpace, W_Root, W_Root]),
    __delitem__ = interp2app(W_InstanceObject.descr_delitem,
                             unwrap_spec=['self', ObjSpace, W_Root]),
    __call__ = interp2app(W_InstanceObject.descr_call,
                          unwrap_spec=['self', ObjSpace, Arguments]),
    __nonzero__ = interp2app(W_InstanceObject.descr_nonzero,
                             unwrap_spec=['self', ObjSpace]),
)

