from pypy.jit.metainterp import history, compile


class AbstractCPU(object):
    supports_floats = False
    # assembler_helper_ptr - a pointer to helper to call after a direct
    #                        assembler call
    portal_calldescr = None
    done_with_this_frame_int_v = -1

    def __init__(self):
        self.fail_descr_list = []

    def get_fail_descr_number(self, descr):
        assert isinstance(descr, history.AbstractFailDescr)
        n = descr.index
        if n < 0:
            lst = self.fail_descr_list
            n = len(lst)
            lst.append(descr)
            descr.index = n
        return n

    def get_fail_descr_from_number(self, n):
        return self.fail_descr_list[n]

    def setup_once(self):
        """Called once by the front-end when the program starts."""
        pass

    def finish_once(self):
        """Called once by the front-end when the program stops."""
        pass


    def compile_loop(self, inputargs, operations, looptoken):
        """Assemble the given loop.
        Extra attributes should be put in the LoopToken to
        point to the compiled loop in assembler.
        """
        raise NotImplementedError

    def compile_bridge(self, faildescr, inputargs, operations):
        """Assemble the bridge.
        The FailDescr is the descr of the original guard that failed.
        """
        raise NotImplementedError    

    def execute_token(self, looptoken):
        """Execute the generated code referenced by the looptoken.
        Returns the descr of the last executed operation: either the one
        attached to the failing guard, or the one attached to the FINISH.
        Use set_future_value_xxx() before, and get_latest_value_xxx() after.
        """
        raise NotImplementedError

    def set_future_value_int(self, index, intvalue):
        """Set the value for the index'th argument for the loop to run."""
        raise NotImplementedError

    def set_future_value_float(self, index, floatvalue):
        """Set the value for the index'th argument for the loop to run."""
        raise NotImplementedError

    def set_future_value_ref(self, index, objvalue):
        """Set the value for the index'th argument for the loop to run."""
        raise NotImplementedError

    def get_latest_value_int(self, index):
        """Returns the value for the index'th argument to the
        last executed operation (from 'fail_args' if it was a guard,
        or from 'args' if it was a FINISH).  Returns an int."""
        raise NotImplementedError

    def get_latest_value_float(self, index):
        """Returns the value for the index'th argument to the
        last executed operation (from 'fail_args' if it was a guard,
        or from 'args' if it was a FINISH).  Returns a float."""
        raise NotImplementedError

    def get_latest_value_ref(self, index):
        """Returns the value for the index'th argument to the
        last executed operation (from 'fail_args' if it was a guard,
        or from 'args' if it was a FINISH).  Returns a ptr or an obj."""
        raise NotImplementedError

    def get_latest_force_token(self):
        """After a GUARD_NOT_FORCED fails, this function returns the
        same FORCE_TOKEN result as the one in the just-failed loop."""
        raise NotImplementedError

    def make_boxes_from_latest_value(self, faildescr):
        """Build a list of Boxes (and None for holes) that contains
        the current values, as would be returned by calls to
        get_latest_value_xxx()."""
        raise NotImplementedError

    def get_exception(self):
        raise NotImplementedError

    def get_exc_value(self):
        raise NotImplementedError

    def clear_exception(self):
        raise NotImplementedError

    def get_overflow_error(self):
        raise NotImplementedError

    def get_zero_division_error(self):
        raise NotImplementedError

    @staticmethod
    def sizeof(S):
        raise NotImplementedError

    @staticmethod
    def sizevtableof(S, vtable):
        raise NotImplementedError

    @staticmethod
    def fielddescrof(S, fieldname):
        """Return the Descr corresponding to field 'fieldname' on the
        structure 'S'.  It is important that this function (at least)
        caches the results."""
        raise NotImplementedError

    @staticmethod
    def arraydescrof(A):
        raise NotImplementedError

    @staticmethod
    def calldescrof(FUNC, ARGS, RESULT):
        # FUNC is the original function type, but ARGS is a list of types
        # with Voids removed
        raise NotImplementedError

    @staticmethod
    def methdescrof(SELFTYPE, methname):
        # must return a subclass of history.AbstractMethDescr
        raise NotImplementedError

    @staticmethod
    def typedescrof(TYPE):
        raise NotImplementedError

    #def cast_adr_to_int(self, adr):
    #    raise NotImplementedError

    #def cast_int_to_adr(self, int):
    #    raise NotImplementedError

    # ---------- the backend-dependent operations ----------

    # lltype specific operations
    # --------------------------
    
    def bh_getfield_gc_i(self, struct, fielddescr):
        raise NotImplementedError
    def bh_getfield_gc_c(self, struct, fielddescr):
        raise NotImplementedError
    def bh_getfield_gc_u(self, struct, fielddescr):
        raise NotImplementedError
    def bh_getfield_gc_r(self, struct, fielddescr):
        raise NotImplementedError
    def bh_getfield_gc_f(self, struct, fielddescr):
        raise NotImplementedError

    def bh_getfield_raw_i(self, struct, fielddescr):
        raise NotImplementedError
    def bh_getfield_raw_c(self, struct, fielddescr):
        raise NotImplementedError
    def bh_getfield_raw_u(self, struct, fielddescr):
        raise NotImplementedError
    def bh_getfield_raw_r(self, struct, fielddescr):
        raise NotImplementedError
    def bh_getfield_raw_f(self, struct, fielddescr):
        raise NotImplementedError

    def bh_new(self, sizedescr):
        raise NotImplementedError
    def bh_new_with_vtable(self, sizevtabledescr):
        raise NotImplementedError
    def bh_new_array(self, arraydescr, length):
        raise NotImplementedError

    def bh_classof(self, struct):
        raise NotImplementedError

    def bh_setarrayitem_gc_i(self, arraydescr, array, index, newvalue):
        raise NotImplementedError
    def bh_setarrayitem_gc_r(self, arraydescr, array, index, newvalue):
        raise NotImplementedError
    def bh_setarrayitem_gc_f(self, arraydescr, array, index, newvalue):
        raise NotImplementedError

    def bh_setfield_gc_i(self, struct, fielddescr, newvalue):
        raise NotImplementedError
    def bh_setfield_gc_c(self, struct, fielddescr, newvalue):
        raise NotImplementedError
    def bh_setfield_gc_u(self, struct, fielddescr, newvalue):
        raise NotImplementedError
    def bh_setfield_gc_r(self, struct, fielddescr, newvalue):
        raise NotImplementedError
    def bh_setfield_gc_f(self, struct, fielddescr, newvalue):
        raise NotImplementedError

    def bh_setfield_raw_i(self, struct, fielddescr, newvalue):
        raise NotImplementedError
    def bh_setfield_raw_c(self, struct, fielddescr, newvalue):
        raise NotImplementedError
    def bh_setfield_raw_u(self, struct, fielddescr, newvalue):
        raise NotImplementedError
    def bh_setfield_raw_r(self, struct, fielddescr, newvalue):
        raise NotImplementedError
    def bh_setfield_raw_f(self, struct, fielddescr, newvalue):
        raise NotImplementedError

    def bh_call_i(self, func, calldescr, args_i, args_r, args_f):
        raise NotImplementedError
    def bh_call_r(self, func, calldescr, args_i, args_r, args_f):
        raise NotImplementedError
    def bh_call_f(self, func, calldescr, args_i, args_r, args_f):
        raise NotImplementedError
    def bh_call_v(self, func, calldescr, args_i, args_r, args_f):
        raise NotImplementedError

    def bh_cast_ptr_to_int(self, ptr):
        raise NotImplementedError

    def force(self, force_token):
        raise NotImplementedError
