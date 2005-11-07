import types
from pypy.interpreter.pycode import cpython_code_signature
from pypy.annotation.classdef import ClassDef
from pypy.annotation import model as annmodel


class Desc(object):
    pyobj = None   # non-None if there is an associated underlying Python obj

    def __repr__(self):
        pyobj = self.pyobj
        if pyobj is None:
            return object.__repr__(self)
        return '<%s for %r>' % (self.__class__.__name__, pyobj)


class FunctionDesc(Desc):
    knowntype = types.FunctionType
    
    def __init__(self, pyobj=None, signature=None):
        self.pyobj = pyobj
        if signature is None:
            signature = cpython_code_signature(pyfunc.func_code)
        self.signature = signature


class ClassDesc(Desc):
    knowntype = type

    def __init__(self, bookkeeper, pyobj, specialize=None):
        self.bookkeeper = bookkeeper
        self.pyobj = pyobj
        self.name = pyobj.__module__ + '.' + pyobj.__name__
        if specialize is None:
            tag = pyobj.__dict__.get('_annspecialcase_', '')
            assert not tag  # XXX later
        self.specialize = specialize
        self._classdef = None

    def getuniqueclassdef(self):
        if self.specialize:
            raise Exception("not supported on class %r because it needs "
                            "specialization" % (self.name,))
        if self._classdef is None:
            classdef = ClassDef(self.pyobj, self.bookkeeper)
            self.bookkeeper.classdefs.append(classdef)
            self._classdef = classdef
            classdef.setup()
        return self._classdef


class MethodDesc(Desc):
    knowntype = types.MethodType

    def __init__(self, funcdesc, classdef):
        self.funcdesc = funcdesc
        self.classdef = classdef

    def __repr__(self):
        return '<MethodDesc %r of %r>' % (self.funcdesc,
                                          self.classdef)


def new_or_old_class(c):
    if hasattr(c, '__class__'):
        return c.__class__
    else:
        return type(c)


class FrozenDesc(Desc):

    def __init__(self, bookkeeper, pyobj):
        self.bookkeeper = bookkeeper
        self.pyobj = pyobj
        self.attributes = self.pyobj.__dict__.copy()
        self.knowntype = new_or_old_class(pyobj)

    def s_read_attribute(self, attr):
        if attr in self.attributes:
            return self.bookkeeper.immutablevalue(self.attributes[attr])
        else:
            return annmodel.SomeImpossibleValue()


class MethodOfFrozenDesc(Desc):
    knowntype = types.MethodType

    def __init__(self, funcdesc, frozendesc):
        self.funcdesc = funcdesc
        self.frozendesc = frozendesc

    def __repr__(self):
        return '<MethodOfFrozenDesc %r of %r>' % (self.funcdesc,
                                                  self.frozendesc)
