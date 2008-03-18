class TypeSystemHelper(object):

    def _freeze_(self):
        return True


class LLTypeHelper(TypeSystemHelper):

    name = 'lltype'
    
    def get_typeptr(self, obj):
        return obj.typeptr


class OOTypeHelper(TypeSystemHelper):

    name = 'ootype'

    def get_typeptr(self, obj):
        return obj.meta


llhelper = LLTypeHelper()
oohelper = OOTypeHelper()
