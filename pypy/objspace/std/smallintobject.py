"""
Implementation of small ints, stored as odd-valued pointers in the
translated PyPy.  To enable them, see inttype.py.
"""
from pypy.objspace.std import intobject
from pypy.objspace.std.model import registerimplementation, W_Object
from pypy.objspace.std.register_all import register_all
from pypy.objspace.std.intobject import W_IntObject
from pypy.rlib.objectmodel import UnboxedValue
from pypy.tool.sourcetools import func_with_new_name


class W_SmallIntObject(W_Object, UnboxedValue):
    __slots__ = 'intval'
    from pypy.objspace.std.inttype import int_typedef as typedef

    def unwrap(w_self, space):
        return int(w_self.intval)


registerimplementation(W_SmallIntObject)


def delegate_SmallInt2Int(space, w_small):
    return W_IntObject(w_small.intval)

def delegate_SmallInt2Long(space, w_small):
    return space.newlong(w_small.intval)

def delegate_SmallInt2Float(space, w_small):
    return space.newfloat(float(w_small.intval))

def delegate_SmallInt2Complex(space, w_small):
    return space.newcomplex(float(w_small.intval), 0.0)

def copy_multimethods(ns):
    """Copy integer multimethods for small int."""
    for name, func in intobject.__dict__.iteritems():
        if "__Int" in name:
            new_name = name.replace("Int", "SmallInt")
            # Copy the function, so the annotator specializes it for
            # W_SmallIntObject.  Also replaces the func_globals with ns.
            # The effect we get is as if the source code of the function
            # was copied in smallintobject.py.
            ns[new_name] = func_with_new_name(func, new_name, globals=ns)
    ns["get_integer"] = ns["pos__SmallInt"] = ns["int__SmallInt"]
    ns["get_negint"] = ns["neg__SmallInt"]

copy_multimethods(globals())

# extra imports needed because we switch the func_globals above
from pypy.interpreter.error import OperationError
from pypy.objspace.std.multimethod import FailedToImplementArgs
from pypy.rlib.rarithmetic import ovfcheck, ovfcheck_lshift, LONG_BIT, r_uint
from pypy.objspace.std.inttype import wrapint
from pypy.objspace.std.intobject import _impl_int_int_pow
from pypy.objspace.std.noneobject import W_NoneObject
from pypy.rlib.rbigint import rbigint

register_all(vars())
