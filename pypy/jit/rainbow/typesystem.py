from pypy.rpython.lltypesystem import lltype, llmemory
from pypy.rpython.ootypesystem import ootype

def deref(T):
    if isinstance(T, lltype.Ptr):
        return T.TO
    assert isinstance(T, (ootype.Instance, ootype.Record))
    return T

def fieldType(T, name):
    if isinstance(T, lltype.Struct):
        return getattr(T, name)
    elif isinstance(T, ootype.Instance):
        _, FIELD = T._lookup_field(name)
        return FIELD
    else:
        assert False

class TypeSystemHelper(object):

    def _freeze_(self):
        return True

class LLTypeHelper(TypeSystemHelper):

    name = 'lltype'
    ROOT_TYPE = llmemory.Address

    def get_typeptr(self, obj):
        return obj.typeptr

    def genop_malloc_fixedsize(self, builder, alloctoken):
        return builder.genop_malloc_fixedsize(alloctoken)

class OOTypeHelper(TypeSystemHelper):

    name = 'ootype'
    ROOT_TYPE = ootype.ROOT

    def get_typeptr(self, obj):
        return obj.meta

    def genop_malloc_fixedsize(self, builder, alloctoken):
        return builder.genop_new(alloctoken)


llhelper = LLTypeHelper()
oohelper = OOTypeHelper()
