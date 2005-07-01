import py
from pypy.objspace.flow.model import Block, Constant, Variable, Link
from pypy.translator.llvm2.log import log 
from pypy.rpython import lltype
log = log.structnode 

class StructNode(object):
    _issetup = False 
    struct_counter = 0

    def __init__(self, db, struct): 
        assert isinstance(struct, lltype.Struct)

        self.db = db
        self.struct = struct
        
        self.name = "%s.%s" % (self.struct._name, StructNode.struct_counter)
        self.ref = "%%st.%s" % self.name
        self.inline_struct = self.struct._arrayfld
        
        StructNode.struct_counter += 1
        
    def __str__(self):
        return "<StructNode %r>" %(self.ref,)
    
    def setup(self):
        # Recurse
        for fieldname in self.struct._names:
            field_type = getattr(self.struct, fieldname)
            self.db.prepare_repr_arg_type(field_type)

        if self.inline_struct:
            log.XXX("Register me", self)

        self._issetup = True

    def get_decl_for_varsize(self):
        self.new_var_name = "%%new.st.%s" % self.name
        return "%s * %s(int %%len)" % (self.ref, self.new_var_name)

    # ______________________________________________________________________
    # main entry points from genllvm 

    def writedatatypedecl(self, codewriter):
        assert self._issetup 
        struct = self.struct
        l = []
        for fieldname in struct._names:
            type_ = getattr(struct, fieldname)
            l.append(self.db.repr_arg_type(type_))
        codewriter.structdef(self.ref, l) 

    def writedecl(self, codewriter): 
        # declaration for constructor
        if self.inline_struct:
            # XXX Not well thought out - hack / better to modify the graph
            codewriter.declare(self.get_decl_for_varsize())

    def writeimpl(self, codewriter):

        if self.inline_struct:
            log.writeimpl(self.ref)
            codewriter.openfunc(self.get_decl_for_varsize())
            codewriter.label("block0")
            
            # XXX TODO
            arraytype = "sbyte"
            indices_to_array = [("uint", 1)]
            
            # Into array and length            
            indices = indices_to_array + [("uint", 1), ("int", "%len")]
            codewriter.getelementptr("%size", self.ref + "*",
                                     "null", *indices)
            
            #XXX is this ok for 64bit?
            codewriter.cast("%sizeu", arraytype + "*", "%size", "uint")
            codewriter.malloc("%resulttmp", "sbyte", "uint", "%sizeu")
            codewriter.cast("%result", "sbyte*", "%resulttmp", self.ref + "*")

            # remember the allocated length for later use.
            indices = indices_to_array + [("uint", 0)]
            codewriter.getelementptr("%size_ptr", self.ref + "*",
                                     "%result", *indices)

            codewriter.cast("%signedsize", "uint", "%sizeu", "int")
            codewriter.store("int", "%signedsize", "%size_ptr")

            codewriter.ret(self.ref + "*", "%result")
            codewriter.closefunc()


class StructInstance(object):
    _issetup = False 
    struct_counter = 0

    def __init__(self, db, value):
        self.db = db
        self.name = "%s.%s" % (value._TYPE._name, StructInstance.struct_counter)
        self.ref = "%%stinstance.%s" % self.name
        self.value = value
        StructInstance.struct_counter += 1

    def __str__(self):
        return "<StructInstance %r>" %(self.ref,)

    def setup(self):
        # Recurse fields (XXX Messy!)
        for name in self.value._TYPE._names:
            T = self.value._TYPE._flds[name]
            self.db.prepare_repr_arg_type(T)
            if not isinstance(T, lltype.Primitive):
                value = getattr(self.value, name)
                self.db.prepare_repr_arg(value)
                
        self._issetup = True

#     def struct_repr(self):
#         typ = repr_arg_type(self.value)
#         self.value._TYPE._names
#         typevaluepairs = ["%s %s" % for t, v in 
#         typevaluepairsstr = ", ".join(typevaluepairs)
#         return "%s { %s }" % (typ, typevaluepairsstr)

    def writedata(self, codewriter):
        log.XXXXXXXXXX("ooops TODO should write - ", self.ref)
        for name in self.value._TYPE._names:
            log.XXXXXXXXXX("ooops ", getattr(self.value, name))
        typ = self.db.repr_arg_type(self.value._TYPE)
        # XXX constant you say?
        codewriter.append("%s = internal constant %s* null" % (self.ref, typ))
