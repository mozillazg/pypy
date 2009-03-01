import sys
import ctypes
import py
from pypy.rpython.lltypesystem import lltype, llmemory, ll2ctypes, rffi
from pypy.rpython.llinterp import LLInterpreter, LLException
from pypy.rpython.lltypesystem.lloperation import llop
from pypy.rpython.annlowlevel import MixLevelHelperAnnotator
from pypy.rlib.objectmodel import CDefinedIntSymbolic, specialize
from pypy.rlib.objectmodel import we_are_translated, keepalive_until_here
from pypy.annotation import model as annmodel
from pypy.rpython.lltypesystem import rclass
from pypy.jit.metainterp import history
from pypy.jit.metainterp.history import (MergePoint, ResOperation, Box, Const,
     ConstInt, ConstPtr, BoxInt, BoxPtr, ConstAddr)
from pypy.jit.backend.x86.assembler import Assembler386
from pypy.jit.backend.x86 import symbolic

class CPU386(object):
    debug = True

    BOOTSTRAP_TP = lltype.FuncType([lltype.Signed,
                                    lltype.Ptr(rffi.CArray(lltype.Signed))],
                                   lltype.Signed)

    def __init__(self, rtyper, stats, translate_support_code=False):
        self.rtyper = rtyper
        self.stats = stats
        self.translate_support_code = translate_support_code
        if translate_support_code:
            self.mixlevelann = MixLevelHelperAnnotator(rtyper)
        else:
            self.current_interpreter = LLInterpreter(self.rtyper)

            def _store_exception(lle):
                tp_i = self.cast_ptr_to_int(lle.args[0])
                v_i = self.cast_gcref_to_int(lle.args[1])
                self.assembler._exception_data[0] = tp_i
                self.assembler._exception_data[1] = v_i
            
            self.current_interpreter._store_exception = _store_exception
        TP = lltype.GcArray(llmemory.GCREF)
        self.keepalives = []
        self.keepalives_index = 0
        self._bootstrap_cache = {}
        self._guard_list = []
        self._compiled_ops = {}
        self._builtin_implementations = {}
        self.setup()
        self.caught_exception = None
        if rtyper is not None: # for tests
            self.lltype2vtable = rtyper.lltype_to_vtable_mapping()
            self._setup_ovf_error()

    def _setup_ovf_error(self):
        bk = self.rtyper.annotator.bookkeeper
        clsdef = bk.getuniqueclassdef(OverflowError)
        ovferror_repr = rclass.getclassrepr(self.rtyper, clsdef)
        ll_inst = self.rtyper.exceptiondata.get_standard_ll_exc_instance(
            self.rtyper, clsdef)
        self._ovf_error_vtable = self.cast_ptr_to_int(ll_inst.typeptr)
        self._ovf_error_inst = self.cast_ptr_to_int(ll_inst)

    def setup(self):
        self.assembler = Assembler386(self)
        # the generic assembler stub that just performs a return
        if self.translate_support_code:
            mixlevelann = self.mixlevelann
            s_int = annmodel.SomeInteger()

            def failure_recovery_callback(guard_index, frame_addr):
                return self.failure_recovery_callback(guard_index, frame_addr)

            fn = mixlevelann.delayedfunction(failure_recovery_callback,
                                             [s_int, s_int], s_int)
            self.cfunc_failure_recovery = fn
        else:
            import ctypes
            # the ctypes callback function that handles guard failures
            fntype = ctypes.CFUNCTYPE(ctypes.c_long,
                                      ctypes.c_long, ctypes.c_void_p)
            self.cfunc_failure_recovery = fntype(self.failure_recovery_callback)
            self.failure_recovery_func_addr = ctypes.cast(
                        self.cfunc_failure_recovery, ctypes.c_void_p).value

    def get_failure_recovery_func_addr(self):
        if self.translate_support_code:
            fn = self.cfunc_failure_recovery
            return lltype.cast_ptr_to_int(fn)
        else:
            return self.failure_recovery_func_addr

    def failure_recovery_callback(self, guard_index, frame_addr):
        """This function is called back from the assembler code when
        a not-yet-implemented path is followed.  It can either compile
        the extra path and ask the assembler to jump to it, or ask
        the assembler to exit the current function.
        """
        self.assembler.make_sure_mc_exists()
        try:
            del self.keepalives[self.keepalives_index:]
            guard_op = self._guard_list[guard_index]
            if self.debug:
                llop.debug_print(lltype.Void, '.. calling back from',
                                 guard_op, 'to the jit')
            gf = GuardFailed(self, frame_addr, guard_op)
            self.metainterp.handle_guard_failure(gf)
            if self.debug:
                if gf.return_addr == self.assembler.generic_return_addr:
                    llop.debug_print(lltype.Void, 'continuing at generic return address')
                else:
                    llop.debug_print(lltype.Void, 'continuing at',
                                     uhex(gf.return_addr))
            return gf.return_addr
        except Exception, e:
            if not we_are_translated():
                self.caught_exception = sys.exc_info()
            else:
                self.caught_exception = e
            return self.assembler.generic_return_addr

    def set_meta_interp(self, metainterp):
        self.metainterp = metainterp

    def _get_overflow_error(self):
        self.assembler._exception_data[1] = self._ovf_error_inst
        return self._ovf_error_vtable

    def get_exception(self, frame):
        res = self.assembler._exception_data[0]
        self.assembler._exception_data[0] = 0
        if res == 1:
            # it's an overflow error, but we need to do all the dance
            # to get a correct exception
            return self._get_overflow_error()
        return res

    def get_exc_value(self, frame):
        return self.cast_int_to_gcref(self.assembler._exception_data[1])

    def execute_operation(self, opname, valueboxes, result_type):
        # mostly a hack: fall back to compiling and executing the single
        # operation.
        if opname.startswith('#'):
            return None
        key = [opname, result_type]
        for valuebox in valueboxes:
            if isinstance(valuebox, Box):
                key.append(valuebox.type)
            else:
                key.append(repr(valuebox)) # XXX not RPython
        mp = self.get_compiled_single_operation(key, valueboxes)
        res = self.execute_operations_in_new_frame(opname, mp, valueboxes,
                                                   result_type)
        if self.assembler._exception_data[0] != 0:
            TP = lltype.Ptr(rclass.OBJECT_VTABLE)
            TP_V = lltype.Ptr(rclass.OBJECT)
            exc_t_a = self.cast_int_to_adr(self.get_exception(None))
            exc_type = llmemory.cast_adr_to_ptr(exc_t_a, TP)
            exc_v_a = self.get_exc_value(None)
            exc_val = lltype.cast_opaque_ptr(TP_V, exc_v_a)
            # clean up the exception
            self.assembler._exception_data[0] = 0
            raise LLException(exc_type, exc_val)
        return res

    def get_compiled_single_operation(self, key, valueboxes):
        real_key = ','.join([str(k) for k in key])
        try:
            return self._compiled_ops[real_key]
        except KeyError:
            opname = key[0]
            result_type = key[1]
            livevarlist = []
            i = 0
            # clonebox below is necessary, because sometimes we know
            # that the value is constant (ie ArrayDescr), but we're not
            # going to get the contant. So instead we get a box with correct
            # value
            for box in valueboxes:
                if box.type == 'int':
                    box = valueboxes[i].clonebox()
                elif box.type == 'ptr':
                    box = valueboxes[i].clonebox()
                else:
                    raise ValueError(type)
                livevarlist.append(box)
                i += 1
            mp = MergePoint('merge_point', livevarlist, [])
            if result_type == 'void':
                results = []
            elif result_type == 'int':
                results = [history.BoxInt()]
            elif result_type == 'ptr':
                results = [history.BoxPtr()]
            else:
                raise ValueError(result_type)
            operations = [mp,
                          ResOperation(opname, livevarlist, results),
                          ResOperation('return', results, [])]
            if opname.startswith('guard_'):
                operations[1].liveboxes = []
            self.compile_operations(operations, verbose=False)
            self._compiled_ops[real_key] = mp
            return mp

    def compile_operations(self, operations, guard_op=None, verbose=True):
        self.assembler.assemble(operations, guard_op, verbose=verbose)

    def get_bootstrap_code(self, startmp):
        # key is locations of arguments
        key = ','.join([str(i) for i in startmp.arglocs])
        try:
            func = self._bootstrap_cache[key]
        except KeyError:
            arglocs = startmp.arglocs
            addr = self.assembler.assemble_bootstrap_code(arglocs)
            # arguments are as follows - address to jump to,
            # and a list of args
            func = rffi.cast(lltype.Ptr(self.BOOTSTRAP_TP), addr)
            self._bootstrap_cache[key] = func
        return func

    def get_box_value_as_int(self, box):
        if isinstance(box, BoxInt):
            return box.value
        elif isinstance(box, ConstInt):
            return box.value
        elif isinstance(box, BoxPtr):
            self.keepalives.append(box.value)
            return self.cast_gcref_to_int(box.value)
        elif isinstance(box, ConstPtr): 
            self.keepalives.append(box.value)
            return self.cast_gcref_to_int(box.value)
        elif ConstAddr.ever_seen and isinstance(box, ConstAddr):
            return self.cast_adr_to_int(box.value)
        else:
            raise ValueError('get_box_value_as_int, wrong arg')

    def get_valuebox_from_int(self, type, x):
        if type == 'int':
            return history.BoxInt(x)
        elif type == 'ptr':
            return history.BoxPtr(self.cast_int_to_gcref(x))
        else:
            raise ValueError('get_valuebox_from_int: %s' % (type,))

    def execute_operations_in_new_frame(self, name, startmp, valueboxes,
                                        result_type):
        func = self.get_bootstrap_code(startmp)
        # turn all the values into integers
        TP = rffi.CArray(lltype.Signed)
        oldindex = self.keepalives_index
        values_as_int = lltype.malloc(TP, len(valueboxes), flavor='raw')
        for i in range(len(valueboxes)):
            box = valueboxes[i]
            v = self.get_box_value_as_int(box)
            values_as_int[i] = v
        # debug info
        values_repr = ", ".join([str(values_as_int[i]) for i in
                                 range(len(valueboxes))])
        if self.debug:
            llop.debug_print(lltype.Void, 'exec:', name, values_repr)

        self.keepalives_index = len(self.keepalives)
        res = self.execute_call(startmp, func, values_as_int)
        if result_type == 'void':
            if self.debug:
                llop.debug_print(lltype.Void, " => void result")
            res = None
        else:
            if self.debug:
                llop.debug_print(lltype.Void, " => ", res)
            res = self.get_valuebox_from_int(result_type, res)
        keepalive_until_here(valueboxes)
        self.keepalives_index = oldindex
        del self.keepalives[oldindex:]
        return res

    def execute_call(self, startmp, func, values_as_int):
        # help flow objspace
        prev_interpreter = None
        if not self.translate_support_code:
            prev_interpreter = LLInterpreter.current_interpreter
            LLInterpreter.current_interpreter = self.current_interpreter
        res = 0
        try:
            self.caught_exception = None
            res = func(startmp.position, values_as_int)
            self.reraise_caught_exception()
        finally:
            if not self.translate_support_code:
                LLInterpreter.current_interpreter = prev_interpreter
            lltype.free(values_as_int, flavor='raw')
        return res

    def reraise_caught_exception(self):
        # this helper is in its own function so that the call to it
        # shows up in traceback -- useful to avoid confusing tracebacks,
        # which are typical when using the 3-arguments raise.
        if self.caught_exception is not None:
            if not we_are_translated():
                exc, val, tb = self.caught_exception
                raise exc, val, tb
            else:
                exc = self.caught_exception
                raise exc

    def make_guard_index(self, guard_op):
        index = len(self._guard_list)
        self._guard_list.append(guard_op)
        return index

    def convert_box_to_int(self, valuebox):
        if isinstance(valuebox, ConstInt):
            return valuebox.value
        elif isinstance(valuebox, BoxInt):
            return valuebox.value
        elif isinstance(valuebox, BoxPtr):
            x = self.cast_gcref_to_int(valuebox.value)
            self.keepalives.append(valuebox.value)
            return x
        elif isinstance(valuebox, ConstPtr):
            x = self.cast_gcref_to_int(valuebox.value)
            self.keepalives.append(valuebox.value)
            return x
        else:
            raise ValueError(valuebox.type)

    def getvaluebox(self, frameadr, guard_op, argindex):
        # XXX that's plain stupid, do we care about the return value???
        box = [b for b in guard_op.liveboxes if isinstance(b, Box)][argindex]
        frame = getframe(frameadr)
        pos = guard_op.stacklocs[argindex]
        intvalue = frame[pos]
        if isinstance(box, history.BoxInt):
            return history.BoxInt(intvalue)
        elif isinstance(box, history.BoxPtr):
            return history.BoxPtr(self.cast_int_to_gcref(intvalue))
        else:
            raise AssertionError('getvalue: box = %s' % (box,))

    def setvaluebox(self, frameadr, mp, argindex, valuebox):
        frame = getframe(frameadr)
        frame[mp.stacklocs[argindex]] = self.convert_box_to_int(valuebox)

    def sizeof(self, S):
        return symbolic.get_size(S)

    numof = sizeof
    addresssuffix = str(symbolic.get_size(llmemory.Address))

    def itemoffsetof(self, A):
        basesize, itemsize, ofs_length = symbolic.get_array_token(A)
        return basesize

    def arraylengthoffset(self, A):
        basesize, itemsize, ofs_length = symbolic.get_array_token(A)
        return ofs_length

    @staticmethod
    def cast_adr_to_int(x):
        res = ll2ctypes.cast_adr_to_int(x)
        return res

    @staticmethod
    def cast_ptr_to_int(x):
        adr = llmemory.cast_ptr_to_adr(x)
        return CPU386.cast_adr_to_int(adr)

    @staticmethod
    def arraydescrof(A):
        assert isinstance(A, lltype.GcArray)
        basesize, itemsize, ofs_length = symbolic.get_array_token(A)
        assert ofs_length == 0
        counter = 0
        while itemsize != 1:
            itemsize >>= 1
            counter += 1
        return basesize + counter * 0x10000

    @staticmethod
    def fielddescrof(S, fieldname):
        ofs, size = symbolic.get_field_token(S, fieldname)
        val = (size << 16) + ofs
        if (isinstance(getattr(S, fieldname), lltype.Ptr) and
            getattr(S, fieldname).TO._gckind == 'gc'):
            return ~val
        return val

    @staticmethod
    def typefor(fielddesc):
        if fielddesc < 0:
            return "ptr"
        return "int"

    @staticmethod
    def cast_int_to_adr(x):
        return llmemory.cast_ptr_to_adr(rffi.cast(llmemory.GCREF, x))

    def cast_gcref_to_int(self, x):
        return rffi.cast(lltype.Signed, x)

    def cast_int_to_gcref(self, x):
        return rffi.cast(llmemory.GCREF, x)

DEFINED_INT_VALUE = {
    'MALLOC_ZERO_FILLED': 1,   # using Boehm for now
    }

def uhex(x):
    if we_are_translated():
        return hex(x)
    else:
        if x < 0:
            x += 0x100000000
        return hex(x)

class GuardFailed(object):
    def __init__(self, cpu, frame, guard_op):
        self.cpu = cpu
        self.frame = frame
        self.guard_op = guard_op

    def make_ready_for_return(self, return_value_box):
        self.cpu.assembler.make_sure_mc_exists()
        if return_value_box is not None:
            frame = getframe(self.frame)
            frame[0] = self.cpu.convert_box_to_int(return_value_box)
        self.return_addr = self.cpu.assembler.generic_return_addr

    def make_ready_for_continuing_at(self, merge_point):
        # we need to make sure here that return_addr points to a code
        # that is ready to grab coorect values
        self.return_addr = merge_point.comeback_bootstrap_addr

def getframe(frameadr):
    return rffi.cast(rffi.CArrayPtr(lltype.Signed), frameadr)

CPU = CPU386

