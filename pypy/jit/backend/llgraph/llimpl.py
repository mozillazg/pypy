"""
The non-RPythonic part of the llgraph backend.
This contains all the code that is directly run
when executing on top of the llinterpreter.
"""

from pypy.objspace.flow.model import Variable, Constant
from pypy.annotation import model as annmodel
from pypy.jit.metainterp.history import (ConstInt, ConstPtr, ConstAddr,
                                         BoxInt, BoxPtr)
from pypy.rpython.lltypesystem import lltype, llmemory, rclass, rstr
from pypy.rpython.ootypesystem import ootype
from pypy.rpython.module.support import LLSupport, OOSupport
from pypy.rpython.llinterp import LLInterpreter, LLFrame, LLException
from pypy.rpython.extregistry import ExtRegistryEntry

from pypy.jit.metainterp import heaptracker
from pypy.jit.backend.llgraph import symbolic

from pypy.rlib.objectmodel import ComputedIntSymbolic

import py
from pypy.tool.ansi_print import ansi_log
log = py.log.Producer('runner')
py.log.setconsumer('runner', ansi_log)


def _from_opaque(opq):
    return opq._obj.externalobj

_TO_OPAQUE = {}

def _to_opaque(value):
    return lltype.opaqueptr(_TO_OPAQUE[value.__class__], 'opaque',
                            externalobj=value)

def from_opaque_string(s):
    if isinstance(s, str):
        return s
    elif isinstance(s, ootype._string):
        return OOSupport.from_rstr(s)
    else:
        return LLSupport.from_rstr(s)

# a list of argtypes of all operations - couldn't find any and it's
# very useful
TYPES = {
    'int_add'         : (('int', 'int'), 'int'),
    'int_mod'         : (('int', 'int'), 'int'),
    'int_rshift'      : (('int', 'int'), 'int'),
    'int_and'         : (('int', 'int'), 'int'),
    'int_sub'         : (('int', 'int'), 'int'),
    'int_mul'         : (('int', 'int'), 'int'),
    'int_lt'          : (('int', 'int'), 'bool'),
    'int_gt'          : (('int', 'int'), 'bool'),
    'int_ge'          : (('int', 'int'), 'bool'),
    'int_le'          : (('int', 'int'), 'bool'),
    'int_eq'          : (('int', 'int'), 'bool'),
    'int_ne'          : (('int', 'int'), 'bool'),
    'int_is_true'     : (('int',), 'bool'),
    'int_neg'         : (('int',), 'int'),
    'int_invert'      : (('int',), 'int'),
    'int_add_ovf'     : (('int', 'int'), 'int'),
    'int_sub_ovf'     : (('int', 'int'), 'int'),
    'int_mul_ovf'     : (('int', 'int'), 'int'),
    'int_neg_ovf'     : (('int',), 'int'),
    'bool_not'        : (('bool',), 'bool'),
    'new_with_vtable' : (('int', 'ptr'), 'ptr'),
    'new'             : (('int',), 'ptr'),
    'new_array'       : (('int', 'int'), 'ptr'),
    'oononnull'       : (('ptr',), 'bool'),
    'ooisnull'        : (('ptr',), 'bool'),
    'oois'            : (('ptr', 'ptr'), 'bool'),
    'ooisnot'         : (('ptr', 'ptr'), 'bool'),
    'setfield_gc'     : (('ptr', 'fieldname', 'intorptr'), None),
    'getfield_gc'     : (('ptr', 'fieldname'), 'intorptr'),
    'setfield_raw'    : (('ptr', 'fieldname', 'intorptr'), None),
    'getfield_raw'    : (('ptr', 'fieldname'), 'intorptr'),
    'setarrayitem_gc' : (('ptr', 'int', 'int', 'intorptr'), None),
    'getarrayitem_gc' : (('ptr', 'int', 'int'), 'intorptr'),
    'call_ptr'        : (('ptr', 'varargs'), 'ptr'),
    'call__4'         : (('ptr', 'varargs'), 'int'),
    'call_void'       : (('ptr', 'varargs'), None),
    'guard_true'      : (('bool',), None),
    'guard_false'     : (('bool',), None),
    'guard_value'     : (('int', 'int'), None),
    'guard_class'     : (('ptr', 'ptr'), None),
    'guard_no_exception'   : ((), None),
    'guard_exception'      : (('ptr',), 'ptr'),
    'guard_nonvirtualized' : (('ptr', 'ptr', 'int'), None),
    'guard_builtin'   : (('ptr',), None),
    'newstr'          : (('int',), 'ptr'),
    'strlen'          : (('ptr',), 'int'),
    'strgetitem'      : (('ptr', 'int'), 'int'),
    'strsetitem'      : (('ptr', 'int', 'int'), None),
    'getitem'         : (('void', 'ptr', 'int'), 'int'),
    'setitem'         : (('void', 'ptr', 'int', 'int'), None),
    'newlist'         : (('void', 'varargs'), 'ptr'),
    'append'          : (('void', 'ptr', 'int'), None),
    'insert'          : (('void', 'ptr', 'int', 'int'), None),
    'pop'             : (('void', 'ptr',), 'int'),
    'len'             : (('void', 'ptr',), 'int'),
    'listnonzero'     : (('void', 'ptr',), 'int'),
}

# ____________________________________________________________


class LoopOrBridge(object):
    def __init__(self):
        self.operations = []

    def __repr__(self):
        lines = ['\t' + repr(op) for op in self.operations]
        lines.insert(0, 'LoopOrBridge:')
        return '\n'.join(lines)

class Operation(object):
    def __init__(self, opname):
        self.opname = opname
        self.args = []
        self.results = []
        self.livevars = []   # for guards only

    def __repr__(self):
        results = self.results
        if len(results) == 1:
            sres = repr0(results[0])
        else:
            sres = repr0(results)
        return '{%s = %s(%s)}' % (sres, self.opname,
                                  ', '.join(map(repr0, self.args)))

def repr0(x):
    if isinstance(x, list):
        return '[' + ', '.join(repr0(y) for y in x) + ']'
    elif isinstance(x, Constant):
        return '(' + repr0(x.value) + ')'
    elif isinstance(x, lltype._ptr):
        x = llmemory.cast_ptr_to_adr(x)
        if x.ptr:
            try:
                container = x.ptr._obj._normalizedcontainer()
                return '* %s' % (container._TYPE._short_name(),)
            except AttributeError:
                return repr(x)
        else:
            return 'NULL'
    else:
        return repr(x)

def repr_list(lst, types, memocast):
    res_l = []
    if types and types[-1] == 'varargs':
        types = types[:-1] + ('int',) * (len(lst) - len(types) + 1)
    assert len(types) == len(lst)
    for elem, tp in zip(lst, types):
        if len(lst) >= 2:
            extraarg = lst[1]
        else:
            extraarg = None
        if isinstance(elem, Constant):
            res_l.append('(%s)' % repr1(elem, tp, memocast, extraarg))
        else:
            res_l.append(repr1(elem, tp, memocast, extraarg))
    return '[%s]' % (', '.join(res_l))

def repr1(x, tp, memocast, extraarg):
    if tp == "intorptr":
        if extraarg % 2:
            tp = "ptr"
        else:
            tp = "int"
    if tp == 'int':
        return str(x)
    elif tp == 'void':
        return ''
    elif tp == 'ptr':
        if not x:
            return '(* None)'
        if isinstance(x, int):
            # XXX normalize?
            ptr = str(cast_int_to_adr(memocast, x))
        else:
            if getattr(x, '_fake', None):
                return repr(x)
            if lltype.typeOf(x) == llmemory.GCREF:
                TP = lltype.Ptr(lltype.typeOf(x._obj.container))
                ptr = lltype.cast_opaque_ptr(TP, x)
            else:
                ptr = x
        try:
            container = ptr._obj._normalizedcontainer()
            return '(* %s)' % (container._TYPE._short_name(),)
        except AttributeError:
            return '(%r)' % (ptr,)
    elif tp == 'bool':
        assert x == 0 or x == 1
        return str(bool(x))
    elif tp == 'fieldname':
        return str(symbolic.TokenToField[x/2][1])
    else:
        raise NotImplementedError("tp = %s" % tp)

_variables = []

def compile_start():
    del _variables[:]
    return _to_opaque(LoopOrBridge())

def compile_start_int_var(loop):
    loop = _from_opaque(loop)
    assert not loop.operations
    v = Variable()
    v.concretetype = lltype.Signed
    r = len(_variables)
    _variables.append(v)
    return r

def compile_start_ptr_var(loop):
    loop = _from_opaque(loop)
    assert not loop.operations
    v = Variable()
    v.concretetype = llmemory.GCREF
    r = len(_variables)
    _variables.append(v)
    return r

def compile_add(loop, opname):
    loop = _from_opaque(loop)
    opname = from_opaque_string(opname)
    loop.operations.append(Operation(opname))

def compile_add_var(loop, intvar):
    loop = _from_opaque(loop)
    op = loop.operations[-1]
    op.args.append(_variables[intvar])

def compile_add_int_const(loop, value):
    loop = _from_opaque(loop)
    const = Constant(value)
    const.concretetype = lltype.Signed
    op = loop.operations[-1]
    op.args.append(const)

def compile_add_ptr_const(loop, value):
    loop = _from_opaque(loop)
    const = Constant(value)
    const.concretetype = llmemory.GCREF
    op = loop.operations[-1]
    op.args.append(const)

def compile_add_int_result(loop):
    loop = _from_opaque(loop)
    v = Variable()
    v.concretetype = lltype.Signed
    op = loop.operations[-1]
    op.results.append(v)
    r = len(_variables)
    _variables.append(v)
    return r

def compile_add_ptr_result(loop):
    loop = _from_opaque(loop)
    v = Variable()
    v.concretetype = llmemory.GCREF
    op = loop.operations[-1]
    op.results.append(v)
    r = len(_variables)
    _variables.append(v)
    return r

def compile_add_jump_target(loop, loop_target, loop_target_index):
    loop = _from_opaque(loop)
    loop_target = _from_opaque(loop_target)
    op = loop.operations[-1]
    op.jump_target = loop_target
    op.jump_target_index = loop_target_index
    if op.opname == 'jump':
        if loop_target == loop and loop_target_index == 0:
            log.info("compiling new loop")
        else:
            log.info("compiling new bridge")

def compile_add_failnum(loop, failnum):
    loop = _from_opaque(loop)
    op = loop.operations[-1]
    op.failnum = failnum

def compile_add_livebox(loop, intvar):
    loop = _from_opaque(loop)
    op = loop.operations[-1]
    op.livevars.append(_variables[intvar])

def compile_from_guard(loop, guard_loop, guard_opindex):
    loop = _from_opaque(loop)
    guard_loop = _from_opaque(guard_loop)
    op = guard_loop.operations[guard_opindex]
    assert op.opname.startswith('guard_')
    op.jump_target = loop
    op.jump_target_index = 0

# ------------------------------

class Frame(object):

    def __init__(self, memocast):
        llinterp = LLInterpreter(_rtyper)    # '_rtyper' set by CPU
        llinterp.traceback_frames = []
        self.llframe = ExtendedLLFrame(None, None, llinterp)
        self.llframe.memocast = memocast
        self.llframe.last_exception = None
        self.llframe.last_exception_handled = True
        self.verbose = False
        self.memocast = memocast

    def getenv(self, v):
        if isinstance(v, Constant):
            return v.value
        else:
            return self.env[v]

    def go_to_merge_point(self, loop, opindex, args):
        mp = loop.operations[opindex]
        assert len(mp.args) == len(args)
        self.loop = loop
        self.opindex = opindex
        self.env = dict(zip(mp.args, args))

    def execute(self):
        """Execute all operations in a loop,
        possibly following to other loops as well.
        """
        verbose = True
        while True:
            self.opindex += 1
            op = self.loop.operations[self.opindex]
            args = [self.getenv(v) for v in op.args]
            if op.opname == 'merge_point':
                self.go_to_merge_point(self.loop, self.opindex, args)
                continue
            if op.opname == 'jump':
                self.go_to_merge_point(op.jump_target,
                                       op.jump_target_index,
                                       args)
                _stats.exec_jumps += 1
                continue
            try:
                results = self.execute_operation(op.opname, args, verbose)
                #verbose = self.verbose
                assert len(results) == len(op.results)
                assert len(op.results) <= 1
                if len(op.results) > 0:
                    RESTYPE = op.results[0].concretetype
                    if RESTYPE is lltype.Signed:
                        x = self.as_int(results[0])
                    elif RESTYPE is llmemory.GCREF:
                        x = self.as_ptr(results[0])
                    else:
                        raise Exception("op.results[0].concretetype is %r"
                                        % (RESTYPE,))
                    self.env[op.results[0]] = x
            except GuardFailed:
                assert self.llframe.last_exception_handled
                if hasattr(op, 'jump_target'):
                    # the guard already failed once, go to the
                    # already-generated code
                    catch_op = op.jump_target.operations[0]
                    assert catch_op.opname == 'catch'
                    args = []
                    it = iter(op.livevars)
                    for v in catch_op.args:
                        if isinstance(v, Variable):
                            args.append(self.getenv(it.next()))
                        else:
                            args.append(v)
                    assert list(it) == []
                    self.go_to_merge_point(op.jump_target,
                                           op.jump_target_index,
                                           args)
                else:
                    if self.verbose:
                        log.trace('failed: %s(%s)' % (
                            op.opname, ', '.join(map(str, args))))
                    self.failed_guard_op = op
                    return op.failnum

    def execute_operation(self, opname, values, verbose):
        """Execute a single operation.
        """
        ophandler = self.llframe.getoperationhandler(opname)
        assert not getattr(ophandler, 'specialform', False)
        if getattr(ophandler, 'need_result_type', False):
            assert result_type is not None
            values = list(values)
            values.insert(0, result_type)
        exec_counters = _stats.exec_counters
        exec_counters[opname] = exec_counters.get(opname, 0) + 1
        for i in range(len(values)):
            if isinstance(values[i], ComputedIntSymbolic):
                values[i] = values[i].compute_fn()
        res = ophandler(*values)
        if verbose:
            argtypes, restype = TYPES[opname]
            if res is None:
                resdata = ''
            else:
                if len(values) >= 2:
                    extraarg = values[1]
                else:
                    extraarg = None
                resdata = '-> ' + repr1(res, restype, self.memocast, extraarg)
            # fish the types
            log.cpu('\t%s %s %s' % (opname, repr_list(values, argtypes,
                                                      self.memocast), resdata))
        if res is None:
            return []
        elif isinstance(res, list):
            return res
        else:
            return [res]

    def as_int(self, x):
        TP = lltype.typeOf(x)
        if isinstance(TP, lltype.Ptr):
            assert TP.TO._gckind == 'raw'
            return cast_adr_to_int(self.memocast, llmemory.cast_ptr_to_adr(x))
        if TP == llmemory.Address:
            return cast_adr_to_int(self.memocast, x)
        return lltype.cast_primitive(lltype.Signed, x)
    
    def as_ptr(self, x):
        if isinstance(lltype.typeOf(x), lltype.Ptr):
            return lltype.cast_opaque_ptr(llmemory.GCREF, x)
        else:
            return x

    def log_progress(self):
        count = sum(_stats.exec_counters.values())
        count_jumps = _stats.exec_jumps
        log.trace('ran %d operations, %d jumps' % (count, count_jumps))


def new_frame(memocast):
    frame = Frame(memocast)
    return _to_opaque(frame)

def frame_clear(frame, loop, opindex):
    frame = _from_opaque(frame)
    loop = _from_opaque(loop)
    frame.loop = loop
    frame.opindex = opindex
    frame.env = {}

def frame_add_int(frame, value):
    frame = _from_opaque(frame)
    i = len(frame.env)
    mp = frame.loop.operations[0]
    frame.env[mp.args[i]] = value

def frame_add_ptr(frame, value):
    frame = _from_opaque(frame)
    i = len(frame.env)
    mp = frame.loop.operations[0]
    frame.env[mp.args[i]] = value

def frame_execute(frame):
    frame = _from_opaque(frame)
    if frame.verbose:
        mp = frame.loop.operations[0]
        values = [frame.env[v] for v in mp.args]
        log.trace('Entering CPU frame <- %r' % (values,))
    try:
        result = frame.execute()
        if frame.verbose:
            log.trace('Leaving CPU frame -> #%d' % (result,))
            frame.log_progress()
    except ExecutionReturned, e:
        frame.returned_value = e.args[0]
        return -1
    except ExecutionRaised, e:
        raise e.args[0]
    except Exception, e:
        log.ERROR('%s in CPU frame: %s' % (e.__class__.__name__, e))
        raise
    return result

def frame_int_getvalue(frame, num):
    frame = _from_opaque(frame)
    return frame.env[frame.failed_guard_op.livevars[num]]

def frame_ptr_getvalue(frame, num):
    frame = _from_opaque(frame)
    return frame.env[frame.failed_guard_op.livevars[num]]

def frame_int_setvalue(frame, num, value):
    frame = _from_opaque(frame)
    frame.env[frame.loop.operations[0].args[num]] = value

def frame_ptr_setvalue(frame, num, value):
    frame = _from_opaque(frame)
    frame.env[frame.loop.operations[0].args[num]] = value

def frame_int_getresult(frame):
    frame = _from_opaque(frame)
    return frame.returned_value

def frame_ptr_getresult(frame):
    frame = _from_opaque(frame)
    return frame.returned_value

def frame_exception(frame):
    frame = _from_opaque(frame)
    assert frame.llframe.last_exception_handled
    last_exception = frame.llframe.last_exception
    if last_exception:
        return llmemory.cast_ptr_to_adr(last_exception.args[0])
    else:
        return llmemory.NULL

def frame_exc_value(frame):
    frame = _from_opaque(frame)
    last_exception = frame.llframe.last_exception
    if last_exception:
        return lltype.cast_opaque_ptr(llmemory.GCREF, last_exception.args[1])
    else:
        return lltype.nullptr(llmemory.GCREF.TO)

class MemoCast(object):
    def __init__(self):
        self.addresses = [llmemory.NULL]
        self.rev_cache = {}

def new_memo_cast():
    memocast = MemoCast()
    return _to_opaque(memocast)

def cast_adr_to_int(memocast, adr):
    # xxx slow
    assert lltype.typeOf(adr) == llmemory.Address
    memocast = _from_opaque(memocast)
    addresses = memocast.addresses
    for i in xrange(len(addresses)-1, -1, -1):
        if addresses[i] == adr:
            return i
    i = len(addresses)
    addresses.append(adr)
    return i

def cast_int_to_adr(memocast, int):
    memocast = _from_opaque(memocast)
    assert 0 <= int < len(memocast.addresses)
    return memocast.addresses[int]

class GuardFailed(Exception):
    pass

class ExecutionReturned(Exception):
    pass

class ExecutionRaised(Exception):
    pass

class ExtendedLLFrame(LLFrame):

    def newsubframe(self, graph, args):
        # the default implementation would also create an ExtendedLLFrame,
        # but we don't want this to occur in our case
        return LLFrame(graph, args, self.llinterpreter)

    def op_return(self, value=None):
        if self.last_exception is None:
            raise ExecutionReturned(value)
        else:
            raise ExecutionRaised(self.last_exception)

    def op_guard_pause(self):
        raise GuardFailed

    def op_guard_builtin(self, b):
        pass

    def op_guard_true(self, value):
        if not value:
            raise GuardFailed

    def op_guard_false(self, value):
        if value:
            raise GuardFailed

    op_guard_nonzero = op_guard_true
    op_guard_iszero  = op_guard_false

    def op_guard_nonnull(self, ptr):
        if lltype.typeOf(ptr) != llmemory.GCREF:
            ptr = cast_int_to_adr(self.memocast, ptr)
        if not ptr:
            raise GuardFailed

    def op_guard_isnull(self, ptr):
        if lltype.typeOf(ptr) != llmemory.GCREF:
            ptr = cast_int_to_adr(self.memocast, ptr)
        if ptr:
            raise GuardFailed

    def op_guard_lt(self, value1, value2):
        if value1 >= value2:
            raise GuardFailed

    def op_guard_le(self, value1, value2):
        if value1 > value2:
            raise GuardFailed

    def op_guard_eq(self, value1, value2):
        if value1 != value2:
            raise GuardFailed

    def op_guard_ne(self, value1, value2):
        if value1 == value2:
            raise GuardFailed

    def op_guard_gt(self, value1, value2):
        if value1 <= value2:
            raise GuardFailed

    def op_guard_ge(self, value1, value2):
        if value1 < value2:
            raise GuardFailed

    op_guard_is    = op_guard_eq
    op_guard_isnot = op_guard_ne

    def op_guard_class(self, value, expected_class):
        value = lltype.cast_opaque_ptr(rclass.OBJECTPTR, value)
        expected_class = llmemory.cast_adr_to_ptr(
            cast_int_to_adr(self.memocast, expected_class),
            rclass.CLASSTYPE)
        if value.typeptr != expected_class:
            raise GuardFailed

    def op_guard_value(self, value, expected_value):
        if value != expected_value:
            raise GuardFailed

    def op_guard_nonvirtualized(self, value, expected_class,
                                for_accessing_field):
        self.op_guard_class(value, expected_class)
        if heaptracker.cast_vable(value).vable_rti:
            raise GuardFailed    # some other code is already in control

    def op_guard_no_exception(self):
        if self.last_exception:
            self.last_exception_handled = True
            raise GuardFailed

    def op_guard_exception(self, expected_exception):
        expected_exception = llmemory.cast_adr_to_ptr(
            cast_int_to_adr(self.memocast, expected_exception),
            rclass.CLASSTYPE)
        assert expected_exception
        if self.last_exception:
            got = self.last_exception.args[0]
            self.last_exception_handled = True
            if not rclass.ll_issubclass(got, expected_exception):
                raise GuardFailed
            return self.last_exception.args[1]
        else:
            raise GuardFailed

    def op_new(self, typesize):
        TYPE = symbolic.Size2Type[typesize]
        return lltype.malloc(TYPE)

    def op_new_with_vtable(self, typesize, vtable):
        TYPE = symbolic.Size2Type[typesize]
        ptr = lltype.malloc(TYPE)
        ptr = lltype.cast_opaque_ptr(llmemory.GCREF, ptr)
        self.op_setfield_gc(ptr, 2, vtable)
        return ptr

    def op_new_array(self, arraydesc, count):
        ITEMTYPE = symbolic.Size2Type[arraydesc/2]
        return lltype.malloc(lltype.GcArray(ITEMTYPE), count)

    def op_getfield_gc(self, ptr, fielddesc):
        STRUCT, fieldname = symbolic.TokenToField[fielddesc/2]
        ptr = lltype.cast_opaque_ptr(lltype.Ptr(STRUCT), ptr)
        return getattr(ptr, fieldname)

    def op_getfield_raw(self, intval, fielddesc):
        STRUCT, fieldname = symbolic.TokenToField[fielddesc/2]
        ptr = llmemory.cast_adr_to_ptr(cast_int_to_adr(self.memocast, intval),
                                       lltype.Ptr(STRUCT))
        return getattr(ptr, fieldname)

    def _cast_newvalue(self, desc, TYPE, newvalue):
        if desc % 2:
            newvalue = lltype.cast_opaque_ptr(TYPE, newvalue)
        else:
            if isinstance(TYPE, lltype.Ptr):
                assert TYPE.TO._gckind == 'raw'
                newvalue = llmemory.cast_adr_to_ptr(
                    cast_int_to_adr(self.memocast, newvalue),
                    TYPE)
            elif TYPE == llmemory.Address:
                newvalue = cast_int_to_adr(self.memocast, newvalue)
        return newvalue

    def op_setfield_gc(self, ptr, fielddesc, newvalue):
        offset = fielddesc/2
        STRUCT, fieldname = symbolic.TokenToField[offset]
        if lltype.typeOf(ptr) == llmemory.GCREF:
            ptr = lltype.cast_opaque_ptr(lltype.Ptr(STRUCT), ptr)
        FIELDTYPE = getattr(STRUCT, fieldname)
        newvalue = self._cast_newvalue(fielddesc, FIELDTYPE, newvalue)
        setattr(ptr, fieldname, newvalue)

    def op_setfield_raw(self, intval, fielddesc, newvalue):
        ptr = llmemory.cast_adr_to_ptr(cast_int_to_adr(self.memocast, intval),
                                       lltype.Ptr(STRUCT))
        self.op_setfield_gc(ptr, fielddesc, newvalue)

    def op_getarrayitem_gc(self, array, arraydesc, index):
        array = array._obj.container
        return array.getitem(index)

    def op_setarrayitem_gc(self, array, arraydesc, index, newvalue):
        ITEMTYPE = symbolic.Size2Type[arraydesc/2]
        array = array._obj.container
        newvalue = self._cast_newvalue(arraydesc, ITEMTYPE, newvalue)
        array.setitem(index, newvalue)

    def op_ooisnull(self, ptr):
        if lltype.typeOf(ptr) != llmemory.GCREF:
            ptr = cast_int_to_adr(self.memocast, ptr)
        return not ptr

    def op_oononnull(self, ptr):
        if lltype.typeOf(ptr) != llmemory.GCREF:
            ptr = cast_int_to_adr(self.memocast, ptr)
        return bool(ptr)

    def op_oois(self, ptr1, ptr2):
        return ptr1 == ptr2

    def op_ooisnot(self, ptr1, ptr2):
        return ptr1 != ptr2

    def op_bool_not(self, b):
        assert isinstance(b, int)
        return not b

    def op_strlen(self, str):
        str = lltype.cast_opaque_ptr(lltype.Ptr(rstr.STR), str)
        return len(str.chars)

    def op_strgetitem(self, str, index):
        str = lltype.cast_opaque_ptr(lltype.Ptr(rstr.STR), str)
        return ord(str.chars[index])

    def op_strsetitem(self, str, index, newchar):
        str = lltype.cast_opaque_ptr(lltype.Ptr(rstr.STR), str)
        str.chars[index] = chr(newchar)

    def op_newstr(self, length):
        return rstr.mallocstr(length)

    def catch_exception(self, e):
        assert self.last_exception_handled
        self.last_exception = e
        self.last_exception_handled = False

    def clear_exception(self):
        assert self.last_exception_handled
        self.last_exception = None

    def do_call(self, f, *args):
        ptr = cast_int_to_adr(self.memocast, f).ptr
        FUNC = lltype.typeOf(ptr).TO
        ARGS = FUNC.ARGS
        args = list(args)
        for i in range(len(ARGS)):
            if ARGS[i] is lltype.Void:
                args.insert(i, lltype.Void)
        assert len(ARGS) == len(args)
        fixedargs = [heaptracker.fixupobj(TYPE, x)
                     for TYPE, x in zip(ARGS, args)]
        try:
            x = self.perform_call(ptr, ARGS, fixedargs)
        except LLException, e:
            self.catch_exception(e)
            x = FUNC.RESULT._defl()
        else:
            self.clear_exception()
        return x

    op_call__4 = do_call
    op_call_ptr = do_call
    op_call_void = do_call

    def op_listop_return(self, ll_func, *args):
        return self.do_call(ll_func, *args)

    def op_listop(self, ll_func, *args):
        self.do_call(ll_func, *args)

    op_getitem = op_listop_return
    op_setitem = op_listop
    op_append = op_listop
    op_insert = op_listop
    op_pop = op_listop_return
    op_len = op_listop_return
    op_listnonzero = op_listop_return

    def op_newlist(self, ll_newlist, lgt, default_val=None):
        res = self.do_call(ll_newlist, lgt)
        if (default_val is not None and
            isinstance(lltype.typeOf(default_val), lltype.Ptr)):
            if hasattr(res, 'items'):
                TP = lltype.typeOf(res.items).TO.OF
            else:
                TP = lltype.typeOf(res).TO.OF
            if default_val:
                default_val = lltype.cast_opaque_ptr(TP, res)
            else:
                default_val = lltype.nullptr(TP.TO)
        if default_val is not None:
            if hasattr(res, 'items'):
                items = res.items
            else:
                items = res
            for i in range(len(items)):
                items[i] = default_val
        return res

    for _opname in ['int_add_ovf', 'int_sub_ovf', 'int_mul_ovf',
                    'int_neg_ovf',
                    ]:
        exec py.code.Source('''
            def op_%s(self, *args):
                try:
                    z = LLFrame.op_%s(self, *args)
                except LLException, e:
                    self.catch_exception(e)
                    z = 0
                else:
                    self.clear_exception()
                return z
        ''' % (_opname, _opname)).compile()

# ____________________________________________________________


def setannotation(func, annotation, specialize_as_constant=False):

    class Entry(ExtRegistryEntry):
        "Annotation and specialization for calls to 'func'."
        _about_ = func

        if annotation is None or isinstance(annotation, annmodel.SomeObject):
            s_result_annotation = annotation
        else:
            def compute_result_annotation(self, *args_s):
                return annotation(*args_s)

        if specialize_as_constant:
            def specialize_call(self, hop):
                llvalue = func(hop.args_s[0].const)
                return hop.inputconst(lltype.typeOf(llvalue), llvalue)
        else:
            # specialize as direct_call
            def specialize_call(self, hop):
                ARGS = [r.lowleveltype for r in hop.args_r]
                RESULT = hop.r_result.lowleveltype
                if hop.rtyper.type_system.name == 'lltypesystem':
                    FUNCTYPE = lltype.FuncType(ARGS, RESULT)
                    funcptr = lltype.functionptr(FUNCTYPE, func.__name__,
                                                 _callable=func, _debugexc=True)
                    cfunc = hop.inputconst(lltype.Ptr(FUNCTYPE), funcptr)
                else:
                    FUNCTYPE = ootype.StaticMethod(ARGS, RESULT)
                    sm = ootype._static_meth(FUNCTYPE, _name=func.__name__, _callable=func)
                    cfunc = hop.inputconst(FUNCTYPE, sm)
                args_v = hop.inputargs(*hop.args_r)
                return hop.genop('direct_call', [cfunc] + args_v, hop.r_result)


LOOPORBRIDGE = lltype.Ptr(lltype.OpaqueType("LoopOrBridge"))
FRAME = lltype.Ptr(lltype.OpaqueType("Frame"))
MEMOCAST = lltype.Ptr(lltype.OpaqueType("MemoCast"))

_TO_OPAQUE[LoopOrBridge] = LOOPORBRIDGE.TO
_TO_OPAQUE[Frame] = FRAME.TO
_TO_OPAQUE[MemoCast] = MEMOCAST.TO

s_LoopOrBridge = annmodel.SomePtr(LOOPORBRIDGE)
s_Frame = annmodel.SomePtr(FRAME)
s_MemoCast = annmodel.SomePtr(MEMOCAST)

setannotation(compile_start, s_LoopOrBridge)
setannotation(compile_start_int_var, annmodel.SomeInteger())
setannotation(compile_start_ptr_var, annmodel.SomeInteger())
setannotation(compile_add, annmodel.s_None)
setannotation(compile_add_var, annmodel.s_None)
setannotation(compile_add_int_const, annmodel.s_None)
setannotation(compile_add_ptr_const, annmodel.s_None)
setannotation(compile_add_int_result, annmodel.SomeInteger())
setannotation(compile_add_ptr_result, annmodel.SomeInteger())
setannotation(compile_add_jump_target, annmodel.s_None)
setannotation(compile_add_failnum, annmodel.s_None)
setannotation(compile_from_guard, annmodel.s_None)
setannotation(compile_add_livebox, annmodel.s_None)

setannotation(new_frame, s_Frame)
setannotation(frame_clear, annmodel.s_None)
setannotation(frame_add_int, annmodel.s_None)
setannotation(frame_add_ptr, annmodel.s_None)
setannotation(frame_execute, annmodel.SomeInteger())
setannotation(frame_int_getvalue, annmodel.SomeInteger())
setannotation(frame_ptr_getvalue, annmodel.SomePtr(llmemory.GCREF))
setannotation(frame_int_setvalue, annmodel.s_None)
setannotation(frame_ptr_setvalue, annmodel.s_None)
setannotation(frame_int_getresult, annmodel.SomeInteger())
setannotation(frame_ptr_getresult, annmodel.SomePtr(llmemory.GCREF))
setannotation(frame_exception, annmodel.SomeAddress())
setannotation(frame_exc_value, annmodel.SomePtr(llmemory.GCREF))

setannotation(new_memo_cast, s_MemoCast)
setannotation(cast_adr_to_int, annmodel.SomeInteger())
setannotation(cast_int_to_adr, annmodel.SomeAddress())
