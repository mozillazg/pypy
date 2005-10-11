import weakref, operator
import py
from pypy.rpython.rarithmetic import r_uint
from pypy.tool.uid import Hashable
from pypy.tool.tls import tlsobject
from types import NoneType
from pypy.rpython.lltype import LowLevelType, Signed, Unsigned, Float, Char
from pypy.rpython.lltype import Bool, Void, UniChar, typeOf

class OOType(LowLevelType):
    pass

class Class(OOType):

    def __init__(self, name, superclass, fields, methods={}):
        self._superclass = superclass

	self._methods = {}
        self._fields = {}

	self._add_fields(fields)
	self._add_methods(methods)

    	self._null = _null_instance(self)

    def _defl(self):
        return self._null

    def _add_fields(self, fields):
        for name, defn in fields.iteritems():
            if self._lookup(name) is not None:
                raise TypeError("Cannot add field %r: method already exists" % name)
	
            if self._superclass is not None:
                if self._superclass._has_field(name):
                    raise TypeError("Field %r exists in superclass" % name)

            if type(defn) is not tuple:
                if isinstance(defn, Meth):
                    raise TypeError("Attempting to store method in field")
                
                fields[name] = (defn, defn._defl())
            else:
                ootype, default = defn

                if isinstance(ootype, Meth):
                    raise TypeError("Attempting to store method in field")

                if ootype != typeOf(default):
                    raise TypeError("Expected type %r for default" % ootype)

	self._fields.update(fields)

    def _add_methods(self, methods):
        for name in methods:
	    if self._has_field(name):
	        raise TypeError("Can't add method %r: field already exists" % name)
        self._methods.update(methods)

    def _init_instance(self, instance):
        if self._superclass is not None:
            self._superclass._init_instance(instance)
        
        for name, (ootype, default) in self._fields.iteritems():
            instance.__dict__[name] = default

    def _has_field(self, name):
        try:
            self._fields[name]
            return True
        except KeyError:
	    if self._superclass is None:
                return False

            return self._superclass._has_field(name)

    def _check_field(self, name):
        if not self._has_field(name):
	    raise TypeError("No field named %r" % name)

    def _lookup(self, meth_name):
        meth = self._methods.get(meth_name)

        if meth is None and self._superclass is not None:
            meth = self._superclass._lookup(meth_name)

        return meth

class StaticMethod(OOType):

    def __init__(self, args, result):
    	self.ARGS = tuple(args)
	self.RESULT = result

class Meth(StaticMethod):

    def __init__(self, args, result):
        StaticMethod.__init__(self, args, result)
# ____________________________________________________________

class _instance(object):
    
    def __init__(self, CLASS):
        self.__dict__["_TYPE"] = CLASS

        CLASS._init_instance(self)

    def __getattr__(self, name):
        meth = self._TYPE._lookup(name)
        if meth is not None:
            return meth._bound(self)
        
        self._TYPE._check_field(name)

        return self.__dict__[name]

    def __setattr__(self, name, value):
        self.__getattr__(name)
            
        if self._TYPE._fields[name][0] != typeOf(value):
            raise TypeError("Expected type %r" % self._TYPE._fields[name][0])

        self.__dict__[name] = value

class _null_instance(_instance):

    def __init__(self, CLASS):
        self.__dict__["_TYPE"] = CLASS

    def __getattribute__(self, name):
        if name.startswith("_"):
            return object.__getattribute__(self, name)
    
        self._TYPE._check_field(name)
        
        raise RuntimeError("Access to field in null object")

    def __setattr__(self, name, value):
        _instance.__setattr__(self, name, value)

        raise RuntimeError("Assignment to field in null object")

class _callable(object):

   def __init__(self, TYPE, **attrs):
       self._TYPE = TYPE
       self._name = "?"
       self._callable = None
       self.__dict__.update(attrs)

   def _checkargs(self, args):
       if len(args) != len(self._TYPE.ARGS):
	   raise TypeError,"calling %r with wrong argument number: %r" % (self._TYPE, args)

       for a, ARG in zip(args, self._TYPE.ARGS):
           if typeOf(a) != ARG:
               if isinstance(ARG, Class) and isinstance(a, _instance):
                    if instanceof(a, ARG):
                        continue
               raise TypeError,"calling %r with wrong argument types: %r" % (self._TYPE, args)
       callb = self._callable
       if callb is None:
           raise RuntimeError,"calling undefined function"
       return callb

class _static_meth(_callable):

   def __init__(self, STATICMETHOD, **attrs):
       assert isinstance(STATICMETHOD, StaticMethod)
       _callable.__init__(self, STATICMETHOD, **attrs)

   def __call__(self, *args):
       return self._checkargs(args)(*args)

class _meth(_callable):
   
    def __init__(self, METHOD, **attrs):
        assert isinstance(METHOD, Meth)
        _callable.__init__(self, METHOD, **attrs)

    def _bound(self, inst):
        return _bound_meth(inst, self)

class _bound_meth(object):

    def __init__(self, inst, meth):
        self.inst = inst
        self.meth = meth

    def __call__(self, *args):
        return self.meth._checkargs(args)(self.inst, *args)

def new(CLASS):
    return _instance(CLASS)

def static_meth(FUNCTION, **attrs):
    return _static_meth(FUNCTION, **attrs)

def meth(METHOD, **attrs):
    return _meth(METHOD, **attrs)

def null(CLASS):
    return CLASS._null

def addFields(CLASS, fields):
    CLASS._add_fields(fields)

def addMethods(CLASS, methods):
    CLASS._add_methods(methods)

def instanceof(inst, CLASS):
    c = inst._TYPE
    while c is not None:
        if c is CLASS:
            return True
        c = c._superclass

    return False

