import py
from pypy.translator.llvm2.log import log 
log = log.structnode 

class ArrayNode(object):
    _issetup = False 
    array_counter = 0

    def __init__(self, db, array): 
        self.db = db
        self.array = array
        self.ref = "%%array.%s.%s" % (array.OF, ArrayNode.array_counter)
        ArrayNode.array_counter += 1
        
    def __str__(self):
        return "<ArrayNode %r>" % self.ref    

    def setup(self):
        self._issetup = True

    # ______________________________________________________________________
    # entry points from genllvm 
    #
    def writedatatypedecl(self, codewriter):
        codewriter.arraydef(self.ref, self.db.repr_arg_type(self.array.OF))
