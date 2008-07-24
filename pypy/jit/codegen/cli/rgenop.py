from pypy.tool.pairtype import extendabletype
from pypy.rlib.rarithmetic import intmask
from pypy.rpython.ootypesystem import ootype
from pypy.rpython.lltypesystem import lltype
from pypy.rlib.objectmodel import specialize
from pypy.jit.codegen.model import AbstractRGenOp, GenBuilder, GenLabel
from pypy.jit.codegen.model import GenVarOrConst, GenVar, GenConst
from pypy.jit.codegen.model import CodeGenSwitch
from pypy.jit.codegen.cli import operation as ops
from pypy.jit.codegen.cli.methodfactory import get_method_wrapper
from pypy.translator.cli.dotnet import CLR, typeof, new_array, init_array
from pypy.translator.cli.dotnet import box, unbox, clidowncast, classof
from pypy.translator.cli import dotnet
System = CLR.System
DelegateHolder = CLR.pypy.runtime.DelegateHolder
LowLevelFlexSwitch = CLR.pypy.runtime.LowLevelFlexSwitch
FlexSwitchCase = CLR.pypy.runtime.FlexSwitchCase
InputArgs = CLR.pypy.runtime.InputArgs
OpCodes = System.Reflection.Emit.OpCodes

cVoid = ootype.nullruntimeclass
cInt32 = classof(System.Int32)
cBoolean = classof(System.Boolean)
cDouble = classof(System.Double)
cObject = classof(System.Object)
cString = classof(System.String)
cChar = classof(System.Char)
cInputArgs = classof(InputArgs)
cUtils = classof(CLR.pypy.runtime.Utils)
cFlexSwitchCase = classof(FlexSwitchCase)

class SigToken:
    def __init__(self, args, res, funcclass):
        self.args = args
        self.res = res
        self.funcclass = funcclass

def class2type(cls):
    'Cast a PBC of type ootype.Class into a System.Type instance'
    if cls is cVoid:
        return None
    else:
        return clidowncast(box(cls), System.Type)

class __extend__(GenVarOrConst):
    __metaclass__ = extendabletype

    def getCliType(self):
        raise NotImplementedError
    
    def load(self, builder):
        raise NotImplementedError

    def store(self, builder):
        raise NotImplementedError

class GenArgVar(GenVar):
    def __init__(self, index, cliType):
        self.index = index
        self.cliType = cliType

    def getCliType(self):
        return self.cliType

    def load(self, meth):
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

    def store(self, meth):
        meth.il.Emit(OpCodes.Starg, self.index)

    def __repr__(self):
        return "GenArgVar(%d)" % self.index

class GenLocalVar(GenVar):
    def __init__(self, v):
        self.v = v

    def getCliType(self):
        return self.v.get_LocalType()

    def load(self, meth):
        meth.il.Emit(OpCodes.Ldloc, self.v)

    def store(self, meth):
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

    def __init__(self, obj):
        self.obj = obj

    def getCliType(self):
        if self.obj == ootype.NULL:
            return class2type(cObject)
        cliobj = dotnet.cast_to_native_object(self.obj)
        return cliobj.GetType()

    def getobj(self):
        return self.obj

    def load(self, meth):
        assert False, 'XXX'
##        import pdb;pdb.set_trace()
##        index = self._get_index(builder)
##        if self.obj is None:
##            t = typeof(System.Object)
##        else:
##            t = self.obj.GetType()
##        self._load_from_array(builder, index, t)

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

class FlexSwitchConst(BaseConst):

    def __init__(self, llflexswitch):
        self.llflexswitch = llflexswitch

    def getobj(self):
        return dotnet.cliupcast(self.llflexswitch, System.Object)

    def load(self, meth):
        index = self._get_index(meth)
        self._load_from_array(meth, index, self.llflexswitch.GetType())


class Label(GenLabel):
    def __init__(self, blockid, il, inputargs_gv):
        self.blockid = blockid
        self.il_label = il.DefineLabel()
        self.il_trampoline_label = il.DefineLabel()
        self.inputargs_gv = inputargs_gv

    def emit_trampoline(self, meth):
        from pypy.jit.codegen.cli.operation import InputArgsManager
        from pypy.jit.codegen.cli.operation import mark
        il = meth.il
        manager = InputArgsManager(meth, self.inputargs_gv)
        il.MarkLabel(self.il_trampoline_label)
        manager.copy_to_args()
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
            obj = ootype.cast_to_object(llvalue)
            return ObjectConst(obj)
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
        return methname #XXX

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
            return cObject # XXX?
        else:
            assert False

    @staticmethod
    @specialize.memo()
    def fieldToken(T, name):
        _, FIELD = T._lookup_field(name)
        return name #, RCliGenOp.kindToken(FIELD)

    @staticmethod
    @specialize.memo()
    def allocToken(T):
        return RCliGenOp.kindToken(T)

    def check_no_open_mc(self):
        pass

    def newgraph(self, sigtoken, name):
        arglist = [class2type(cls) for cls in sigtoken.args]
        restype = class2type(sigtoken.res)
        delegatetype = class2type(sigtoken.funcclass)
        graph = GraphGenerator(self, name, restype, arglist,
                               delegatetype)
        builder = graph.branches[0]
        return builder, graph.gv_entrypoint, graph.inputargs_gv[:]


class GraphInfo:
    def __init__(self):
        self.has_flexswitches = False
        self.blocks = [] # blockid -> (meth, label)
        self.flexswitch_meths = []
        self.main_retlabel = None

class MethodGenerator:
    
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

        self.gv_entrypoint = FunctionConst(delegatetype)
        self.gv_inputargs = None
        self.genconsts = {}
        self.branches = []
        self.newbranch()
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
        blocks = self.graphinfo.blocks
        blockid = len(blocks)
        result = Label(blockid, self.il, args_gv)
        blocks.append((self, result))
        return result

    def newlocalvar(self, clitype):
        return GenLocalVar(self.il.DeclareLocal(clitype))

    def map_genvar(self, gv_var):
        return gv_var

    def get_op_Return(self, gv_returnvar):
        raise NotImplementedError

    def emit_code(self):
        # emit initialization code
        self.emit_preamble()
        
        # render all the pending branches
        for branchbuilder in self.branches:
            branchbuilder.replayops()

        # emit dispatch_jump, if there are flexswitches
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


class GraphGenerator(MethodGenerator):
    def __init__(self, rgenop, name, restype, args, delegatetype):
        graphinfo = GraphInfo()
        MethodGenerator.__init__(self, rgenop, name, restype, args, delegatetype, graphinfo)
        graphinfo.graph_retlabel = self.retlabel

    def setup_flexswitches(self):
        if self.graphinfo.has_flexswitches:
            return
        self.graphinfo.has_flexswitches = True
        self.il_dispatch_jump_label = self.il.DefineLabel()
        self.jumpto_var = self.il.DeclareLocal(class2type(cInt32))

    def get_op_Return(self, gv_returnvar):
        return ops.Return(self, gv_returnvar)

    def emit_code(self):
        self.emit_flexswitches()
        MethodGenerator.emit_code(self)

    def emit_flexswitches(self):
        for meth in self.graphinfo.flexswitch_meths:
            meth.emit_code()

    def emit_preamble(self):
        if not self.graphinfo.has_flexswitches:
            return
        
        # InputArgs inputargs = new InputArgs()
        self.gv_inputargs = self.newlocalvar(class2type(cInputArgs))
        clitype = self.gv_inputargs.getCliType()
        ctor = clitype.GetConstructor(new_array(System.Type, 0))
        self.il.Emit(OpCodes.Newobj, ctor)
        self.gv_inputargs.store(self)

    def emit_before_returnblock(self):
        if not self.graphinfo.has_flexswitches:
            return
        # make sure we don't enter dispatch_jump by mistake
        self.il.Emit(OpCodes.Br, self.retlabel.il_label)
        self.il.MarkLabel(self.il_dispatch_jump_label)

        blocks = self.graphinfo.blocks
        il_labels = new_array(System.Reflection.Emit.Label, len(blocks))
        for blockid in range(len(blocks)):
            builder, label = blocks[blockid]
            if builder is not self:
                continue # XXX FIXME
            il_labels[blockid] = label.il_trampoline_label

        self.il.Emit(OpCodes.Ldloc, self.jumpto_var)
        self.il.Emit(OpCodes.Switch, il_labels)
        # XXX: handle blockids that are inside flexswitch cases
        # default: Utils.throwInvalidBlockId(jumpto)
        clitype = class2type(cUtils)
        meth = clitype.GetMethod("throwInvalidBlockId")
        self.il.Emit(OpCodes.Ldloc, self.jumpto_var)
        self.il.Emit(OpCodes.Call, meth)

        # emit all the trampolines to the blocks
        for builder, label in blocks:
            if builder is not self:
                continue #XXX?
            label.emit_trampoline(self)

class FlexSwitchCaseGenerator(MethodGenerator):
    flexswitch = None
    value = -1
    linkargs_gv = None
    linkargs_gv_map = None

    def set_parent_flexswitch(self, flexswitch, value):
        self.parent_flexswitch = flexswitch
        self.value = value

    def set_linkargs_gv(self, linkargs_gv):
        self.linkargs_gv = linkargs_gv
        self.linkargs_gv_map = {}
        for gv_arg in linkargs_gv:
            gv_local = self.newlocalvar(gv_arg.getCliType())
            self.linkargs_gv_map[gv_arg] = gv_local

    def map_genvar(self, gv_var):
        return self.linkargs_gv_map.get(gv_var, gv_var)

    def get_op_Return(self, gv_returnvar):
        return ops.ReturnFromFlexSwitch(self, gv_returnvar)

    def emit_code(self):
        MethodGenerator.emit_code(self)
        func = self.gv_entrypoint.holder.GetFunc()
        func2 = clidowncast(func, FlexSwitchCase)
        self.parent_flexswitch.llflexswitch.add_case(self.value, func2)

    def emit_preamble(self):
        from pypy.jit.codegen.cli.operation import InputArgsManager

        # InputArgs inputargs = (InputArgs)obj // obj is the 2nd arg
        clitype = class2type(cInputArgs)
        self.gv_inputargs = self.newlocalvar(clitype)
        self.inputargs_gv[1].load(self)
        self.il.Emit(OpCodes.Castclass, clitype)
        self.gv_inputargs.store(self)

        linkargs_out_gv = []
        for gv_linkarg in self.linkargs_gv:
            gv_var = self.linkargs_gv_map[gv_linkarg]
            linkargs_out_gv.append(gv_var)
        manager = InputArgsManager(self, linkargs_out_gv)
        manager.copy_to_args()


class BranchBuilder(GenBuilder):

    def __init__(self, meth, il_label):
        self.meth = meth
        self.rgenop = meth.rgenop
        self.il_label = il_label
        self.operations = []
        self.is_open = False
        self.genconsts = meth.genconsts

    def start_writing(self):
        self.is_open = True

    def finish_and_return(self, sigtoken, gv_returnvar):
        op = self.meth.get_op_Return(gv_returnvar)
        self.appendop(op)
        self.is_open = False

    def finish_and_goto(self, outputargs_gv, label):
        inputargs_gv = label.inputargs_gv
        assert len(inputargs_gv) == len(outputargs_gv)
        op = ops.FollowLink(self.meth, outputargs_gv,
                            inputargs_gv, label.il_label)
        self.appendop(op)
        self.is_open = False

    @specialize.arg(1)
    def genop1(self, opname, gv_arg):
        opcls = ops.getopclass1(opname)
        op = opcls(self.meth, gv_arg)
        self.appendop(op)
        gv_res = op.gv_res()
        return gv_res
    
    @specialize.arg(1)
    def genop2(self, opname, gv_arg1, gv_arg2):
        # XXX: also other ops
        gv_arg1 = self.meth.map_genvar(gv_arg1)
        gv_arg2 = self.meth.map_genvar(gv_arg2)
        
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
        # XXX: this code is valid only for GraphGenerator
        self.meth.setup_flexswitches()
        flexswitch = IntFlexSwitch(self.meth, args_gv)
        gv_flexswitch = flexswitch.gv_flexswitch
        default_branch = self.meth.newbranch()
        label = default_branch.enter_next_block(args_gv)
        flexswitch.llflexswitch.set_default_blockid(label.blockid)
        op = ops.DoFlexSwitch(self.meth, gv_flexswitch,
                              gv_exitswitch, args_gv)
        self.appendop(op)
        self.is_open = False
        return flexswitch, default_branch

    def appendop(self, op):
        self.operations.append(op)

    def end(self):
        self.meth.emit_code()

    def replayops(self):
        assert not self.is_open
        il = self.meth.il
        il.MarkLabel(self.il_label)
        for op in self.operations:
            op.emit()


class IntFlexSwitch(CodeGenSwitch):

    def __init__(self, graph, linkargs_gv):
        self.graph = graph
        self.linkargs_gv = linkargs_gv
        self.llflexswitch = LowLevelFlexSwitch()
        self.gv_flexswitch = FlexSwitchConst(self.llflexswitch)

    def add_case(self, gv_case):
        graph = self.graph
        name = graph.name + '_case'
        restype = class2type(cInt32)
        arglist = [class2type(cInt32), class2type(cObject)]
        delegatetype = class2type(cFlexSwitchCase)
        graphinfo = graph.graphinfo
        meth = FlexSwitchCaseGenerator(graph.rgenop, name, restype,
                                       arglist, delegatetype, graphinfo)
        graphinfo.flexswitch_meths.append(meth)
        value = gv_case.revealconst(ootype.Signed)
        meth.set_parent_flexswitch(self, value)
        meth.set_linkargs_gv(self.linkargs_gv)
        return meth.branches[0]


global_rgenop = RCliGenOp()
RCliGenOp.constPrebuiltGlobal = global_rgenop.genconst
zero_const = ObjectConst(ootype.NULL)
