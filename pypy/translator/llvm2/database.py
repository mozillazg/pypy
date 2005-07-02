from pypy.translator.llvm2.log import log 
from pypy.translator.llvm2.funcnode import FuncNode, FuncTypeNode
from pypy.translator.llvm2.structnode import StructNode, StructInstance
from pypy.translator.llvm2.arraynode import ArrayNode
from pypy.rpython import lltype
from pypy.objspace.flow.model import Block, Constant, Variable

log = log.database 

PRIMITIVES_TO_LLVM = {lltype.Signed: "int",
                      lltype.Char: "sbyte",
                      lltype.Unsigned: "uint",
                      lltype.Bool: "bool",
                      lltype.Float: "double" }

class Database(object): 
    def __init__(self, translator): 
        self._translator = translator
        self.obj2node = {}
        self._pendingsetup = []
        self._tmpcount = 1
        
    def addpending(self, key, node): 
        assert key not in self.obj2node, (
            "node with key %r already known!" %(key,))
        self.obj2node[key] = node 
        log("added to pending nodes:", node) 
        self._pendingsetup.append(node) 

    def prepare_repr_arg(self, const_or_var):
        """if const_or_var is not already in a dictionary self.obj2node,
        the appropriate node gets constructed and gets added to
        self._pendingsetup and to self.obj2node"""
        if const_or_var in self.obj2node:
            return
        if isinstance(const_or_var, Constant):
            
            ct = const_or_var.concretetype
            while isinstance(ct, lltype.Ptr):
                ct = ct.TO
            
            if isinstance(ct, lltype.FuncType):
                self.addpending(const_or_var, FuncNode(self, const_or_var))
            else:
                #value = const_or_var.value
                #while hasattr(value, "_obj"):
                #    value = value._obj
                
                if isinstance(ct, lltype.Struct):
                    self.addpending(const_or_var, StructInstance(self, value))

                elif isinstance(ct, lltype.Primitive):
                    log.prepare(const_or_var, "(is primitive)")
                else:
                    log.XXX("not sure what to do about %s(%s)" % (ct, const_or_var))
        else:
            log.prepare.ignore(const_or_var)

    def prepare_repr_arg_multi(self, args):
        for const_or_var in args:
            self.prepare_repr_arg(const_or_var)

    def prepare_repr_arg_type(self, type_):
        if type_ in self.obj2node:
            return
        if isinstance(type_, lltype.Primitive):
            pass
        elif isinstance(type_, lltype.Ptr): 
            self.prepare_repr_arg_type(type_.TO)

        elif isinstance(type_, lltype.Struct): 
            self.addpending(type_, StructNode(self, type_))

        elif isinstance(type_, lltype.FuncType): 
            self.addpending(type_, FuncTypeNode(self, type_))

        elif isinstance(type_, lltype.Array): 
            self.addpending(type_, ArrayNode(self, type_))

        else:     
            log.XXX("need to prepare typerepr", type_)

    def prepare_repr_arg_type_multi(self, types):
        for type_ in types:
            self.prepare_repr_arg_type(type_)

    def prepare_arg(self, const_or_var):
        log.prepare(const_or_var)
        self.prepare_repr_arg_type(const_or_var.concretetype)
        self.prepare_repr_arg(const_or_var)
            
    def setup_all(self):
        while self._pendingsetup: 
            self._pendingsetup.pop().setup()

    def getobjects(self, subset_types=None):
        res = []
        for v in self.obj2node.values():
            if subset_types is None or isinstance(v, subset_types):
                res.append(v)
        res.reverse()
        return res

    def get_typedecls(self):
        return self.getobjects((StructNode, ArrayNode, FuncTypeNode))

    def get_globaldata(self):
        return self.getobjects((StructInstance))

    def get_functions(self):
        struct_nodes = [n for n in self.getobjects(StructNode) if n.inline_struct]
        return struct_nodes + self.getobjects(FuncNode)

    def dump(self):

        # get and reverse the order in which seen objs
        all_objs = self.obj2node.items()
        all_objs.reverse()

        log.dump_db("*** type declarations ***")
        for k,v in all_objs:
            if isinstance(v, (StructNode, ArrayNode)):
                log.dump_db("%s ---> %s" % (k, v))            

        log.dump_db("*** global data ***")
        for k,v in all_objs:
            if isinstance(v, (StructInstance)):
                log.dump_db("%s ---> %s" % (k, v))

        log.dump_db("*** function protos ***")
        for k,v in all_objs:
            if isinstance(v, (FuncNode)):
                log.dump_db("%s ---> %s" % (k, v))

        log.dump_db("*** function implementations ***")
        for k,v in all_objs:
            if isinstance(v, (FuncNode)):
                log.dump_db("%s ---> %s" % (k, v))
                
        log.dump_db("*** unknown ***")
        for k,v in all_objs:
            if isinstance(v, (FuncTypeNode)):
                log.dump_db("%s ---> %s" % (k, v))
        
    # __________________________________________________________
    # Getters
    
    def repr_arg(self, arg):
        if (isinstance(arg, Constant) and 
            isinstance(arg.concretetype, lltype.Primitive)):
            return str(arg.value).lower() #False --> false
        elif isinstance(arg, Variable):
            return "%" + str(arg)
        return self.obj2node[arg].ref

    def repr_arg_type(self, arg):
        if isinstance(arg, (Constant, Variable)): 
            arg = arg.concretetype 
        try:
            return self.obj2node[arg].ref 
        except KeyError: 
            if isinstance(arg, lltype.Primitive):
                return PRIMITIVES_TO_LLVM[arg]
            elif isinstance(arg, lltype.Ptr):
                return self.repr_arg_type(arg.TO) + '*'
            else: 
                raise TypeError("cannot represent %r" %(arg,))

    def repr_arg_multi(self, args):
        return [self.repr_arg(arg) for arg in args]

    def repr_arg_type_multi(self, args):
        return [self.repr_arg_type(arg) for arg in args]

    def repr_tmpvar(self): 
        count = self._tmpcount 
        self._tmpcount += 1
        return "%tmp." + str(count) 
