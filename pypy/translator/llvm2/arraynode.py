import py
from pypy.rpython import lltype
from pypy.translator.llvm2.log import log
from pypy.translator.llvm2.node import LLVMNode
log = log.structnode

class ArrayTypeNode(LLVMNode):
    _issetup = False
    def __init__(self, db, array):
        self.db = db
        assert isinstance(array, lltype.ArrayType)
        self.array = array
        self.ref_template = "%%array.%s" % array.OF
        self.ref = self.ref_template + ".0"

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


# Each ArrayNode is a global constant.  This needs to have a specific type of
# a certain type.

class ArrayNode(LLVMNode):

    _issetup = False 
    array_counter = 0

    def __init__(self, db, value):
        self.db = db
        self.name = "%s.%s" % (value._TYPE.OF, ArrayNode.array_counter)
        self.ref = "%%stinstance.%s" % self.name
        self.value = value
        ArrayNode.array_counter += 1

    def __str__(self):
        return "<ArrayNode %r>" %(self.ref,)

    def setup(self):
        T = self.value._TYPE.OF
        for item in self.value.items:
            if not isinstance(T, lltype.Primitive):
                value = getattr(self.value, name)
                # Create a dummy constant hack XXX
                c = Constant(value, T)
                self.db.prepare_arg(c)

        self._issetup = True

    def get_values(self):
        res = []

        T = self.value._TYPE.OF
        typval = self.db.repr_arg_type(self.value._TYPE.OF)
        for value in self.value.items:
            if not isinstance(T, lltype.Primitive):
                # Create a dummy constant hack XXX
                value = self.db.repr_arg(Constant(value, T))
            else:
                value = repr(value)
            res.append((typval, value))

        return ", ".join(["%s %s" % (t, v) for t, v in res])

    def writeglobalconstants(self, codewriter):
        lenitems = len(self.value.items)
        lenstr = ".%s" % lenitems
        codewriter.globalinstance(self.ref,
                                  self.db.repr_arg_type() + lenstr,
                                  self.get_values())
