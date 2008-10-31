import py
from pypy.tool.pairtype import extendabletype
from pypy.rlib.rarithmetic import intmask
from pypy.rpython.ootypesystem import ootype
from pypy.rpython.lltypesystem import lltype
from pypy.rlib.objectmodel import specialize
from pypy.rlib.rarithmetic import r_uint
from pypy.jit.codegen.model import AbstractRGenOp, GenBuilder, GenLabel
from pypy.jit.codegen.model import GenVarOrConst, GenVar, GenConst
from pypy.jit.codegen.model import CodeGenSwitch
from pypy.jit.codegen.model import ReplayBuilder, dummy_var
from pypy.jit.codegen.cli import operation as ops
from pypy.jit.codegen.cli.methodfactory import get_method_wrapper
from pypy.jit.codegen.cli.args_manager import ArgsManager
from pypy.translator.cli.dotnet import CLR, typeof, new_array, init_array
from pypy.translator.cli.dotnet import box, unbox, clidowncast, classof
from pypy.translator.cli.dotnet import class2type, type2class
from pypy.translator.cli import dotnet
System = CLR.System
DelegateHolder = CLR.pypy.runtime.DelegateHolder
IntLowLevelFlexSwitch = CLR.pypy.runtime.IntLowLevelFlexSwitch
ObjectLowLevelFlexSwitch = CLR.pypy.runtime.ObjectLowLevelFlexSwitch
FlexSwitchCase = CLR.pypy.runtime.FlexSwitchCase
MethodIdMap = CLR.pypy.runtime.MethodIdMap
OpCodes = System.Reflection.Emit.OpCodes
InputArgs = CLR.pypy.runtime.InputArgs

cVoid = ootype.nullruntimeclass
cInt32 = classof(System.Int32)
cBoolean = classof(System.Boolean)
cDouble = classof(System.Double)
cObject = classof(System.Object)
cString = classof(System.String)
cChar = classof(System.Char)
cUtils = classof(CLR.pypy.runtime.Utils)
cFlexSwitchCase = classof(FlexSwitchCase)
cpypyString = classof(CLR.pypy.runtime.String)

class SigToken:
    def __init__(self, args, res, funcclass):
        self.args = args
        self.res = res
        self.funcclass = funcclass

class FieldToken:
    def __init__(self, ooclass, name):
        self.ooclass = ooclass
        self.name = name

    def getFieldInfo(self):
        clitype = class2type(self.ooclass)
        return clitype.GetField(str(self.name))

class MethToken:

    def __init__(self, ooclass, name):
        self.ooclass = ooclass
        self.name = name

    def getMethodInfo(self):
        clitype = class2type(self.ooclass)
        res = clitype.GetMethod(str(self.name))
        if res is None:
            print 'getMethodInfo --> None'
            print 'clitype =', clitype.get_FullName()
            print 'name =', self.name
        return res

    def getReturnType(self):
        methodinfo = self.getMethodInfo()
        return methodinfo.get_ReturnType()

    def emit_call(self, il):
        raise NotImplementedError


class VirtualMethToken(MethToken):

    def emit_call(self, il):
        methodinfo = self.getMethodInfo()
        il.Emit(OpCodes.Callvirt, methodinfo)


class StaticMethodToken(MethToken):

    def emit_call(self, il):
        methodinfo = self.getMethodInfo()
        il.Emit(OpCodes.Call, methodinfo)

class ArrayMethodToken(MethToken):

    def __init__(self, name, itemclass):
        self.name = name
        self.itemclass = itemclass

    def getReturnType(self):
        if self.name == 'll_getitem_fast':
            return class2type(self.itemclass)
        elif self.name == 'll_setitem_fast':
            return class2type(cVoid) # ???
        elif self.name == 'll_length':
            return class2type(cInt32)
        else:
            assert False

    def emit_call(self, il):
        itemtype = class2type(self.itemclass)
        if self.name == 'll_getitem_fast':
            il.Emit(OpCodes.Ldelem, itemtype)
        elif self.name == 'll_setitem_fast':
            il.Emit(OpCodes.Stelem, itemtype)
        elif self.name == 'll_length':
            il.Emit(OpCodes.Ldlen)
        else:
            assert False

class AllocToken:
    def __init__(self, ooclass):
        self.ooclass = ooclass

    def getCliType(self):
        return class2type(self.ooclass)

class __extend__(GenVarOrConst):
    __metaclass__ = extendabletype

    def getCliType(self):
        raise NotImplementedError

    def getkind(self):
        return type2class(self.getCliType())

    def load(self, meth):
        gv = meth.map_genvar(self)
        gv._do_load(meth)

    def store(self, meth):
        gv = meth.map_genvar(self)
        gv._do_store(meth)

    def _do_load(self, meth):
        raise NotImplementedError

    def _do_store(self, meth):
        raise NotImplementedError

class GenArgVar(GenVar):
    def __init__(self, index, cliType):
        self.index = index
        self.cliType = cliType

    def getCliType(self):
        return self.cliType

    def _do_load(self, meth):
        if self.index == 0:
            meth.il.Emit(OpCodes.Ldarg_0)
        elif self.index == 1:
            meth.il.Emit(OpCodes.Ldarg_1)
        elif self.index == 2:
            meth.il.Emit(OpCodes.Ldarg_2)
        elif self.index == 3:
            meth.il.Emit(OpCodes.Ldarg_3)
        else:
            meth.il.Emit(OpCodes.Ldarg, self.index)

    def _do_store(self, meth):
        meth.il.Emit(OpCodes.Starg, self.index)

    def __repr__(self):
        return "GenArgVar(%d)" % self.index

class GenLocalVar(GenVar):
    def __init__(self, meth, v):
        self.v = v

    def getCliType(self):
        return self.v.get_LocalType()

    def _do_load(self, meth):
        meth.il.Emit(OpCodes.Ldloc, self.v)

    def _do_store(self, meth):
        meth.il.Emit(OpCodes.Stloc, self.v)


class IntConst(GenConst):

    def __init__(self, value, cliclass):
        self.value = value
        self.cliclass = cliclass

    @specialize.arg(1)
    def revealconst(self, T):
        if T is ootype.Object:
            return ootype.NULL # XXX?
        elif isinstance(T, ootype.OOType):
            return ootype.null(T) # XXX
        return lltype.cast_primitive(T, self.value)

    def getCliType(self):
        return class2type(self.cliclass)

    def load(self, meth):
        meth.il.Emit(OpCodes.Ldc_I4, self.value)

    def __repr__(self):
        return "int const=%s" % self.value


class FloatConst(GenConst):

    def __init__(self, value):
        self.value = value

    @specialize.arg(1)
    def revealconst(self, T):
        if T is ootype.Object:
            return ootype.NULL # XXX?
        elif isinstance(T, ootype.OOType):
            return ootype.null(T) # XXX
        return lltype.cast_primitive(T, self.value)

    def getCliType(self):
        return typeof(System.Double)

    def load(self, meth):
        meth.il.Emit(OpCodes.Ldc_R8, self.value)

    def __repr__(self):
        return "float const=%s" % self.value

class BaseConst(GenConst):

    def _get_index(self, meth):
        # check whether there is already an index associated to this const
        try:
            index = meth.genconsts[self]
        except KeyError:
            index = len(meth.genconsts)
            meth.genconsts[self] = index
        return index

    def _load_from_array(self, meth, index, clitype):
        meth.il.Emit(OpCodes.Ldarg_0)
        meth.il.Emit(OpCodes.Ldc_I4, index)
        meth.il.Emit(OpCodes.Ldelem_Ref)
        meth.il.Emit(OpCodes.Castclass, clitype)

    def getobj(self):
        raise NotImplementedError

class ObjectConst(BaseConst):

    def __init__(self, ooclass, obj):
        self.ooclass = ooclass
        self.obj = obj

    def getCliType(self):
        return class2type(self.ooclass)

    def getobj(self):
        return dotnet.cast_to_native_object(self.obj)

    def load(self, meth):
        index = self._get_index(meth)
        clitype = self.getCliType()
        self._load_from_array(meth, index, clitype)

    @specialize.arg(1)
    def revealconst(self, T):
        if isinstance(T, ootype.OOType):
            return ootype.cast_from_object(T, self.obj)
        else:
            h = ootype.ooidentityhash(self.obj)
            return lltype.cast_primitive(T, h)


OBJECT = System.Object._INSTANCE
class FunctionConst(BaseConst):

    def __init__(self, delegatetype):
        self.holder = DelegateHolder()
        self.delegatetype = delegatetype

    def getobj(self):
        return dotnet.cliupcast(self.holder, System.Object)

    def load(self, meth):
        holdertype = box(self.holder).GetType()
        funcfield = holdertype.GetField('func')
        delegatetype = self.delegatetype
        index = self._get_index(meth)
        self._load_from_array(meth, index, holdertype)
        meth.il.Emit(OpCodes.Ldfld, funcfield)
        meth.il.Emit(OpCodes.Castclass, delegatetype)

    @specialize.arg(1)
    def revealconst(self, T):
        assert isinstance(T, ootype.OOType)
        if isinstance(T, ootype.StaticMethod):
            return unbox(self.holder.GetFunc(), T)
        else:
            assert T is ootype.Object
            return ootype.cast_to_object(self.holder.GetFunc())

class NativeObjectConst(BaseConst):
    "GenConst for .NET objects"

    def __init__(self, obj):
        "obj must casted to System.Object with dotnet.cliupcast"
        self.obj = obj

    def getCliType(self):
        return self.obj.GetType()

    def getobj(self):
        return self.obj

    def load(self, meth):
        index = self._get_index(meth)
        self._load_from_array(meth, index, self.obj.GetType())


class Label(GenLabel):
    def __init__(self, meth, block_id, inputargs_gv):
        self.meth = meth
        self.block_id = block_id
        self.il_label = meth.il.DefineLabel()
        self.il_trampoline_label = meth.il.DefineLabel()
        self.inputargs_gv = inputargs_gv

    def emit_trampoline(self, meth):
        il = meth.il
        args_manager = meth.graphinfo.args_manager
        il.MarkLabel(self.il_trampoline_label)
        args_manager.copy_from_inputargs(meth, self.inputargs_gv)
        il.Emit(OpCodes.Br, self.il_label)

class RCliGenOp(AbstractRGenOp):

    def __init__(self):
        self.meth = None
        self.il = None
        self.constcount = 0

    @specialize.genconst(1)
    def genconst(self, llvalue):
        T = ootype.typeOf(llvalue)
        if T is ootype.Signed:
            return IntConst(llvalue, cInt32)
        elif T is ootype.Bool:
            return IntConst(int(llvalue), cBoolean)
        elif T is ootype.Char:
            return IntConst(ord(llvalue), cChar)
        elif T is ootype.Float:
            return FloatConst(llvalue)
        elif isinstance(T, ootype.OOType):
            ooclass = ootype.runtimeClass(T)
            obj = ootype.cast_to_object(llvalue)
            return ObjectConst(ooclass, obj)
        else:
            assert False, "XXX not implemented"

    @staticmethod
    def genzeroconst(kind):
        if kind is cInt32:
            return IntConst(0, cInt32)
        else:
            return zero_const # ???

    @staticmethod
    @specialize.memo()
    def sigToken(FUNCTYPE):
        """Return a token describing the signature of FUNCTYPE."""
        args = [RCliGenOp.kindToken(T) for T in FUNCTYPE.ARGS]
        res = RCliGenOp.kindToken(FUNCTYPE.RESULT)
        funcclass = classof(FUNCTYPE)
        return SigToken(args, res, funcclass)

    @staticmethod
    def erasedType(T):
        if isinstance(T, lltype.Primitive):
            return lltype.Signed
        elif isinstance(T, ootype.OOType):
            return ootype.Object
        else:
            assert 0, "XXX not implemented"

    @staticmethod
    @specialize.memo()
    def methToken(TYPE, methname):
        if TYPE is ootype.String:
            return StaticMethodToken(cpypyString, methname)
        elif isinstance(TYPE, ootype.Array):
            itemclass = RCliGenOp.kindToken(TYPE.ITEM)
            return ArrayMethodToken(methname, itemclass)
        else:
            ooclass = ootype.runtimeClass(TYPE)
            return VirtualMethToken(ooclass, methname)

    @staticmethod
    @specialize.memo()
    def kindToken(T):
        if T is ootype.Void:
            return cVoid
        elif T is ootype.Signed:
            return cInt32
        elif T is ootype.Bool:
            return cBoolean
        elif T is ootype.Float:
            return cDouble
        elif T is ootype.String:
            return cString
        elif T is ootype.Char:
            return cChar
        elif isinstance(T, ootype.OOType):
            return ootype.runtimeClass(T)
        else:
            assert False

    @staticmethod
    @specialize.memo()
    def fieldToken(T, name):
        ooclass = ootype.runtimeClass(T)
        return FieldToken(ooclass, name)

    @staticmethod
    @specialize.memo()
    def allocToken(T):
        return AllocToken(ootype.runtimeClass(T))

    def check_no_open_mc(self):
        pass

    def newgraph(self, sigtoken, name):
        arglist = [class2type(cls) for cls in sigtoken.args]
        restype = class2type(sigtoken.res)
        delegatetype = class2type(sigtoken.funcclass)
        graph = MainMethod(self, name, restype, arglist,
                               delegatetype)
        builder = graph.branches[0]
        return builder, graph.gv_entrypoint, graph.inputargs_gv[:]

    def replay(self, label):
        return ReplayBuilder(self), [dummy_var] * len(label.inputargs_gv)


"""
Glossary:

  - Graph: a RPython graph
  
  - Method: a .NET method
  
  - in case of flexswitches, a graph is composed by many methods

  - each method is a collections of blocks

  - MainMethod: the method containing the first block of the graph, and all
    the blocks reachable without passing throgh a flexswitch

  - FlexCaseMethod: a method containing the blocks for a specific case of a
    flexswitch

  - method_id: unique 16 bit number that identifies a method (either MainMethod or
    FlexCaseMethod) inside a graph. MainMethod.method_id == 0

  - block_num: unique 16 bit number that identifies a block inside a method

  - block_id: unique 32 bit number that identifies a block inside a graph; it
    is computed as (method_id << 16 | block_num)
"""

class GraphInfo:
    def __init__(self):        
        self.args_manager = ArgsManager()
        self.methods = []
        self.method_id_map = MethodIdMap()
        obj = dotnet.cliupcast(self.method_id_map, System.Object)
        self.gv_method_id_map = NativeObjectConst(obj)

    def register_method(self, meth):
        meth.method_id = len(self.methods)
        self.methods.append(meth)

    def register_case(self, method_id, case):
        self.method_id_map.add_case(method_id, case)
            

class MethodGenerator:

    method_id = -1 # must be overridden
    
    def __init__(self, rgenop, name, restype, arglist,
                 delegatetype, graphinfo):
        self.rgenop = rgenop
        self.name = name
        args = self._get_args_array(arglist)
        self.meth_wrapper = get_method_wrapper(name, restype, args)
        self.il = self.meth_wrapper.get_il_generator()
        self.inputargs_gv = []
        # we start from 1 because the 1st arg is an Object[] containing the genconsts
        for i in range(1, len(args)):
            self.inputargs_gv.append(GenArgVar(i, args[i]))
        self.delegatetype = delegatetype
        self.graphinfo = graphinfo
        graphinfo.register_method(self)
        self.gv_entrypoint = FunctionConst(delegatetype)
        self.gv_inputargs = None
        self.genconsts = {}
        self.branches = []
        self.newbranch()
        self.blocks = []   # block_num -> label
        if restype is None:
            self.gv_retvar = None
            self.retlabel = self.newblock([])
        else:
            self.gv_retvar = self.newlocalvar(restype)
            self.retlabel = self.newblock([self.gv_retvar])


    def _get_args_array(self, arglist):
        array = new_array(System.Type, len(arglist)+1)
        array[0] = System.Type.GetType("System.Object[]")
        for i in range(len(arglist)):
            array[i+1] = arglist[i]
        return array

    def newbranch(self):
        branch = BranchBuilder(self, self.il.DefineLabel())
        self.branches.append(branch)
        return branch

    def newblock(self, args_gv):
        block_num = len(self.blocks)
        assert block_num < 2**16
        assert self.method_id >= 0
        block_id = r_uint(self.method_id) << 16 | block_num
        lbl = Label(self, block_id, args_gv)
        self.blocks.append(lbl)
        return lbl

    def newlocalvar(self, clitype):
        return GenLocalVar(self, self.il.DeclareLocal(clitype))

    def map_genvar(self, gv_var):
        return gv_var

    def get_op_Return(self, gv_returnvar):
        raise NotImplementedError

    def branch_closed(self):
        # XXX: it's not needed to iterate over all branches
        allclosed = True
        for branchbuilder in self.branches:
            if branchbuilder.is_open:
                allclosed = False
                break
        if allclosed:
            self.emit_code()

    def emit_code(self):
        # emit initialization code
        self.emit_preamble()
        
        # render all the pending branches
        for branchbuilder in self.branches:
            branchbuilder.replayops()

        # emit dispatch_block, if there are flexswitches
        self.emit_before_returnblock()

        # emit the return block at last, else the verifier complains
        self.il.MarkLabel(self.retlabel.il_label)
        if self.gv_retvar:
            self.gv_retvar.load(self)

        self.il.Emit(OpCodes.Ret)

        # initialize the array of genconsts
        consts = new_array(System.Object, len(self.genconsts))
        for gv_const, i in self.genconsts.iteritems():
            consts[i] = gv_const.getobj()
        # build the delegate
        myfunc = self.meth_wrapper.create_delegate(self.delegatetype, consts)
        self.gv_entrypoint.holder.SetFunc(myfunc)

    def emit_preamble(self):
        pass

    def emit_before_returnblock(self):
        pass

    def setup_dispatch_block(self):
        self.il_dispatch_block_label = self.il.DefineLabel()
        self.jumpto_var = self.il.DeclareLocal(typeof(System.UInt32))

    def emit_dispatch_block(self):
        # make sure we don't enter dispatch_block by mistake
        il = self.il
        il.Emit(OpCodes.Br, self.retlabel.il_label)
        il.MarkLabel(self.il_dispatch_block_label)

        blocks = self.blocks
        il_labels = new_array(System.Reflection.Emit.Label, len(blocks))
        for block_num in range(len(blocks)):
            label = blocks[block_num]
            il_labels[block_num] = label.il_trampoline_label
        
        # XXX: do the right thing if no block was found
        # (depends if we are in the MainMethod or in a FlexCaseMethod)

        # if (((jumpto & 0xFFFF0000) >> 16) != method_id)
        #    goto jump_to_unknown
        il_jump_to_unknown_label = il.DefineLabel()
        il.Emit(OpCodes.Ldloc, self.jumpto_var)
        il.Emit(OpCodes.Ldc_I4, intmask(0xFFF0000))
        il.Emit(OpCodes.And)
        il.Emit(OpCodes.Ldc_I4, 16)
        il.Emit(OpCodes.Shr_Un)
        il.Emit(OpCodes.Ldc_I4, self.method_id)
        il.Emit(OpCodes.Bne_Un, il_jump_to_unknown_label)

        # switch(jumpto && 0x0000FFFF)
        il.Emit(OpCodes.Ldloc, self.jumpto_var)
        il.Emit(OpCodes.Ldc_I4, 0x0000FFFF)
        il.Emit(OpCodes.And)
        il.Emit(OpCodes.Switch, il_labels)
        # default: Utils.throwInvalidBlockId(jumpto)
        clitype = class2type(cUtils)
        meth = clitype.GetMethod("throwInvalidBlockId")
        il.Emit(OpCodes.Ldloc, self.jumpto_var)
        il.Emit(OpCodes.Call, meth)

        # emit all the trampolines to the blocks
        for label in blocks:
            label.emit_trampoline(self)

        self.emit_jump_to_unknown_block(il_jump_to_unknown_label)


class MainMethod(MethodGenerator):

    def __init__(self, rgenop, name, restype, args, delegatetype):
        graphinfo = GraphInfo()
        MethodGenerator.__init__(self, rgenop, name, restype, args, delegatetype, graphinfo)
        graphinfo.graph_retlabel = self.retlabel
        self.has_flexswitches = False

    def setup_flexswitches(self):
        if self.has_flexswitches:
            return
        self.has_flexswitches = True
        self.setup_dispatch_block()

    def get_op_Return(self, gv_returnvar):
        return ops.Return(self, gv_returnvar)

    def emit_preamble(self):
        if not self.has_flexswitches:
            return
        # InputArgs inputargs = new InputArgs()
        args_manager = self.graphinfo.args_manager
        self.gv_inputargs = self.newlocalvar(args_manager.getCliType())
        clitype = self.gv_inputargs.getCliType()
        ctor = clitype.GetConstructor(new_array(System.Type, 0))
        self.il.Emit(OpCodes.Newobj, ctor)
        self.gv_inputargs.store(self)

    def emit_before_returnblock(self):
        if not self.has_flexswitches:
            return
        self.emit_dispatch_block()

    def emit_jump_to_unknown_block(self, il_label):
        il = self.il
        gv_method_id_map = self.graphinfo.gv_method_id_map
        clitype = gv_method_id_map.getCliType()
        meth_jumpto = clitype.GetMethod('jumpto')

        # jumpto = method_id_map.jumpto(jumpto, args)
        il.MarkLabel(il_label)
        gv_method_id_map.load(self)
        il.Emit(OpCodes.Ldloc, self.jumpto_var)
        self.gv_inputargs.load(self)
        il.Emit(OpCodes.Callvirt, meth_jumpto)
        il.Emit(OpCodes.Stloc, self.jumpto_var)
        il.Emit(OpCodes.Br, self.il_dispatch_block_label)


class FlexCaseMethod(MethodGenerator):
    flexswitch = None
    gv_value = None
    linkargs_gv = None
    linkargs_gv_map = None

    def setup_flexswitches(self):
        pass
    
    def set_parent_flexswitch(self, flexswitch, gv_value):
        self.parent_flexswitch = flexswitch
        self.gv_value = gv_value
        self.setup_dispatch_block()

    def set_linkargs_gv(self, linkargs_gv):
        self.linkargs_gv = linkargs_gv
        self.linkargs_gv_map = {}
        for gv_arg in linkargs_gv:
            gv_local = self.newlocalvar(gv_arg.getCliType())
            self.linkargs_gv_map[gv_arg] = gv_local

    def map_genvar(self, gv_var):
        return self.linkargs_gv_map.get(gv_var, gv_var)

    def get_op_Return(self, gv_returnvar):
        target = self.graphinfo.graph_retlabel
        return ops.NonLocalJump(self, target, [gv_returnvar])

    def emit_code(self):
        MethodGenerator.emit_code(self)
        func = self.gv_entrypoint.holder.GetFunc()
        func2 = clidowncast(func, FlexSwitchCase)
        self.parent_flexswitch.set_link(self.gv_value, func2)
        self.graphinfo.register_case(self.method_id, func2)

    def emit_preamble(self):
        # the signature of the method is
        # int case_0(int jumpto, InputArgs args)
        self.gv_inputargs = self.inputargs_gv[1]        
        args_manager = self.graphinfo.args_manager

        # 0 is a special value that means "first block of the function",
        # i.e. don't go through the dispatch block. 0 can never passed as
        # blockid, because it's used as the returnblock of the MainMethod, and
        # it's handled by its dispatch block

        # if (jumpto != 0) goto dispatch_block
        self.inputargs_gv[0].load(self)
        self.il.Emit(OpCodes.Ldc_I4_0)
        self.il.Emit(OpCodes.Bne_Un, self.il_dispatch_block_label)

        linkargs_out_gv = []
        for gv_linkarg in self.linkargs_gv:
            gv_var = self.linkargs_gv_map[gv_linkarg]
            linkargs_out_gv.append(gv_var)
        args_manager.copy_from_inputargs(self, linkargs_out_gv)


    def emit_before_returnblock(self):
        self.emit_dispatch_block()

    def emit_jump_to_unknown_block(self, il_label):
        # delegate to parent
        il = self.il
        il.MarkLabel(il_label)
        il.Emit(OpCodes.Ldloc, self.jumpto_var)
        il.Emit(OpCodes.Ret)


class BranchBuilder(GenBuilder):

    def __init__(self, meth, il_label):
        self.meth = meth
        self.rgenop = meth.rgenop
        self.il_label = il_label
        self.operations = []
        self.is_open = True
        self.genconsts = meth.genconsts

    def start_writing(self):
        self.is_open = True

    def close(self):
        assert self.is_open
        self.is_open = False
        self.meth.branch_closed()

    def finish_and_return(self, sigtoken, gv_returnvar):
        op = self.meth.get_op_Return(gv_returnvar)
        self.appendop(op)
        self.close()

    def finish_and_goto(self, outputargs_gv, label):
        inputargs_gv = label.inputargs_gv
        assert len(inputargs_gv) == len(outputargs_gv)
        if self.meth is label.meth:
            # jump inside the same method, easy
            op = ops.FollowLink(self.meth, outputargs_gv,
                                inputargs_gv, label.il_label)
        else:
            # jump from a flexswitch to the parent method
            op = ops.NonLocalJump(self.meth, label,
                                  outputargs_gv)
        self.appendop(op)
        self.close()


    @specialize.arg(1)
    def genop1(self, opname, gv_arg):
        opcls = ops.getopclass1(opname)
        op = opcls(self.meth, gv_arg)
        self.appendop(op)
        gv_res = op.gv_res()
        return gv_res
    
    @specialize.arg(1)
    def genop2(self, opname, gv_arg1, gv_arg2):
        opcls = ops.getopclass2(opname)
        op = opcls(self.meth, gv_arg1, gv_arg2)
        self.appendop(op)
        gv_res = op.gv_res()
        return gv_res

    def genop_call(self, sigtoken, gv_fnptr, args_gv):
        op = ops.Call(self.meth, sigtoken, gv_fnptr, args_gv)
        self.appendop(op)
        return op.gv_res()

    def genop_same_as(self, gv_x):
        op = ops.SameAs(self.meth, gv_x)
        self.appendop(op)
        return op.gv_res()

    def genop_oogetfield(self, fieldtoken, gv_obj):
        op = ops.GetField(self.meth, gv_obj, fieldtoken)
        self.appendop(op)
        return op.gv_res()

    def genop_oosetfield(self, fieldtoken, gv_obj, gv_value):
        op = ops.SetField(self.meth, gv_obj, gv_value, fieldtoken)
        self.appendop(op)

    def genop_oosend(self, methtoken, gv_self, args_gv):
        op = ops.OOSend(self.meth, gv_self, args_gv, methtoken)
        self.appendop(op)
        return op.gv_res()

    def genop_oononnull(self, gv_obj):
        OP = ops.getopclass1('oononnull')
        op = OP(self.meth, gv_obj)
        self.appendop(op)
        return op.gv_res()

    def genop_ooisnull(self, gv_obj):
        OP = ops.getopclass1('ooisnull')
        op = OP(self.meth, gv_obj)
        self.appendop(op)
        return op.gv_res()

    def genop_new(self, alloctoken):
        op = ops.New(self.meth, alloctoken)
        self.appendop(op)
        return op.gv_res()

    def genop_oonewarray(self, alloctoken, gv_length):
        op = ops.OONewArray(self.meth, alloctoken, gv_length)
        self.appendop(op)
        return op.gv_res()

    def genop_instanceof(self, gv_obj, alloctoken):
        op = ops.InstanceOf(self.meth, gv_obj, alloctoken)
        self.appendop(op)
        return op.gv_res()

    def enter_next_block(self, args_gv):
        seen = {}
        for i in range(len(args_gv)):
            gv = args_gv[i]
            if isinstance(gv, GenConst) or gv in seen:
                op = ops.SameAs(self.meth, gv)
                self.appendop(op)
                args_gv[i] = op.gv_res()
            else:
                seen[gv] = None
        label = self.meth.newblock(args_gv)
        self.appendop(ops.MarkLabel(self.meth, label.il_label))
        return label

    def _jump_if(self, gv_condition, opcode):
        branch = self.meth.newbranch()
        op = ops.Branch(self.meth, gv_condition, opcode, branch.il_label)
        self.appendop(op)
        return branch

    def jump_if_false(self, gv_condition, args_for_jump_gv):
        return self._jump_if(gv_condition, OpCodes.Brfalse)

    def jump_if_true(self, gv_condition, args_for_jump_gv):
        return self._jump_if(gv_condition, OpCodes.Brtrue)

    def flexswitch(self, gv_exitswitch, args_gv):
        self.meth.setup_flexswitches()
        clitype = gv_exitswitch.getCliType()
        if clitype.get_IsPrimitive():
            flexswitch = IntFlexSwitch(self.meth, args_gv)
        else:
            flexswitch = ObjectFlexSwitch(self.meth, args_gv)
        gv_flexswitch = flexswitch.gv_flexswitch
        default_branch = self.meth.newbranch()
        label = default_branch.enter_next_block(args_gv)

        flexswitch.set_defaul_link(label)
        op = ops.DoFlexSwitch(self.meth, gv_flexswitch,
                              gv_exitswitch, args_gv)
        self.appendop(op)
        self.close()
        return flexswitch, default_branch

    def appendop(self, op):
        self.operations.append(op)

    def end(self):
         pass

    def replayops(self):
        assert not self.is_open
        il = self.meth.il
        il.MarkLabel(self.il_label)
        for op in self.operations:
            op.emit()

template = """
class %(classname)s(CodeGenSwitch):

    def __init__(self, graph, linkargs_gv):
        self.graph = graph
        self.linkargs_gv = linkargs_gv
        self.llflexswitch = LowLevelFlexSwitch()
        obj = dotnet.cliupcast(self.llflexswitch, System.Object)
        self.gv_flexswitch = NativeObjectConst(obj)

    def set_defaul_link(self, label):
        self.llflexswitch.set_default_blockid(label.block_id)

    def set_link(self, gv_value, func):
        value = revealconst(gv_value)
        self.llflexswitch.add_case(value, func)

    def add_case(self, gv_case):
        graph = self.graph
        name = graph.name + '_case'
        restype = typeof(System.UInt32)
        arglist = [typeof(System.UInt32), typeof(InputArgs)]
        delegatetype = class2type(cFlexSwitchCase)
        graphinfo = graph.graphinfo
        meth = FlexCaseMethod(graph.rgenop, name, restype,
                              arglist, delegatetype, graphinfo)
        meth.set_parent_flexswitch(self, gv_case)
        meth.set_linkargs_gv(self.linkargs_gv)
        return meth.branches[0]
"""

def revealconst_int(gv_value):
    return gv_value.revealconst(ootype.Signed)

def revealconst_obj(gv_value):
    obj = gv_value.revealconst(ootype.Object)
    return dotnet.cast_to_native_object(obj)

def build_flexswitch_class(classname, LowLevelFlexSwitch, revealconst):
    src = py.code.Source(template % locals())
    mydict = globals().copy()
    mydict['LowLevelFlexSwitch'] = LowLevelFlexSwitch
    mydict['revealconst'] = revealconst
    exec src.compile() in mydict
    globals()[classname] = mydict[classname]

build_flexswitch_class('IntFlexSwitch',
                       IntLowLevelFlexSwitch,
                       revealconst_int)

build_flexswitch_class('ObjectFlexSwitch',
                       ObjectLowLevelFlexSwitch,
                       revealconst_obj)


global_rgenop = RCliGenOp()
RCliGenOp.constPrebuiltGlobal = global_rgenop.genconst
zero_const = ObjectConst(cObject, ootype.NULL)
