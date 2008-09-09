
from pypy.objspace.std.objspace import W_Object

class W_SeqObject(W_Object):
    """ This is a common superclass for W_ListObject and W_TupleObject.
    it's purpose is to have some methods that present common interface
    to accessing items from interp-level. The whole idea is to not have
    wrappeditems of both shared
    """

    def getlength(self):
        return len(self.wrappeditems)

    def getitem(self, i):
        return self.wrappeditems[i]
