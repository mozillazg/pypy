import py
from pypy.rpython import lltype
from pypy.translator.llvm2.log import log
from pypy.translator.llvm2.node import LLVMNode
from pypy.objspace.flow.model import Constant
from pypy.translator.llvm2 import varsize 
import itertools  
log = log.structnode

nextnum = itertools.count().next 

class ArrayTypeNode(LLVMNode):
    _issetup = False
    def __init__(self, db, array):
        self.db = db
        assert isinstance(array, lltype.Array)
        self.array = array
        c = nextnum()
        ref_template = "%%array.%s." + str(c)

        # ref is used to reference the arraytype in llvm source 
        self.ref = ref_template % array.OF
        # constructor_ref is used to reference the constructor 
        # for the array type in llvm source code 
        self.constructor_ref = "%%new.array.%s" % c 
        # constructor_decl is used to declare the constructor
        # for the array type (see writeimpl). 
        self.constructor_decl = "%s * %s(int %%len)" % \
                                (self.ref, self.constructor_ref)

    def __str__(self):
        return "<ArrayTypeNode %r>" % self.ref
        
    def setup(self):
        self.db.prepare_repr_arg_type(self.array.OF)
        self._issetup = True

    # ______________________________________________________________________
    # entry points from genllvm
    #
    def writedatatypedecl(self, codewriter):
        codewriter.arraydef(self.ref, self.db.repr_arg_type(self.array.OF))

    def writedecl(self, codewriter): 
        # declaration for constructor
        codewriter.declare(self.constructor_decl)

    def writeimpl(self, codewriter):
        log.writeimpl(self.ref)
        fromtype = self.db.repr_arg_type(self.array.OF) 
        varsize.write_constructor(codewriter, self.ref, 
                                  self.constructor_decl,
                                  fromtype)

# Each ArrayNode instance is a global constant. 

class ArrayNode(LLVMNode):

    _issetup = False 

    def __init__(self, db, value):
        self.db = db
        self.ref = "%%arrayinstance.%s.%s" % (value._TYPE.OF, nextnum())
        self.value = value

    def __str__(self):
        return "<ArrayNode %r>" %(self.ref,)

    def setup(self):
        T = self.value._TYPE.OF
        for item in self.value.items:
            if not isinstance(T, lltype.Primitive):
                # Create a dummy constant hack XXX
                c = Constant(item, T)
                self.db.prepare_arg(c)
        self._issetup = True

    def getall(self):
        "Returns the type and value for this node. "
        arraylen = len(self.value.items)

        res = []

        T = self.value._TYPE.OF
        typval = self.db.repr_arg_type(self.value._TYPE.OF)
        for value in self.value.items:
            if not isinstance(T, lltype.Primitive):
                # Create a dummy constant hack XXX
                value = self.db.repr_arg(Constant(value, T))
            else:
                if isinstance(value, str):
                    value = ord(value)
                    
                value = str(value)
            res.append((typval, value))

        type_ = "{ int, [%s x %s] }" % (arraylen,
                                        self.db.repr_arg_type(self.value._TYPE.OF))
        
        arrayvalues = ", ".join(["%s %s" % (t, v) for t, v in res])
        value = "int %s, [%s x %s] [ %s ]" % (arraylen,
                                              arraylen,
                                              typval,
                                              arrayvalues)
        return type_, value
    
    def writeglobalconstants(self, codewriter):
        type_, values = self.getall()
        codewriter.globalinstance(self.ref, type_, values)
