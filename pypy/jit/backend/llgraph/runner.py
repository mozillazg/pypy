"""
Minimal-API wrapper around the llinterpreter to run operations.
"""

from pypy.rpython.lltypesystem import lltype, llmemory, rclass
from pypy.jit.metainterp import history
from pypy.jit.metainterp.resoperation import ResOperation, rop
from pypy.jit.backend.llgraph import llimpl, symbolic


class MiniStats:
    pass


class CPU(object):

    def __init__(self, rtyper, stats=None, translate_support_code=False,
                 annmixlevel=None):
        self.rtyper = rtyper
        self.translate_support_code = translate_support_code
        self.jumptarget2loop = {}
        self.guard_ops = []
        self.compiled_single_ops = {}
        self.stats = stats or MiniStats()
        self.stats.exec_counters = {}
        self.stats.exec_jumps = 0
        self.memo_cast = llimpl.new_memo_cast()
        llimpl._stats = self.stats
        llimpl._rtyper = self.rtyper
        if translate_support_code:
            self.mixlevelann = annmixlevel
        self.fielddescrof_vtable = self.fielddescrof(rclass.OBJECT, 'typeptr')

    def set_meta_interp(self, metainterp):
        self.metainterp = metainterp    # to handle guard failures

    def compile_operations(self, operations, from_guard=None):
        """In a real assembler backend, this should assemble the given
        list of operations.  Here we just generate a similar LoopOrBridge
        instance.  The code here is RPython, whereas the code in llimpl
        is not.
        """

        c = llimpl.compile_start()
        var2index = {}
        for i in range(len(operations[0].args)):
            box = operations[0].args[i]
            if isinstance(box, history.BoxInt):
                var2index[box] = llimpl.compile_start_int_var(c)
            elif isinstance(box, history.BoxPtr):
                var2index[box] = llimpl.compile_start_ptr_var(c)
            elif isinstance(box, history.Const):
                pass     # accept anything and ignore it
            else:
                raise Exception("box is: %r" % (box,))
        j = 0
        for i in range(len(operations)):
            op = operations[i]
            #if op.opname[0] == '#':
            #    continue
            op._compiled = c
            op._opindex = j
            j += 1
            llimpl.compile_add(c, op.opnum)
            for x in op.args:
                if isinstance(x, history.Box):
                    llimpl.compile_add_var(c, var2index[x])
                elif isinstance(x, history.ConstInt):
                    llimpl.compile_add_int_const(c, x.value)
                elif isinstance(x, history.ConstPtr):
                    llimpl.compile_add_ptr_const(c, x.value)
                elif isinstance(x, history.ConstAddr):
                    llimpl.compile_add_int_const(c, x.getint())
                else:
                    raise Exception("%s args contain: %r" % (op.getopname(),
                                                             x))
            x = op.result
            if x is not None:
                if isinstance(x, history.BoxInt):
                    var2index[x] = llimpl.compile_add_int_result(c)
                elif isinstance(x, history.BoxPtr):
                    var2index[x] = llimpl.compile_add_ptr_result(c)
                else:
                    raise Exception("%s.result contain: %r" % (op.getopname(),
                                                               x))
            if op.jump_target is not None:
                loop_target, loop_target_index = \
                                           self.jumptarget2loop[op.jump_target]
                llimpl.compile_add_jump_target(c, loop_target,
                                                  loop_target_index)
            if op.is_guard():
                llimpl.compile_add_failnum(c, len(self.guard_ops))
                self.guard_ops.append(op)
                for box in op.liveboxes:
                    if isinstance(box, history.Box):
                        llimpl.compile_add_livebox(c, var2index[box])
            if op.opnum == rop.MERGE_POINT:
                self.jumptarget2loop[op] = c, i
        if from_guard is not None:
            llimpl.compile_from_guard(c, from_guard._compiled,
                                         from_guard._opindex)

    def execute_operations_in_new_frame(self, name, merge_point, valueboxes,
                                        result_type=None):
        """Perform a 'call' to the given merge point, i.e. create
        a new CPU frame and use it to execute the operations that
        follow the merge point.
        """
        assert result_type is None or isinstance(result_type, str)
        frame = llimpl.new_frame(self.memo_cast)
        llimpl.frame_clear(frame, merge_point._compiled, merge_point._opindex)
        for box in valueboxes:
            if isinstance(box, history.BoxInt):
                llimpl.frame_add_int(frame, box.value)
            elif isinstance(box, history.BoxPtr):
                llimpl.frame_add_ptr(frame, box.value)
            elif isinstance(box, history.ConstInt):
                llimpl.frame_add_int(frame, box.value)
            elif isinstance(box, history.ConstPtr):
                llimpl.frame_add_ptr(frame, box.value)
            else:
                raise Exception("bad box in valueboxes: %r" % (box,))
        return self.loop(frame)

    def execute_operation(self, opnum, valueboxes, result_type):
        """Execute a single operation, returning the result.
        Mostly a hack: falls back to interpreting a complete bridge
        containing the operation.
        """
        #if opname[0] == '#':
        #    return None
        c = self.get_compiled_single_op(opnum, valueboxes, result_type)
        frame = llimpl.new_frame(self.memo_cast)
        llimpl.frame_clear(frame, c, 0)
        for box in valueboxes:
            if box.type == 'int':
                llimpl.frame_add_int(frame, box.getint())
            elif box.type == 'ptr':
                llimpl.frame_add_ptr(frame, box.getptr_base())
            else:
                raise Exception("bad box in valueboxes: %r" % (box,))
        res = llimpl.frame_execute(frame)
        assert res == -1
        if result_type == 'int':
            return history.BoxInt(llimpl.frame_int_getresult(frame))
        elif result_type == 'ptr':
            return history.BoxPtr(llimpl.frame_ptr_getresult(frame))
        else:
            return None

    def get_compiled_single_op(self, opnum, valueboxes, result_type):
        assert isinstance(opnum, int)
        keylist = self.compiled_single_ops.setdefault((opnum, result_type),
                                                      [])
        types = [valuebox.type for valuebox in valueboxes]
        for key, impl in keylist:
            if len(key) == len(types):
                for i in range(len(key)):
                    if key[i] is not types[i]:
                        break
                else:
                    return impl
        valueboxes = []
        for type in types:
            if type == 'int':
                valueboxes.append(history.BoxInt())
            elif type == 'ptr':
                valueboxes.append(history.BoxPtr())
            else:
                raise AssertionError('valuebox type=%s' % (type,))
        if result_type == 'void':
            resbox = None
        elif result_type == 'int':
            resbox = history.BoxInt()
        elif result_type == 'ptr':
            resbox = history.BoxPtr()
        else:
            raise AssertionError(result_type)
        resboxes = []
        if resbox is not None:
            resboxes.append(resbox)
        operations = [
            ResOperation(rop.MERGE_POINT, valueboxes, None),
            ResOperation(opnum, valueboxes, resbox),
            ResOperation(rop.RETURN, resboxes, None),
            ]
        self.compile_operations(operations)
        impl = operations[0]._compiled
        keylist.append((types, impl))
        return impl

    def loop(self, frame):
        """Execute a loop.  When the loop fails, ask the metainterp for more.
        """
        while True:
            guard_index = llimpl.frame_execute(frame)
            guard_op = self.guard_ops[guard_index]
            assert isinstance(lltype.typeOf(frame), lltype.Ptr)
            gf = GuardFailed(frame, guard_op)
            self.metainterp.handle_guard_failure(gf)
            if gf.returns:
                return gf.retbox

    def getrealbox(self, guard_op, argindex):
        box = None
        i = 0
        j = argindex
        while j >= 0:
            box = guard_op.liveboxes[i]
            i += 1
            if isinstance(box, history.Box):
                j -= 1
        return box

    def getvaluebox(self, frame, guard_op, argindex):
        box = self.getrealbox(guard_op, argindex)
        if isinstance(box, history.BoxInt):
            value = llimpl.frame_int_getvalue(frame, argindex)
            return history.BoxInt(value)
        elif isinstance(box, history.BoxPtr):
            value = llimpl.frame_ptr_getvalue(frame, argindex)
            return history.BoxPtr(value)
        else:
            raise AssertionError('getvalue: box = %s' % (box,))

    def setvaluebox(self, frame, guard_op, argindex, valuebox):
        if isinstance(valuebox, history.BoxInt):
            llimpl.frame_int_setvalue(frame, argindex, valuebox.value)
        elif isinstance(valuebox, history.BoxPtr):
            llimpl.frame_ptr_setvalue(frame, argindex, valuebox.value)
        elif isinstance(valuebox, history.ConstInt):
            llimpl.frame_int_setvalue(frame, argindex, valuebox.value)
        elif isinstance(valuebox, history.ConstPtr):
            llimpl.frame_ptr_setvalue(frame, argindex, valuebox.value)
        elif isinstance(valuebox, history.ConstAddr):
            llimpl.frame_int_setvalue(frame, argindex, valuebox.getint())
        else:
            raise AssertionError('setvalue: valuebox = %s' % (valuebox,))

    def get_exception(self, frame):
        return self.cast_adr_to_int(llimpl.frame_exception(frame))

    def get_exc_value(self, frame):
        return llimpl.frame_exc_value(frame)

    @staticmethod
    def sizeof(S):
        return symbolic.get_size(S)

    @staticmethod
    def numof(S):
        return 4

    addresssuffix = '4'

    @staticmethod
    def fielddescrof(S, fieldname):
        ofs, size = symbolic.get_field_token(S, fieldname)
        token = history.getkind(getattr(S, fieldname))
        if token == 'ptr':
            bit = 1
        else:
            bit = 0
        return ofs*2 + bit

    @staticmethod
    def arraydescrof(A):
        assert isinstance(A, lltype.GcArray)
        size = symbolic.get_size(A)
        token = history.getkind(A.OF)
        if token == 'ptr':
            bit = 1
        else:
            bit = 0
        return size*2 + bit

    @staticmethod
    def calldescrof(ARGS, RESULT):
        if RESULT is lltype.Void:
            return -1
        token = history.getkind(RESULT)
        if token == 'ptr':
            return 1
        else:
            return 0

    @staticmethod
    def typefor(fielddesc):
        if fielddesc == -1:
            return 'void'
        if fielddesc % 2:
            return 'ptr'
        return 'int'

    @staticmethod
    def itemoffsetof(A):
        basesize, itemsize, ofs_length = symbolic.get_array_token(A)
        return basesize

    @staticmethod
    def arraylengthoffset(A):
        basesize, itemsize, ofs_length = symbolic.get_array_token(A)
        return ofs_length

    def cast_adr_to_int(self, adr):
        return llimpl.cast_adr_to_int(self.memo_cast, adr)

    def cast_int_to_adr(self, int):
        return llimpl.cast_int_to_adr(self.memo_cast, int)

    # ---------- the backend-dependent operations ----------

    def do_arraylen_gc(self, args):
        array = args[0].getptr_base()
        return history.BoxInt(llimpl.do_arraylen_gc(array))

    def do_strlen(self, args):
        string = args[0].getptr_base()
        return history.BoxInt(llimpl.do_strlen(string))

    def do_strgetitem(self, args):
        string = args[0].getptr_base()
        index = args[1].getint()
        return history.BoxInt(llimpl.do_strgetitem(string, index))

    def do_getarrayitem_gc(self, args):
        array = args[0].getptr_base()
        arraydescr = args[1].getint()
        index = args[2].getint()
        if self.typefor(arraydescr) == 'ptr':
            return history.BoxPtr(llimpl.do_getarrayitem_gc_ptr(array, index))
        else:
            return history.BoxInt(llimpl.do_getarrayitem_gc_int(array, index,
                                                               self.memo_cast))

    def do_getfield_gc(self, args):
        struct = args[0].getptr_base()
        fielddescr = args[1].getint()
        if self.typefor(fielddescr) == 'ptr':
            return history.BoxPtr(llimpl.do_getfield_gc_ptr(struct,
                                                            fielddescr))
        else:
            return history.BoxInt(llimpl.do_getfield_gc_int(struct,
                                                            fielddescr,
                                                            self.memo_cast))

    def do_getfield_raw(self, args):
        struct = self.cast_int_to_adr(args[0].getint())
        fielddescr = args[1].getint()
        if self.typefor(fielddescr) == 'ptr':
            return history.BoxPtr(llimpl.do_getfield_raw_ptr(struct,
                                                             fielddescr))
        else:
            return history.BoxInt(llimpl.do_getfield_raw_int(struct,
                                                             fielddescr,
                                                             self.memo_cast))

    def do_new(self, args):
        size = args[0].getint()
        return history.BoxPtr(llimpl.do_new(size))

    def do_new_with_vtable(self, args):
        size = args[0].getint()
        vtable = args[1].getint()
        result = llimpl.do_new(size)
        llimpl.do_setfield_gc_int(result, self.fielddescrof_vtable, vtable,
                                  self.memo_cast)
        return history.BoxPtr(result)

    def do_new_array(self, args):
        size = args[0].getint()
        count = args[1].getint()
        return history.BoxPtr(llimpl.do_new_array(size, count))

    def do_setarrayitem_gc(self, args):
        array = args[0].getptr_base()
        arraydescr = args[1].getint()
        index = args[2].getint()
        if self.typefor(arraydescr) == 'ptr':
            newvalue = args[3].getptr_base()
            llimpl.do_setarrayitem_gc_ptr(array, index, newvalue)
        else:
            newvalue = args[3].getint()
            llimpl.do_setarrayitem_gc_int(array, index, newvalue,
                                          self.memo_cast)

    def do_setfield_gc(self, args):
        struct = args[0].getptr_base()
        fielddescr = args[1].getint()
        if self.typefor(fielddescr) == 'ptr':
            newvalue = args[2].getptr_base()
            llimpl.do_setfield_gc_ptr(struct, fielddescr, newvalue)
        else:
            newvalue = args[2].getint()
            llimpl.do_setfield_gc_int(struct, fielddescr, newvalue,
                                      self.memo_cast)

    def do_setfield_raw(self, args):
        struct = self.cast_int_to_adr(args[0].getint())
        fielddescr = args[1].getint()
        if self.typefor(fielddescr) == 'ptr':
            newvalue = args[2].getptr_base()
            llimpl.do_setfield_raw_ptr(struct, fielddescr, newvalue)
        else:
            newvalue = args[2].getint()
            llimpl.do_setfield_raw_int(struct, fielddescr, newvalue,
                                       self.memo_cast)


class GuardFailed(object):
    returns = False

    def __init__(self, frame, guard_op):
        self.frame = frame
        self.guard_op = guard_op

    def make_ready_for_return(self, retbox):
        self.returns = True
        self.retbox = retbox

    def make_ready_for_continuing_at(self, merge_point):
        llimpl.frame_clear(self.frame, merge_point._compiled,
                           merge_point._opindex)
        self.merge_point = merge_point
