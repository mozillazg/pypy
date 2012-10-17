
from weakref import WeakKeyDictionary

from pypy.jit.backend import model
from pypy.jit.backend.llgraph import support
from pypy.jit.metainterp.history import Const, getkind, AbstractDescr, VOID
from pypy.jit.metainterp.resoperation import rop
from pypy.jit.codewriter import heaptracker

from pypy.rpython.llinterp import LLInterpreter
from pypy.rpython.lltypesystem import lltype, llmemory, rclass, rstr

from pypy.rlib.rarithmetic import ovfcheck

class LLLoop(object):
    def __init__(self, inputargs, operations):
        self.inputargs = inputargs
        self.operations = operations

class GuardFailed(Exception):
    def __init__(self, failargs, descr):
        self.failargs = failargs
        self.descr = descr

class ExecutionFinished(Exception):
    def __init__(self, descr, args):
        self.descr = descr
        self.args = args

class Jump(Exception):
    def __init__(self, descr, args):
        self.descr = descr
        self.args = args

class CallDescr(AbstractDescr):
    def __init__(self, RESULT, ARGS):
        self.RESULT = RESULT
        self.ARGS = ARGS

class SizeDescr(AbstractDescr):
    def __init__(self, S):
        self.S = S
    def as_vtable_size_descr(self):
        return self

class FieldDescr(AbstractDescr):
    def __init__(self, S, fieldname):
        self.S = S
        self.fieldname = fieldname
        self.FIELD = getattr(S, fieldname)

    def is_pointer_field(self):
        return getkind(self.FIELD) == 'ref'

class ArrayDescr(AbstractDescr):
    def __init__(self, A):
        self.A = A

    def is_array_of_pointers(self):
        return getkind(self.A.OF) == 'ref'

class InteriorFieldDescr(AbstractDescr):
    def __init__(self, A, fieldname):
        self.A = A
        self.fieldname = fieldname
        self.FIELD = getattr(A.OF, fieldname)

class LLGraphCPU(model.AbstractCPU):
    def __init__(self, rtyper):
        self.rtyper = rtyper
        self.llinterp = LLInterpreter(rtyper)
        self.known_labels = WeakKeyDictionary()
        self.exc_value = lltype.nullptr(llmemory.GCREF.TO)
        self.descrs = {}

    def compile_loop(self, inputargs, operations, looptoken, log=True, name=''):
        self.total_compiled_loops += 1
        for i, op in enumerate(operations):
            if op.getopnum() == rop.LABEL:
                self.known_labels[op.getdescr()] = (operations, i)
        looptoken._llgraph_loop = LLLoop(inputargs, operations)

    def compile_bridge(self, faildescr, inputargs, operations,
                       original_loop_token):
        faildescr._llgraph_bridge = LLLoop(inputargs, operations)
        self.total_compiled_bridges += 1

    def make_execute_token(self, *argtypes):
        return self._execute_token

    def _execute_token(self, loop_token, *args):
        loop = loop_token._llgraph_loop
        frame = LLFrame(self, loop.inputargs, args)
        try:
            frame.execute(loop.operations)
            assert False
        except ExecutionFinished, e:
            self.latest_values = e.args
            return e.descr
        except GuardFailed, e:
            self.latest_values = e.failargs
            return e.descr

    def get_latest_value_int(self, index):
        return self.latest_values[index]
    get_latest_value_float = get_latest_value_int
    get_latest_value_ref   = get_latest_value_int

    def get_latest_value_count(self):
        return len(self.latest_values)

    def clear_latest_values(self, count):
        del self.latest_values

    def grab_exc_value(self):
        return self.exc_value

    def calldescrof(self, FUNC, ARGS, RESULT, effect_info):
        key = ('call', getkind(RESULT),
               tuple([getkind(A) for A in ARGS]),
               effect_info)
        try:
            return self.descrs[key]
        except KeyError:
            descr = CallDescr(RESULT, ARGS)
            self.descrs[key] = descr
            return descr

    def sizeof(self, S):
        key = ('size', S)
        try:
            return self.descrs[key]
        except KeyError:
            descr = SizeDescr(S)
            self.descrs[key] = descr
            return descr

    def fielddescrof(self, S, fieldname):
        key = ('field', S, fieldname)
        try:
            return self.descrs[key]
        except KeyError:
            descr = FieldDescr(S, fieldname)
            self.descrs[key] = descr
            return descr

    def arraydescrof(self, A):
        key = ('array', A)
        try:
            return self.descrs[key]
        except KeyError:
            descr = ArrayDescr(A)
            self.descrs[key] = descr
            return descr

    def interiorfielddescrof(self, A, fieldname):
        key = ('interiorfield', A, fieldname)
        try:
            return self.descrs[key]
        except KeyError:
            descr = InteriorFieldDescr(A, fieldname)
            self.descrs[key] = descr
            return descr        

    def _calldescr_dynamic_for_tests(self, atypes, rtype,
                                     abiname='FFI_DEFAULT_ABI'):
        # XXX WTF is that and why it breaks all abstractions?
        from pypy.jit.backend.llsupport import ffisupport
        return ffisupport.calldescr_dynamic_for_tests(self, atypes, rtype,
                                                      abiname)

    def calldescrof_dynamic(self, cif_description, extrainfo):
        # XXX WTF, this is happy nonsense
        from pypy.jit.backend.llsupport.ffisupport import get_ffi_type_kind
        from pypy.jit.backend.llsupport.ffisupport import UnsupportedKind
        ARGS = []
        try:
            for itp in range(cif_description.nargs):
                arg = cif_description.atypes[itp]
                kind = get_ffi_type_kind(self, arg)
                if kind != VOID:
                    ARGS.append(support.kind2TYPE[kind[0]])
            RESULT = support.kind2TYPE[get_ffi_type_kind(self, cif_description.rtype)[0]]
        except UnsupportedKind:
            return None
        key = ('call_dynamic', RESULT, tuple(ARGS),
               extrainfo, cif_description.abi)
        try:
            return self.descrs[key]
        except KeyError:
            descr = CallDescr(RESULT, ARGS)
            self.descrs[key] = descr
            return descr

    # ------------------------------------------------------------

    def call(self, func, calldescr, args):
        TP = llmemory.cast_int_to_adr(func).ptr._obj._TYPE
        RESULT = TP.RESULT
        func = llmemory.cast_int_to_adr(func).ptr._obj._callable
        res = func(*args)
        return support.cast_result(RESULT, res)

    def _do_call(self, func, args_i, args_r, args_f, calldescr):
        TP = llmemory.cast_int_to_adr(func).ptr._obj._TYPE
        args = support.cast_call_args(TP.ARGS, args_i, args_r, args_f)
        return self.call(func, calldescr, args)

    bh_call_i = _do_call
    bh_call_r = _do_call
    bh_call_f = _do_call
    bh_call_v = _do_call

    def bh_getfield_gc(self, p, descr):
        p = lltype.cast_opaque_ptr(lltype.Ptr(descr.S), p)
        return support.cast_result(descr.FIELD, getattr(p, descr.fieldname))

    bh_getfield_gc_i = bh_getfield_gc
    bh_getfield_gc_r = bh_getfield_gc
    bh_getfield_gc_f = bh_getfield_gc

    def bh_setfield_gc(self, p, newvalue, descr):
        p = lltype.cast_opaque_ptr(lltype.Ptr(descr.S), p)
        setattr(p, descr.fieldname, support.cast_arg(descr.FIELD, newvalue))

    bh_setfield_gc_i = bh_setfield_gc
    bh_setfield_gc_r = bh_setfield_gc
    bh_setfield_gc_f = bh_setfield_gc

    def bh_arraylen_gc(self, a, descr):
        array = a._obj.container
        return array.getlength()

    def bh_setarrayitem_gc(self, a, index, item, descr):
        array = a._obj.container
        array.setitem(index, support.cast_arg(descr.A.OF, item))

    def bh_getarrayitem_gc(self, a, index, descr):
        array = a._obj.container
        return support.cast_result(descr.A.OF, array.getitem(index))

    def bh_getinteriorfield_gc(self, a, index, descr):
        array = a._obj.container
        return support.cast_result(descr.FIELD,
                          getattr(array.getitem(index), descr.fieldname))

    bh_getinteriorfield_gc_f = bh_getinteriorfield_gc
    bh_getinteriorfield_gc_i = bh_getinteriorfield_gc
    bh_getinteriorfield_gc_r = bh_getinteriorfield_gc

    def bh_setinteriorfield_gc(self, a, index, item, descr):
        array = a._obj.container
        setattr(array.getitem(index), descr.fieldname,
                support.cast_arg(descr.FIELD, item))

    bh_setinteriorfield_gc_f = bh_setinteriorfield_gc
    bh_setinteriorfield_gc_r = bh_setinteriorfield_gc
    bh_setinteriorfield_gc_i = bh_setinteriorfield_gc

    def bh_newstr(self, length):
        return lltype.cast_opaque_ptr(llmemory.GCREF,
                                      lltype.malloc(rstr.STR, length))

    def bh_strlen(self, s):
        return s._obj.container.chars.getlength()

    def bh_strgetitem(self, s, item):
        return ord(s._obj.container.chars.getitem(item))

    def bh_strsetitem(self, s, item, v):
        s._obj.container.chars.setitem(item, chr(v))

    def bh_copystrcontent(self, src, dst, srcstart, dststart, length):
        src = lltype.cast_opaque_ptr(lltype.Ptr(rstr.STR), src)
        dst = lltype.cast_opaque_ptr(lltype.Ptr(rstr.STR), dst)
        assert 0 <= srcstart <= srcstart + length <= len(src.chars)
        assert 0 <= dststart <= dststart + length <= len(dst.chars)
        rstr.copy_string_contents(src, dst, srcstart, dststart, length)

    def bh_newunicode(self, length):
        return lltype.cast_opaque_ptr(llmemory.GCREF,
                                      lltype.malloc(rstr.UNICODE, length))

    def bh_unicodelen(self, string):
        return string._obj.container.chars.getlength()

    def bh_unicodegetitem(self, string, index):
        return ord(string._obj.container.chars.getitem(index))

    def bh_unicodesetitem(self, string, index, newvalue):
        string._obj.container.chars.setitem(index, unichr(newvalue))

    def bh_copyunicodecontent(self, src, dst, srcstart, dststart, length):
        src = lltype.cast_opaque_ptr(lltype.Ptr(rstr.UNICODE), src)
        dst = lltype.cast_opaque_ptr(lltype.Ptr(rstr.UNICODE), dst)
        assert 0 <= srcstart <= srcstart + length <= len(src.chars)
        assert 0 <= dststart <= dststart + length <= len(dst.chars)
        rstr.copy_unicode_contents(src, dst, srcstart, dststart, length)

    def bh_new(self, sizedescr):
        return lltype.cast_opaque_ptr(llmemory.GCREF,
                                      lltype.malloc(sizedescr.S))

    def bh_new_with_vtable(self, vtable, descr):
        result = lltype.malloc(descr.S)
        result_as_objptr = lltype.cast_pointer(rclass.OBJECTPTR, result)
        result_as_objptr.typeptr = support.cast_from_int(rclass.CLASSTYPE,
                                                         vtable)
        return lltype.cast_opaque_ptr(llmemory.GCREF, result)

    def bh_new_array(self, length, arraydescr):
        array = lltype.malloc(arraydescr.A, length, zero=True)
        return lltype.cast_opaque_ptr(llmemory.GCREF, array)


class LLFrame(object):
    def __init__(self, cpu, argboxes, args):
        self.env = {}
        self.cpu = cpu
        assert len(argboxes) == len(args)
        for box, arg in zip(argboxes, args):
            self.env[box] = arg
        self.overflow_flag = False

    def lookup(self, arg):
        if isinstance(arg, Const):
            return arg.value
        return self.env[arg]

    def execute(self, operations):
        i = 0
        while True:
            op = operations[i]
            args = [self.lookup(arg) for arg in op.getarglist()]
            self.current_op = op # for label
            try:
                resval = getattr(self, 'execute_' + op.getopname())(op.getdescr(),
                                                                    *args)
            except Jump, j:
                operations, i = self.cpu.known_labels[j.descr]
                label_op = operations[i]
                self.do_renaming(label_op.getarglist(), j.args)
                i += 1
                continue
            except GuardFailed, gf:
                if hasattr(gf.descr, '_llgraph_bridge'):
                    i = 0
                    bridge = gf.descr._llgraph_bridge
                    operations = bridge.operations
                    newargs = [self.env[arg] for arg in
                               self.current_op.getfailargs() if arg is not None]
                    self.do_renaming(bridge.inputargs, newargs)
                    continue
                raise
            if op.result is not None:
                assert resval is not None
                self.env[op.result] = resval
            else:
                assert resval is None
            i += 1

    def _getfailargs(self):
        r = []
        for arg in self.current_op.getfailargs():
            if arg is None:
                r.append(None)
            else:
                r.append(self.env[arg])
        return r

    def do_renaming(self, newargs, oldargs):
        assert len(newargs) == len(oldargs)
        newenv = {}
        for new, old in zip(newargs, oldargs):
            newenv[new] = old
        self.env = newenv

    # -----------------------------------------------------

    def fail_guard(self, descr):
        raise GuardFailed(self._getfailargs(), descr)

    def execute_finish(self, descr, *args):
        raise ExecutionFinished(descr, args)

    def execute_label(self, descr, *args):
        argboxes = self.current_op.getarglist()
        self.do_renaming(argboxes, args)

    def execute_guard_true(self, descr, arg):
        if not arg:
            self.fail_guard(descr)

    def execute_guard_false(self, descr, arg):
        if arg:
            self.fail_guard(descr)

    def execute_guard_value(self, descr, arg1, arg2):
        if arg1 != arg2:
            self.fail_guard(descr)

    def execute_guard_nonnull(self, descr, arg):
        if not arg:
            self.fail_guard(descr)

    def execute_guard_isnull(self, descr, arg):
        if arg:
            self.fail_guard(descr)

    def execute_guard_class(self, descr, arg, klass):
        value = lltype.cast_opaque_ptr(rclass.OBJECTPTR, arg)
        expected_class = llmemory.cast_adr_to_ptr(
            llmemory.cast_int_to_adr(klass),
            rclass.CLASSTYPE)
        if value.typeptr != expected_class:
            self.fail_guard(descr)

    def execute_guard_nonnull_class(self, descr, arg, klass):
        self.execute_guard_nonnull(descr, arg)
        self.execute_guard_class(descr, arg, klass)

    def execute_int_add_ovf(self, _, x, y):
        try:
            z = ovfcheck(x + y)
        except OverflowError:
            ovf = True
            z = 0
        else:
            ovf = False
        self.overflow_flag = ovf
        return z

    def execute_int_sub_ovf(self, _, x, y):
        try:
            z = ovfcheck(x - y)
        except OverflowError:
            ovf = True
            z = 0
        else:
            ovf = False
        self.overflow_flag = ovf
        return z

    def execute_int_mul_ovf(self, _, x, y):
        try:
            z = ovfcheck(x * y)
        except OverflowError:
            ovf = True
            z = 0
        else:
            ovf = False
        self.overflow_flag = ovf
        return z        

    def execute_guard_no_overflow(self, descr):
        if self.overflow_flag:
            self.fail_guard(descr)

    def execute_guard_overflow(self, descr):
        if not self.overflow_flag:
            self.fail_guard(descr)

    def execute_jump(self, descr, *args):
        raise Jump(descr, args)

    def execute_call(self, descr, *args):
        call_args = support.cast_call_args_in_order(args[0], args[1:])
        return self.cpu.call(args[0], descr, call_args)

    def execute_same_as(self, _, x):
        return x

    def execute_debug_merge_point(self, descr, *args):
        pass

    def execute_new_with_vtable(self, _, vtable):
        descr = heaptracker.vtable2descr(self.cpu, vtable)
        return self.cpu.bh_new_with_vtable(vtable, descr)


def _setup():
    def _make_impl_from_blackhole_interp(opname):
        from pypy.jit.metainterp.blackhole import BlackholeInterpreter
        name = 'bhimpl_' + opname.lower()
        try:
            func = BlackholeInterpreter.__dict__[name]
        except KeyError:
            return
        for argtype in func.argtypes:
            if argtype not in ('i', 'r', 'f'):
                return
        #
        def _op_default_implementation(self, descr, *args):
            # for all operations implemented in the blackhole interpreter
            return func(*args)
        #
        _op_default_implementation.func_name = 'execute_' + opname
        return _op_default_implementation

    def _new_execute(opname):
        def execute(self, descr, *args):
            if descr is not None:
                new_args = args + (descr,)
            else:
                new_args = args
            return getattr(self.cpu, 'bh_' + opname)(*new_args)
        execute.func_name = 'execute_' + opname
        return execute

    for k, v in rop.__dict__.iteritems():
        if not k.startswith("_"):
            fname = 'execute_' + k.lower()
            if not hasattr(LLFrame, fname):
                func = _make_impl_from_blackhole_interp(k)
                if func is None:
                    func = _new_execute(k.lower())
                setattr(LLFrame, fname, func)

_setup()
