""" Contains a mechanism for turning any class instance and any integer into a
pointer-like thing. Gives full control over pointer tagging, i.e. there won't
be tag checks everywhere in the C code. """

import sys
from pypy.annotation import model as annmodel
from pypy.tool.pairtype import pairtype
from pypy.rpython.extregistry import ExtRegistryEntry
from pypy.rpython.rclass import getinstancerepr
from pypy.rpython.rmodel import Repr
from pypy.rpython.lltypesystem.lloperation import llop
from pypy.rpython.lltypesystem.rclass import OBJECTPTR
from pypy.rpython.lltypesystem import lltype
from pypy.rpython.error import TyperError



def erase(x):
    """Creates an 'erased' object that contains a reference to 'x'. Nothing can
    be done with this object, except calling unerase(y, <type>) on it.
    x needs to be either an instance or an integer fitting into 31/63 bits."""
    if isinstance(x, int):
        res = 2 * x + 1
        if res > sys.maxint or res < -sys.maxint - 1:
            raise OverflowError
    return Erased(x)

def unerase(y, type):
    """Turn an erased object back into an object of type 'type'."""
    if y._x is None:
        return None
    assert isinstance(y._x, type)
    return y._x

def is_integer(e):
    """Gives information whether the erased argument is a tagged integer or not."""
    return isinstance(e._x, int)


# ---------- implementation-specific ----------

class Erased(object):
    def __init__(self, x):
        self._x = x
    def __repr__(self):
        return "Erased(%r)" % (self._x, )

class Entry(ExtRegistryEntry):
    _about_ = erase

    def compute_result_annotation(self, s_obj):
        return someErased

    def specialize_call(self, hop):
        return hop.r_result.specialize_call(hop)

class Entry(ExtRegistryEntry):
    _about_ = unerase

    def compute_result_annotation(self, s_obj, s_type):
        assert s_type.is_constant()
        if s_type.const is int:
            return annmodel.SomeInteger()
        assert isinstance(s_type, annmodel.SomePBC)
        assert len(s_type.descriptions) == 1
        clsdef = s_type.descriptions.keys()[0].getuniqueclassdef()
        return annmodel.SomeInstance(clsdef)

    def specialize_call(self, hop):
        v, t = hop.inputargs(hop.args_r[0], lltype.Void)
        if isinstance(hop.s_result, annmodel.SomeInteger):
            c_one = hop.inputconst(lltype.Signed, 1)
            vi = hop.genop('cast_ptr_to_int', [v], resulttype=lltype.Signed)
            return hop.genop('int_rshift', [vi, c_one], resulttype=lltype.Signed)
        return hop.genop('cast_pointer', [v], resulttype = hop.r_result)

class Entry(ExtRegistryEntry):
    _about_ = is_integer

    def compute_result_annotation(self, s_obj):
        return annmodel.SomeBool()

    def specialize_call(self, hop):
        v, = hop.inputargs(hop.args_r[0])
        c_one = hop.inputconst(lltype.Signed, 1)
        vi = hop.genop('cast_ptr_to_int', [v], resulttype=lltype.Signed)
        vb = hop.genop('int_and', [vi, c_one], resulttype=lltype.Signed)
        return hop.genop('int_is_true', [vb], resulttype=lltype.Bool)


class Entry(ExtRegistryEntry):
    _type_ = Erased

    def compute_annotation(self):
        from pypy.rlib import _jit_vref
        s_obj = self.bookkeeper.immutablevalue(self.instance._x)
        return someErased

# annotation and rtyping support 

class SomeErased(annmodel.SomeObject):

    def __init__(self):
        pass

    def can_be_none(self):
        return False # cannot be None, but can contain a None

    def rtyper_makerepr(self, rtyper):
        return ErasedRepr(rtyper)

    def rtyper_makekey(self):
        return self.__class__,

someErased = SomeErased()

class __extend__(pairtype(SomeErased, SomeErased)):

    def union((serased1, serased2)):
        return serased1


class ErasedRepr(Repr):
    lowleveltype = OBJECTPTR
    def __init__(self, rtyper):
        self.rtyper = rtyper

    def specialize_call(self, hop):
        s_arg, = hop.args_s
        if isinstance(s_arg, annmodel.SomeInstance):
            r_generic_object = getinstancerepr(hop.rtyper, None)
            hop.exception_cannot_occur()
            [v] = hop.inputargs(r_generic_object)   # might generate a cast_pointer
            return v
        else:
            assert isinstance(s_arg, annmodel.SomeInteger)
            v_value = hop.inputarg(lltype.Signed, arg=0)
            c_one = hop.inputconst(lltype.Signed, 1)
            hop.exception_is_here()
            v2 = hop.genop('int_lshift_ovf', [v_value, c_one],
                           resulttype = lltype.Signed)
            v2p1 = hop.genop('int_add', [v2, c_one],
                             resulttype = lltype.Signed)
            v_instance =  hop.genop('cast_int_to_ptr', [v2p1],
                                    resulttype = self.lowleveltype)
            return v_instance


    def convert_const(self, value):
        if isinstance(value._x, int):
            return lltype.cast_int_to_ptr(self.lowleveltype, value._x * 2 + 1)
        else:
            r_generic_object = getinstancerepr(self.rtyper, None)
            v = r_generic_object.convert_const(value._x)
            return v

