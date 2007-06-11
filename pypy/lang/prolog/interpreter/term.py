import math
from pypy.rlib.objectmodel import we_are_translated, UnboxedValue
from pypy.rlib.rarithmetic import intmask
from pypy.lang.prolog.interpreter.error import UnificationFailed, UncatchableError
from pypy.lang.prolog.interpreter import error
from pypy.rlib.jit import hint
from pypy.rlib.objectmodel import specialize
from pypy.rlib.jit import we_are_jitted, hint, purefunction, _is_early_constant

DEBUG = False


def debug_print(*args):
    if DEBUG and not we_are_translated():
        print " ".join([str(a) for a in args])


class PrologObject(object):
    __slots__ = ()
    _immutable_ = True

    def __init__(self):
        raise NotImplementedError("abstract base class")
        return self

    def getvalue(self, trail):
        return self

    def dereference(self, trail):
        raise NotImplementedError("abstract base class")

    def copy(self, trail, memo):
        raise NotImplementedError("abstract base class")

    @specialize.arg(3)
    def unify(self, other, trail, occurs_check=False):
        raise NotImplementedError("abstract base class")

    @specialize.arg(3)
    def _unify(self, other, trail, occurs_check=False):
        raise NotImplementedError("abstract base class")

    def contains_var(self, var, trail):
        return False

    def __eq__(self, other):
        # for testing
        return (self.__class__ == other.__class__ and
                self.__dict__ == other.__dict__)

    def __ne__(self, other):
        # for testing
        return not (self == other)

    def eval_arithmetic(self, engine):
        error.throw_type_error("evaluable", self)

class Var(PrologObject):
    STANDARD_ORDER = 0

    __slots__ = ('binding', )
    cache = {}

    def __init__(self):
        self.binding = None

    @specialize.arg(3)
    def unify(self, other, trail, occurs_check=False):
        return self.dereference(trail)._unify(other, trail, occurs_check)

    @specialize.arg(3)
    def _unify(self, other, trail, occurs_check=False):
        other = other.dereference(trail)
        if isinstance(other, Var) and other is self:
            pass
        elif occurs_check and other.contains_var(self, trail):
            raise UnificationFailed()
        else:
            self.setvalue(other, trail)

    def dereference(self, trail):
        next = self.binding
        if next is None:
            return self
        if isinstance(next, Var):
            if _is_early_constant(next):
                result = next.dereference(trail)
            else:
                result = next.opaque_dereference(trail)
            self.setvalue(result, trail)
            return result
        return next

    def opaque_dereference(self, trail):
        return self.dereference(trail)

    def getvalue(self, trail):
        res = self.dereference(trail)
        if not isinstance(res, Var):
            return res.getvalue(trail)
        return res

    def setvalue(self, value, trail):
        if value is not self.binding:
            trail.add_trail(self)
            self.binding = value

    def copy(self, trail, memo):
        try:
            return memo[self]
        except KeyError:
            newvar = memo[self] = trail.newvar()
            return newvar

    def contains_var(self, var, trail):
        self = self.dereference(trail)
        if self is var:
            return True
        if not isinstance(self, Var):
            return self.contains_var(var, trail)
        return False

    def __repr__(self):
        return "Var(%s)" % (self.binding, )


    def __eq__(self, other):
        # for testing
        return self is other

    def eval_arithmetic(self, engine):
        self = self.dereference(engine.trail)
        if isinstance(self, Var):
            error.throw_instantiation_error()
        return self.eval_arithmetic(engine)


class LocalVar(Var):
    __slots__ = ("binding", "active")

    def __init__(self):
        self.binding = None
        self.active = False

    def setvalue(self, value, trail):
        if self.active:
            trail.add_trail(self)
        self.binding = value


class NonVar(PrologObject):
    __slots__ = ()

    def dereference(self, trail):
        return self

    @specialize.arg(3)
    def unify(self, other, trail, occurs_check=False):
        return self._unify(other, trail, occurs_check)


    @specialize.arg(3)
    def basic_unify(self, other, trail, occurs_check=False):
        raise NotImplementedError("abstract base class")

    @specialize.arg(3)
    def _unify(self, other, trail, occurs_check=False):
        other = other.dereference(trail)
        if isinstance(other, Var):
            other._unify(self, trail, occurs_check)
        else:
            self.basic_unify(other, trail, occurs_check)


class Callable(NonVar):
    __slots__ = ("name", "signature")
    name = ""
    signature = ""

    def get_prolog_signature(self):
        raise NotImplementedError("abstract base")


class Atom(Callable):
    STANDARD_ORDER = 1

    cache = {}
    _immutable_ = True

    def __init__(self, name):
        self.name = name
        self.signature = self.name + "/0"

    def __str__(self):
        return self.name

    def __repr__(self):
        return "Atom(%r)" % (self.name,)

    @specialize.arg(3)
    def basic_unify(self, other, trail, occurs_check=False):
        if isinstance(other, Atom) and (self is other or
                                        other.name == self.name):
            return
        raise UnificationFailed

    def copy(self, trail, memo):
        return self

    def get_prolog_signature(self):
        return Term("/", [self, NUMBER_0])

    @staticmethod
    @purefunction
    def newatom(name):
        result = Atom.cache.get(name, None)
        if result is not None:
            return result
        Atom.cache[name] = result = Atom(name)
        return result

    def eval_arithmetic(self, engine):
        #XXX beautify that
        if self.name == "pi":
            return Float.pi
        if self.name == "e":
            return Float.e
        error.throw_type_error("evaluable", self.get_prolog_signature())


class Number(NonVar):
    STANDARD_ORDER = 2
    _immutable_ = True
    def __init__(self, num):
        self.num = num

    @specialize.arg(3)
    def basic_unify(self, other, trail, occurs_check=False):
        if isinstance(other, Number) and other.num == self.num:
            return
        raise UnificationFailed

    def copy(self, trail, memo):
        return self

    def __str__(self):
        return repr(self.num)

    def __repr__(self):
        return "Number(%r)" % (self.num, )

    def eval_arithmetic(self, engine):
        return self

NUMBER_0 = Number(0)

class Float(NonVar):
    STANDARD_ORDER = 2
    _immutable_ = True
    def __init__(self, floatval):
        self.floatval = floatval

    @specialize.arg(3)
    def basic_unify(self, other, trail, occurs_check=False):
        if isinstance(other, Float) and other.floatval == self.floatval:
            return
        raise UnificationFailed
    basic_unify._look_inside_me_ = False

    def copy(self, trail, memo):
        return self

    def __str__(self):
        return repr(self.floatval)

    def __repr__(self):
        return "Float(%r)" % (self.floatval, )

    def eval_arithmetic(self, engine):
        from pypy.lang.prolog.interpreter.arithmetic import norm_float
        return norm_float(self)

Float.e = Float(math.e)
Float.pi = Float(math.pi)


class BlackBox(NonVar):
    # meant to be subclassed
    STANDARD_ORDER = 4
    def __init__(self):
        pass

    @specialize.arg(3)
    def basic_unify(self, other, trail, occurs_check=False):
        if self is other:
            return
        raise UnificationFailed

    def copy(self, trail, memo):
        return self


# helper functions for various Term methods

def _getvalue(obj, trail):
    return obj.getvalue(trail)

class Term(Callable):
    STANDARD_ORDER = 3
    _immutable_ = True
    def __init__(self, name, args, signature=None):
        self.name = name
        self.args = args
        if signature is None:
            self.signature = name + "/" + str(len(args))
        else:
            self.signature = signature

    def __repr__(self):
        return "Term(%r, %r)" % (self.name, self.args)

    def __str__(self):
        return "%s(%s)" % (self.name, ", ".join([str(a) for a in self.args]))

    @specialize.arg(3)
    def basic_unify(self, other, trail, occurs_check=False):
        if (isinstance(other, Term) and
            self.name == other.name and
            len(self.args) == len(other.args)):
            i = 0
            while i < len(self.args):
                self.args[i].unify(other.args[i], trail, occurs_check)
                i += 1
        else:
            raise UnificationFailed

    def copy(self, trail, memo):
        newargs = []
        i = 0
        while i < len(self.args):
            arg = self.args[i].copy(trail, memo)
            newargs.append(arg)
            i += 1
        return Term(self.name, newargs, self.signature)

    def getvalue(self, trail):
        return self._copy_term(_getvalue, trail)

    def _copy_term(self, copy_individual, *extraargs):
        args = [None] * len(self.args)
        newinstance = False
        for i in range(len(self.args)):
            arg = self.args[i]
            cloned = copy_individual(arg, *extraargs)
            if cloned is not arg:
                newinstance = True
            args[i] = cloned
        if newinstance:
            return Term(self.name, args, self.signature)
        else:
            return self

    def get_prolog_signature(self):
        return Term("/", [Atom.newatom(self.name), Number(len(self.args))])
    
    def contains_var(self, var, trail):
        for arg in self.args:
            if arg.contains_var(var, trail):
                return True
        return False
        
    def eval_arithmetic(self, engine):
        from pypy.lang.prolog.interpreter.arithmetic import arithmetic_functions
        from pypy.lang.prolog.interpreter.arithmetic import arithmetic_functions_list
        if we_are_jitted():
            signature = hint(self.signature, promote=True)
            func = None
            for sig, func in arithmetic_functions_list:
                if sig == signature:
                    break
        else:
            func = arithmetic_functions.get(self.signature, None)
        if func is None:
            error.throw_type_error("evaluable", self.get_prolog_signature())
        return func(engine, self)


@specialize.argtype(0)
def rcmp(a, b): # RPython does not support cmp...
    if a == b:
        return 0
    if a < b:
        return -1
    return 1

def cmp_standard_order(obj1, obj2, trail):
    c = rcmp(obj1.STANDARD_ORDER, obj2.STANDARD_ORDER)
    if c != 0:
        return c
    if isinstance(obj1, Var):
        assert isinstance(obj2, Var)
        return rcmp(id(obj1), id(obj2))
    if isinstance(obj1, Atom):
        assert isinstance(obj2, Atom)
        return rcmp(obj1.name, obj2.name)
    if isinstance(obj1, Term):
        assert isinstance(obj2, Term)
        c = rcmp(len(obj1.args), len(obj2.args))
        if c != 0:
            return c
        c = rcmp(obj1.name, obj2.name)
        if c != 0:
            return c
        for i in range(len(obj1.args)):
            a1 = obj1.args[i].dereference(trail)
            a2 = obj2.args[i].dereference(trail)
            c = cmp_standard_order(a1, a2, trail)
            if c != 0:
                return c
        return 0
    # XXX hum
    if isinstance(obj1, Number):
        if isinstance(obj2, Number):
            return rcmp(obj1.num, obj2.num)
        elif isinstance(obj2, Float):
            return rcmp(obj1.num, obj2.floatval)
    if isinstance(obj1, Float):
        if isinstance(obj2, Number):
            return rcmp(obj1.floatval, obj2.num)
        elif isinstance(obj2, Float):
            return rcmp(obj1.floatval, obj2.floatval)
    assert 0
