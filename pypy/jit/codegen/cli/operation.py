import py
from pypy.rlib.objectmodel import specialize
from pypy.rpython.ootypesystem import ootype
from pypy.translator.cli.dotnet import CLR, typeof, new_array
from pypy.translator.cli import opcodes as cli_opcodes
System = CLR.System
OpCodes = System.Reflection.Emit.OpCodes

class Operation(object):
    _gv_res = None

    def restype(self):
        return self.gv_x.getCliType()

    def gv_res(self):
        if self._gv_res is None:
            restype = self.restype()
            if restype is not None:
                self._gv_res = self.meth.newlocalvar(restype)
        return self._gv_res

    def emit(self):
        raise NotImplementedError

    def pushAllArgs(self):
        raise NotImplementedError

    def storeResult(self):
        self.gv_res().store(self.meth)


class UnaryOp(Operation):
    def __init__(self, meth, gv_x):
        self.meth = meth
        self.gv_x = gv_x

    def pushAllArgs(self):
        self.gv_x.load(self.meth)

    def emit(self):
        self.pushAllArgs()
        self.meth.il.Emit(self.getOpCode())
        self.storeResult()

    def getOpCode(self):
        raise NotImplementedError

class BinaryOp(Operation):
    def __init__(self, meth, gv_x, gv_y):
        self.meth = meth
        self.gv_x = gv_x
        self.gv_y = gv_y

    def pushAllArgs(self):
        self.gv_x.load(self.meth)
        self.gv_y.load(self.meth)

    def emit(self):
        self.pushAllArgs()
        self.meth.il.Emit(self.getOpCode())
        self.storeResult()

    def getOpCode(self):
        raise NotImplementedError


class SameAs(UnaryOp):
    def emit(self):
        gv_res = self.gv_res()
        self.gv_x.load(self.meth)
        self.gv_res().store(self.meth)

class MarkLabel(Operation):

    def __init__(self, meth, il_label):
        self.meth = meth
        self.il_label = il_label

    def restype(self):
        return None

    def emit(self):
        self.meth.il.MarkLabel(self.il_label)
        
class FollowLink(Operation):
    
    def __init__(self, meth, outputargs_gv, inputargs_gv, il_label):
        self.meth = meth
        self.outputargs_gv = outputargs_gv
        self.inputargs_gv = inputargs_gv
        self.il_label = il_label

    def restype(self):
        return None

    def emit(self):
        for i in range(len(self.outputargs_gv)):
            self.outputargs_gv[i].load(self.meth)
            self.inputargs_gv[i].store(self.meth)
        self.meth.il.Emit(OpCodes.Br, self.il_label)

class Branch(Operation):
    
    def __init__(self, meth, gv_cond, opcode, il_label):
        self.meth = meth
        self.gv_cond = gv_cond
        self.opcode = opcode
        self.il_label = il_label

    def restype(self):
        return None

    def emit(self):
        if self.gv_cond is not None:
            self.gv_cond.load(self.meth)
        self.meth.il.Emit(self.opcode, self.il_label)

class Return(Operation):

    def __init__(self, meth, gv_x):
        self.meth = meth
        self.gv_x = gv_x

    def restype(self):
        return None

    def emit(self):
        gv_retvar = self.meth.gv_retvar
        retlabel = self.meth.retlabel
        if self.gv_x is not None:
            self.gv_x.load(self.meth)
            gv_retvar.store(self.meth)
        self.meth.il.Emit(OpCodes.Br, retlabel.il_label)

class ReturnFromFlexSwitch(Operation):

    def __init__(self, meth, gv_x):
        self.meth = meth
        self.gv_x = gv_x

    def restype(self):
        return None

    def emit(self):
        il = self.meth.il
        graphinfo = self.meth.graphinfo
        graphinfo.args_manager.copy_to_inputargs(self.meth, [self.gv_x])
        blockid = graphinfo.graph_retlabel.blockid
        il.Emit(OpCodes.Ldc_I4, blockid)
        il.Emit(OpCodes.Ret)

class Call(Operation):

    def __init__(self, meth, sigtoken, gv_fnptr, args_gv):
        from pypy.jit.codegen.cli.rgenop import class2type
        self.meth = meth
        self.sigtoken = sigtoken
        self.gv_fnptr = gv_fnptr
        self.args_gv = args_gv
        self._restype = class2type(sigtoken.res)

    def restype(self):
        return self._restype

    def emit(self):
        from pypy.jit.codegen.cli.rgenop import class2type
        delegate_type = class2type(self.sigtoken.funcclass)
        meth_invoke = delegate_type.GetMethod('Invoke')
        self.gv_fnptr.load(self.meth)
        self.meth.il.Emit(OpCodes.Castclass, delegate_type)
        for gv_arg in self.args_gv:
            gv_arg.load(self.meth)
        self.meth.il.EmitCall(OpCodes.Callvirt, meth_invoke, None)
        if self.restype():
            self.storeResult()


class GetField(Operation):

    def __init__(self, meth, gv_obj, fieldtoken):
        self.meth = meth
        self.gv_obj = gv_obj
        self.fieldinfo = fieldtoken.getFieldInfo()

    def restype(self):
        return self.fieldinfo.get_FieldType()

    def emit(self):
        self.gv_obj.load(self.meth)
        self.meth.il.Emit(OpCodes.Ldfld, self.fieldinfo)
        self.storeResult()


class SetField(Operation):

    def __init__(self, meth, gv_obj, gv_value, fieldtoken):
        self.meth = meth
        self.gv_obj = gv_obj
        self.gv_value = gv_value
        self.fieldinfo = fieldtoken.getFieldInfo()

    def restype(self):
        return None

    def emit(self):
        self.gv_obj.load(self.meth)
        self.gv_value.load(self.meth)
        self.meth.il.Emit(OpCodes.Stfld, self.fieldinfo)

class New(Operation):

    def __init__(self, meth, alloctoken):
        self.meth = meth
        self.clitype = alloctoken.getCliType()

    def restype(self):
        return self.clitype

    def emit(self):
        ctor = self.clitype.GetConstructor(new_array(System.Type, 0))
        self.meth.il.Emit(OpCodes.Newobj, ctor)
        self.storeResult()

class OOSend(Operation):

    def __init__(self, meth, gv_self, args_gv, methtoken):
        self.meth = meth
        self.gv_self = gv_self
        self.args_gv = args_gv
        self.methtoken = methtoken

    def restype(self):
        clitype = self.methtoken.getReturnType()
        if clitype is typeof(System.Void):
            return None
        return clitype

    def emit(self):
        self.gv_self.load(self.meth)
        for gv_arg in self.args_gv:
            gv_arg.load(self.meth)
        self.methtoken.emit_call(self.meth.il)
        if self.restype() is not None:
            self.storeResult()

def mark(il, s):
    il.Emit(OpCodes.Ldstr, s)
    il.Emit(OpCodes.Pop)

class DoFlexSwitch(Operation):

    def __init__(self, meth, gv_flexswitch, gv_exitswitch, args_gv):
        self.meth = meth
        self.gv_flexswitch = gv_flexswitch
        self.gv_exitswitch = gv_exitswitch
        self.args_gv = args_gv # XXX: remove duplicates

    def restype(self):
        return None

    def emit(self):
        graph = self.meth
        il = graph.il
        # get MethodInfo for LowLevelFlexSwitch.execute
        clitype = self.gv_flexswitch.llflexswitch.GetType()
        meth_execute = clitype.GetMethod('execute')

        # setup the correct inputargs
        args_manager = graph.graphinfo.args_manager
        args_manager.copy_to_inputargs(graph, self.args_gv)

        # jumpto = flexswitch.execute(exitswitch, inputargs);
        # goto dispatch_jump;
        self.gv_flexswitch.load(graph)
        self.gv_exitswitch.load(graph)
        graph.gv_inputargs.load(graph)
        il.Emit(OpCodes.Callvirt, meth_execute)
        il.Emit(OpCodes.Stloc, graph.jumpto_var)
        il.Emit(OpCodes.Br, graph.il_dispatch_jump_label)


class WriteLine(Operation):

    def __init__(self, meth, message):
        self.meth = meth
        self.message = message

    def restype(self):
        return None

    def emit(self):
        self.meth.il.EmitWriteLine(self.message)

def opcode2attrname(opcode):
    if opcode == 'ldc.r8 0':
        return 'Ldc_R8, 0' # XXX this is a hack
    if opcode == 'ldc.i8 0':
        return 'Ldc_I8, 0' # XXX this is a hack
    parts = map(str.capitalize, opcode.split('.'))
    return '_'.join(parts)

def is_comparison(opname):
    if opname in ('ooisnull', 'oononnull'):
        return True
    suffixes = '_lt _le _eq _ne _gt _ge'.split()
    for suffix in suffixes:
        if opname.endswith(suffix):
            return True
    return False

def restype_bool(self):     return typeof(System.Boolean)
def restype_int(self):      return typeof(System.Int32)
def restype_uint(self):     return typeof(System.Int32)
def restype_float(self):    return typeof(System.Double)
def restype_char(self):     return typeof(System.Char)
def restype_unichar(self):  return typeof(System.Char)
def restype_longlong(self): return typeof(System.Int64)

def fillops(ops, baseclass):
    out = {}
    for opname, value in ops.iteritems():
        if isinstance(value, str):
            attrname = opcode2attrname(value)
            source = py.code.Source("""
            class %(opname)s (%(baseclass)s):
                def getOpCode(self):
                    return OpCodes.%(attrname)s
            """ % locals())
            code = source.compile()
            exec code in globals(), out
        elif value is cli_opcodes.DoNothing:
            # create a new subclass of SameAs; we can't use SameAs directly
            # because its restype could be patched later
            out[opname] = type(opname, (SameAs,), {})
        else:
            renderCustomOp(opname, baseclass, value, out)

        # fix the restype for comparison ops and casts
        if is_comparison(opname):
            out[opname].restype = restype_bool
        elif opname != 'cast_primitive' and opname.startswith('cast_'):
            _, _, _, to = opname.split('_')
            funcname = 'restype_%s' % to
            out[opname].restype = globals()[funcname]

    return out

def renderCustomOp(opname, baseclass, steps, out):
    assert steps
    body = []
    for step in steps:
        if step is cli_opcodes.PushAllArgs:
            body.append('self.pushAllArgs()')
        elif step is cli_opcodes.StoreResult:
            body.append('self.storeResult()')
        elif isinstance(step, str):
            if 'call' in step:
                return # XXX, fix this
            attrname = opcode2attrname(step)
            body.append('self.meth.il.Emit(OpCodes.%s)' % attrname)
        elif isinstance(step, cli_opcodes.MapException):
            return # XXX, TODO
        else:
            return # ignore it for now

    if cli_opcodes.StoreResult not in steps:
        body.append('self.storeResult()')

    emit = py.code.Source('\n'.join(body))
    emit = emit.putaround('def emit(self):')
    source = emit.putaround('class %(opname)s (%(baseclass)s):' % locals())
    code = source.compile()
    exec code in globals(), out


UNARYOPS = fillops(cli_opcodes.unary_ops, "UnaryOp")
BINARYOPS = fillops(cli_opcodes.binary_ops, "BinaryOp")

class XXX(BinaryOp):
    pass

BINARYOPS['oostring'] = XXX
BINARYOPS['subclassof'] = XXX

@specialize.memo()
def getopclass1(opname):
    try:
        return UNARYOPS[opname]
    except KeyError:
        raise MissingBackendOperation(opname)

@specialize.memo()
def getopclass2(opname):
    try:
        return BINARYOPS[opname]
    except KeyError:
        raise MissingBackendOperation(opname)

class MissingBackendOperation(Exception):
    pass
