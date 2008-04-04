from pypy.rpython.lltypesystem import lltype, llmemory
from pypy.rpython.ootypesystem import ootype

def deref(T):
    if isinstance(T, lltype.Ptr):
        return T.TO
    assert isinstance(T, ootype.OOType)
    return T

def fieldType(T, name):
    if isinstance(T, lltype.Struct):
        return getattr(T, name)
    elif isinstance(T, (ootype.Instance, ootype.Record)):
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

    def genop_ptr_iszero(self, builder, argbox, gv_addr):
        return builder.genop1("ptr_iszero", gv_addr)

    def genop_ptr_nonzero(self, builder, argbox, gv_addr):
        return builder.genop1("ptr_nonzero", gv_addr)

    def get_FuncType(self, ARGS, RESULT):
        FUNCTYPE = lltype.FuncType(ARGS, RESULT)
        FUNCPTRTYPE = lltype.Ptr(FUNCTYPE)
        return FUNCTYPE, FUNCPTRTYPE

class OOTypeHelper(TypeSystemHelper):

    name = 'ootype'
    ROOT_TYPE = ootype.Object

    def get_typeptr(self, obj):
        return obj.meta

    def genop_malloc_fixedsize(self, builder, alloctoken):
        return builder.genop_new(alloctoken)

    def genop_ptr_iszero(self, builder, argbox, gv_addr):
        return builder.genop_ooisnull(gv_addr)

    def genop_ptr_nonzero(self, builder, argbox, gv_addr):
        return builder.genop_oononnull(gv_addr)

    def get_FuncType(self, ARGS, RESULT):
        FUNCTYPE = ootype.StaticMethod(ARGS, RESULT)
        return FUNCTYPE, FUNCTYPE


llhelper = LLTypeHelper()
oohelper = OOTypeHelper()
