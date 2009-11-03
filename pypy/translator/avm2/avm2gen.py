
""" backend generator routines
"""

from pypy.objspace.flow import model as flowmodel
from pypy.rpython.ootypesystem import ootype
from pypy.translator.avm2 import assembler, constants, instructions, abc, types
# from pypy.translator.oosupport.treebuilder import SubOperation
from pypy.translator.oosupport.metavm import Generator
from pypy.translator.oosupport.constant import push_constant
from collections import namedtuple
from itertools import chain

class GlobalContext(object):
    CONTEXT_TYPE = "global"
    parent = None

    def __init__(self, gen):
        self.gen = gen
    
    def new_script(self):
        return ScriptContext(self)

class ScriptContext(object):
    CONTEXT_TYPE = "script"

    def __init__(self, gen, parent):
        self.gen, self.parent = gen, parent
    
    def init(self):
        self.init = abc.AbcMethodInfo("$init", [], constants.QName("void"))
        ctx = MethodContext(self.gen, self.init, self)
        self.gen.enter_context(ctx)
        
    def exit(self):
        assert self.parent.CONTEXT_TYPE == "global"
        self.gen.abc.scripts.index_for(abc.AbcScriptInfo(self.init._info_index))
        return self.parent

class ClassContext(object):
    CONTEXT_TYPE = "class"

    def __init__(self, gen, name, super_name, parent):
        self.gen, self.name, self.super_name, self.parent = gen, name, super_name, parent
        self.methods = []
        self.static  = []
        self.instance_traits = []
        self.static_traits   = []

    def cinit(self):
        self.cinit = abc.AbcMethodInfo("$cinit", [], constants.QName("*"))
        ctx = MethodContext(self.gen, self.cinit, self)
        self.gen.enter_context(ctx)
        
        self.gen.I(instructions.getlocal(0))
        self.gen.I(instructions.pushscope())

    def iinit(self, params):
        self.iinit = abc.AbcMethodInfo("$construct", [p.multiname() for n, p in params], constants.QName("*"))
        ctx = MethodContext(self.gen, self.iinit, self, len(params))

        # constructor prologoue
        self.gen.enter_context(ctx)
        self.gen.I(instructions.getlocal(0))
        self.gen.I(instructions.pushscope())

    def new_method(self, name, params, rettype, static=None):
        meth = abc.AbcMethodInfo(name, [p.multiname() for n, p in params], rettype.multiname())
        self.methods.append(meth)
        self.enter_context(MethodContext(self.gen, meth, self, len(params)))

    def add_instance_trait(self, trait):
        self.instance_traits.append(trait)

    def add_static_trait(self, trait):
        self.static_traits.append(trait)
    
    def exit(self):
        assert self.parent.CONTEXT_TYPE == "script"
        self.instance = abc.AbcInstanceInfo(self.name, self.iinit, traits=self.instance_traits, super_name=self.super_name)
        self.classobj = abc.AbcClassInfo(self.cinit, traits=self.static_traits)
        self.gen.abc.instances.index_for(self.instance)
        self.gen.abc.classes.index_for(self.classobj)
        return self.parent
        
class MethodContext(object):
    CONTEXT_TYPE = "method"
    
    def __init__(self, gen, method, parent, num_params):
        self.gen, self.method, self.parent = gen, method, parent
        self.asm = assembler.Avm2CodeAssembler(gen.constants, 1+num_params)
        self.acv_traits = []

    def exit(self):
        self.asm.add(instructions.returnvoid())
        self._info_index = self.gen.abc.methods.index_for(self.method)
        self.gen.abc.bodies.index_for(abc.AbcMethodBodyInfo(self.method, self.asm, self.acv_traits))
        return self.parent

    def add_activation_trait(self, trait):
        self.acv_traits.append(trait)
    
    def add_instructions(self, *instructions):
        self.asm.add(instructions)

    def next_free_local(self):
        return self.asm.next_free_local()

    def set_local(self, index):
        return self.asm.set_local(index)

    def kill_local(self, index):
        return self.asm.kill_local(index)

Context = namedtuple("Context", "asm body method parent registers")

class Avm2ilasm(Generator):
    """ AVM2 'assembler' generator routines """
    def __init__(self, db):
        # self.scope = Scope(asm, None, constants.ValuePool("this"), [constants.PACKAGE_NAMESPACE, constants.PRIVATE_NAMESPACE])
        self.constants = constants.AbcConstantPool()
        self.abc = abc.AbcFile(self.constants)
        self.context = GlobalContext(self)
        #self.script0 = abc.AbcMethodInfo("$init", constants.QName("void"))
        #self.context = Context(assembler.Avm2CodeAssembler(self.constants), None, constants.ValuePool())
        
    def I(self, *instructions):
        assert self.context.CONTEXT_TYPE == "method"
        self.context.add_instructions(instructions)

    def M(self, multiname):
        return self.constants.multiname_pool.index_for(multiname)

    def SL(self, index=None):
        assert self.context.CONTEXT_TYPE == "method"
        if index is None:
            index = self.context.next_free_local()
        self.context.set_local(index)
        self.I(instructions.setlocal(index))
        return index

    def KL(self, index):
        assert self.context.CONTEXT_TYPE == "method"
        self.context.kill_local(index)

    def begin_class(self, qname):
        pass

    # @property
    # def current_namespaces(self):
    #     context = self.scope
    #     namespaces = []
    #     while context is not None:
    #         namespaces += context.namespaces
    #         context = context.parent
    #     return namespaces
        
    def enter_context(self, ctx):
        self.context = ctx

    def exit_context(self):
        ctx = self.context
        self.context = self.context.exit()
        return ctx.block

    def current_class(self):
        context = self.context
        while context is not None:
            if context.CONTEXT_TYPE == "class":
                return context
            context = context.parent
    
    @property
    def registers(self):
        return self.scope.registers
        
    def pop(self):
        self.I(instructions.pop())

    def dup(self):
        self.I(instructions.dup())

    def swap(self):
        self.I(instructions.swap())

    def emit(self, instr, *args):
        self.I(instructions.INSTRUCTIONS[instr](*args))

    def load(self, v, *args):
        if isinstance(v, flowmodel.Variable):
            if v.concretetype is ootype.Void:
                return # ignore it
            else:
                self.push_local(v)
        elif isinstance(v, flowmodel.Constant):
            push_constant(self.db, v.concretetype, v.value, self)
        else:
            self.push_const(v)

        for i in args:
            self.load(i)

    def store_var(self, v):
        self.I(instructions.setlocal(self.registers.index_for(v)))

    def store_local(self, v):
        self.store_var(v.name)

    def call_oostring(self, OOTYPE):
        self.I(instructions.findpropstrict(self.M(types._str_qname)))
        self.swap()
        self.I(instructions.callproperty(self.M(types._str_qname), 1))
        
    call_oounicode = call_oostring

    def call_this_const(self, name):
        self.I(instructions.getlocal0())
        self.I(instructions)

    def newarray(self, TYPE, length=1):
        self.I(instructions.getlex(self.M(types._arr_qname)))
        self.push_const(length)
        self.I(instructions.construct(1))

    def oonewarray(self, TYPE, length=1):
        self.I(instructions.getlex(self.M(types._vec_qname)))
        self.load(TYPE)
        self.I(instructions.applytype(1))
        self.push_const(length)
        self.I(instructions.coerce(self.M(constants.TypeName(
                        types._vec_qname, self.cts.lltype_to_cts(TYPE).multiname()))))
        self.I(instructions.construct(1))

    # def initvector(self, TYPE, 
    
    def push_this(self):
        self.I(instructions.getlocal(0))
    
    def push_local(self, v):
        self.push_var(v.name)

    push_arg = push_local

    def push_var(self, v):
        assert v in self.registers
        self.I(instructions.getlocal(self.registers.index_for(v)))

    def push_const(self, v):
        if isinstance(v, int):
            if 0 <= v < 256:
                self.I(instructions.pushbyte(v))
            elif v >= 0:
                self.I(instructions.pushuint(self.constants.uint_pool.index_for(v)))
            else:
                self.I(instructions.pushint(self.constants.int_pool.index_for(v)))
        elif isinstance(v, float):
            self.I(instructions.pushdouble(self.constants.double_pool.index_for(v)))
        elif isinstance(v, basestring):
            self.I(instructions.pushstring(self.constants.utf8_pool.index_for(v)))
        elif v is True:
            self.I(instructions.pushtrue())
        elif v is False:
            self.I(instructions.pushfalse())

    def push_undefined(self):
        self.I(instructions.pushundefined())

    def push_null(self, TYPE=None):
        self.I(instructions.pushnull())

    def push_primitive_constant(self, TYPE, value):
        if TYPE is ootype.Void:
            self.push_null()
        elif TYPE is ootype.String:
            if value._str is None:
                self.push_null()
            else:
                self.push_const(value._str)
        else:
            self.push_const(value)

    def init_array(self, members=[]):
        self.load(*members)
        self.I(instructions.newarray(len(members)))

    def init_object(self, members={}):
        self.load(*chain(*members.items()))
        self.I(instructions.newobject(len(members)))

    def init_vector(self, members=[]):
        self.load()
