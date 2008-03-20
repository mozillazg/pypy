from pypy.rpython.lltypesystem import llmemory
from pypy.rpython.ootypesystem import ootype

class TypeSystemHelper(object):

    def _freeze_(self):
        return True


class LLTypeHelper(TypeSystemHelper):

    name = 'lltype'
    ROOT_TYPE = llmemory.Address

    def get_typeptr(self, obj):
        return obj.typeptr


class OOTypeHelper(TypeSystemHelper):

    name = 'ootype'
    ROOT_TYPE = llmemory.Address # XXX: should be ootype.ROOT
    #ROOT_TYPE = ootype.ROOT

    def get_typeptr(self, obj):
        return obj.meta


llhelper = LLTypeHelper()
oohelper = OOTypeHelper()
