from pypy.rlib.objectmodel import we_are_translated, specialize
from pypy.rpython.lltypesystem.llmemory import GCREF
from pypy.rpython.lltypesystem.lltype import typeOf
from pypy.jit.codewriter import longlong
from pypy.rlib.objectmodel import compute_identity_hash

INT   = 'i'
REF   = 'r'
FLOAT = 'f'
STRUCT = 's'
VOID  = 'v'

def create_resop_dispatch(opnum, result, args, descr=None):
    cls = opclasses[opnum]
    if cls.NUMARGS == 0:
        return create_resop_0(opnum, result, descr)
    elif cls.NUMARGS == 1:
        return create_resop_1(opnum, result, args[0], descr)
    elif cls.NUMARGS == 2:
        return create_resop_2(opnum, result, args[0], args[1], descr)
    elif cls.NUMARGS == 3:
        return create_resop_1(opnum, result, args[0], args[1], args[2],
                              args[3], descr)
    else:
        return create_resop(opnum, result, args, descr)

@specialize.arg(0)
def create_resop(opnum, result, args, descr=None):
    cls = opclasses[opnum]
    assert cls.NUMARGS == -1
    if cls.is_always_pure():
        for arg in args:
            if not arg.is_constant():
                break
        else:
            return cls.wrap_constant(result)
    if result is None:
        op = cls()
    else:
        op = cls(result)
    op.initarglist(args)
    if descr is not None:
        assert isinstance(op, ResOpWithDescr)
        op.setdescr(descr)
    return op

@specialize.arg(0)
def create_resop_0(opnum, result, descr=None):
    cls = opclasses[opnum]
    assert cls.NUMARGS == 0
    if result is None:
        op = cls()
    else:
        op = cls(result)
    if descr is not None:
        assert isinstance(op, ResOpWithDescr)
        op.setdescr(descr)
    return op

@specialize.arg(0)
def create_resop_1(opnum, result, arg0, descr=None):
    cls = opclasses[opnum]
    assert cls.NUMARGS == 1
    if cls.is_always_pure():
        if arg0.is_constant():
            return cls.wrap_constant(result)
    if result is None:
        op = cls()
    else:
        op = cls(result)
    op._arg0 = arg0
    if descr is not None:
        assert isinstance(op, ResOpWithDescr)
        op.setdescr(descr)
    return op

@specialize.arg(0)
def create_resop_2(opnum, result, arg0, arg1, descr=None):
    cls = opclasses[opnum]
    assert cls.NUMARGS == 2
    if cls.is_always_pure():
        if arg0.is_constant() and arg1.is_constant():
            return cls.wrap_constant(result)
    if result is None:
        op = cls()
    else:
        op = cls(result)
    op._arg0 = arg0
    op._arg1 = arg1
    if descr is not None:
        assert isinstance(op, ResOpWithDescr)
        op.setdescr(descr)
    return op

@specialize.arg(0)
def create_resop_3(opnum, result, arg0, arg1, arg2, descr=None):
    cls = opclasses[opnum]
    assert cls.NUMARGS == 3
    if cls.is_always_pure():
        if arg0.is_constant() and arg1.is_constant() and arg2.is_constant():
            return cls.wrap_constant(result)
    if result is None:
        op = cls()
    else:
        op = cls(result)
    op._arg0 = arg0
    op._arg1 = arg1
    op._arg2 = arg2
    if descr is not None:
        assert isinstance(op, ResOpWithDescr)
        op.setdescr(descr)
    return op

def copy_and_change(self, opnum, args=None, result=None, descr=None):
    "shallow copy: the returned operation is meant to be used in place of self"
    if args is None:
        args = self.getarglist()
    if result is None:
        result = self.result
    if descr is None:
        descr = self.getdescr()
    newop = ResOperation(opnum, args, result, descr)
    return newop

class AbstractValue(object):
    __slots__ = ()

    def getint(self):
        raise NotImplementedError

    def getfloatstorage(self):
        raise NotImplementedError

    def getfloat(self):
        return longlong.getrealfloat(self.getfloatstorage())

    def getlonglong(self):
        assert longlong.supports_longlong
        return self.getfloatstorage()

    def getref_base(self):
        raise NotImplementedError

    def getref(self, TYPE):
        raise NotImplementedError
    getref._annspecialcase_ = 'specialize:arg(1)'

    def _get_hash_(self):
        return compute_identity_hash(self)

    # XXX the interface below has to be revisited

    def clonebox(self):
        raise NotImplementedError

    def constbox(self):
        raise NotImplementedError

    def nonconstbox(self):
        raise NotImplementedError

    def getaddr(self):
        raise NotImplementedError

    def sort_key(self):
        raise NotImplementedError

    def nonnull(self):
        raise NotImplementedError

    def repr_rpython(self):
        return '%s' % self

    def _get_str(self):
        raise NotImplementedError

    def same_box(self, other):
        return self is other

    def is_constant(self):
        return False

class AbstractResOp(AbstractValue):
    """The central ResOperation class, representing one operation."""

    # debug
    name = ""
    pc = 0
    opnum = 0

    @classmethod
    def getopnum(cls):
        return cls.opnum

    # methods implemented by the arity mixins
    # ---------------------------------------

    def initarglist(self, args):
        "This is supposed to be called only just after the ResOp has been created"
        raise NotImplementedError

    def getarglist(self):
        raise NotImplementedError

    def getarg(self, i):
        raise NotImplementedError

    def setarg(self, i, box):
        raise NotImplementedError

    def numargs(self):
        raise NotImplementedError


    # methods implemented by GuardResOp
    # ---------------------------------

    def getfailargs(self):
        return None

    def setfailargs(self, fail_args):
        raise NotImplementedError

    # methods implemented by ResOpWithDescr
    # -------------------------------------

    def getdescr(self):
        return None

    def getdescrclone(self):
        return None

    def setdescr(self, descr):
        raise NotImplementedError

    def cleardescr(self):
        pass

    # common methods
    # --------------

    def __repr__(self):
        try:
            return self.repr()
        except NotImplementedError:
            return object.__repr__(self)

    def repr(self, graytext=False):
        # RPython-friendly version
        resultrepr = self.getresultrepr()
        if resultrepr is not None:
            sres = '%s = ' % (resultrepr,)
        else:
            sres = ''
        if self.name:
            prefix = "%s:%s   " % (self.name, self.pc)
            if graytext:
                prefix = "\f%s\f" % prefix
        else:
            prefix = ""
        args = self.getarglist()
        descr = self.getdescr()
        if descr is None or we_are_translated():
            return '%s%s%s(%s)' % (prefix, sres, self.getopname(),
                                 ', '.join([str(a) for a in args]))
        else:
            return '%s%s%s(%s, descr=%r)' % (prefix, sres, self.getopname(),
                                             ', '.join([str(a) for a in args]), descr)

    @classmethod
    def getopname(cls):
        try:
            return opname[cls.getopnum()].lower()
        except KeyError:
            return '<%d>' % cls.getopnum()

    @classmethod
    def is_guard(cls):
        return rop._GUARD_FIRST <= cls.getopnum() <= rop._GUARD_LAST

    @classmethod
    def is_foldable_guard(cls):
        return rop._GUARD_FOLDABLE_FIRST <= cls.getopnum() <= rop._GUARD_FOLDABLE_LAST

    @classmethod
    def is_guard_exception(cls):
        return (cls.getopnum() == rop.GUARD_EXCEPTION or
                cls.getopnum() == rop.GUARD_NO_EXCEPTION)

    @classmethod
    def is_guard_overflow(cls):
        return (cls.getopnum() == rop.GUARD_OVERFLOW or
                cls.getopnum() == rop.GUARD_NO_OVERFLOW)

    @classmethod
    def is_always_pure(cls):
        return rop._ALWAYS_PURE_FIRST <= cls.getopnum() <= rop._ALWAYS_PURE_LAST

    @classmethod
    def has_no_side_effect(cls):
        return rop._NOSIDEEFFECT_FIRST <= cls.getopnum() <= rop._NOSIDEEFFECT_LAST

    @classmethod
    def can_raise(cls):
        return rop._CANRAISE_FIRST <= cls.getopnum() <= rop._CANRAISE_LAST

    @classmethod
    def is_malloc(cls):
        # a slightly different meaning from can_malloc
        return rop._MALLOC_FIRST <= cls.getopnum() <= rop._MALLOC_LAST

    @classmethod
    def can_malloc(cls):
        return cls.is_call() or cls.is_malloc()

    @classmethod
    def is_call(cls):
        return rop._CALL_FIRST <= cls.getopnum() <= rop._CALL_LAST

    @classmethod
    def is_ovf(cls):
        return rop._OVF_FIRST <= cls.getopnum() <= rop._OVF_LAST

    @classmethod
    def is_comparison(cls):
        return cls.is_always_pure() and cls.returns_bool_result()

    @classmethod
    def is_final(cls):
        return rop._FINAL_FIRST <= cls.getopnum() <= rop._FINAL_LAST

    @classmethod
    def returns_bool_result(cls):
        opnum = cls.getopnum()
        if we_are_translated():
            assert opnum >= 0
        elif opnum < 0:
            return False     # for tests
        return opboolresult[opnum]

class ResOpNone(object):
    _mixin_ = True
    type = VOID
    
    def __init__(self):
        pass # no return value

    def getresult(self):
        return None

    def getresultrepr(self):
        return None

class ResOpInt(object):
    _mixin_ = True
    type = INT
    
    def __init__(self, intval):
        assert isinstance(intval, int)
        self.intval = intval

    def getint(self):
        return self.intval
    getresult = getint

    def getresultrepr(self):
        return str(self.intval)

    @staticmethod
    def wrap_constant(intval):
        from pypy.jit.metainterp.history import ConstInt
        return ConstInt(intval)

class ResOpFloat(object):
    _mixin_ = True
    type = FLOAT
    
    def __init__(self, floatval):
        #assert isinstance(floatval, float)
        # XXX not sure between float or float storage
        self.floatval = floatval

    def getresultrepr(self):
        return str(self.floatval)

    def getfloatstorage(self):
        return self.floatval
    getresult = getfloatstorage

    @staticmethod
    def wrap_constant(floatval):
        from pypy.jit.metainterp.history import ConstFloat
        return ConstFloat(floatval)

class ResOpPointer(object):
    _mixin_ = True
    type = REF
    
    def __init__(self, pval):
        assert typeOf(pval) == GCREF
        self.pval = pval

    def getref_base(self):
        return self.pval
    getresult = getref_base

    def getresultrepr(self):
        # XXX what do we want to put in here?
        return str(self.pval)

    @staticmethod
    def wrap_constant(pval):
        from pypy.jit.metainterp.history import ConstPtr
        return ConstPtr(pval)

# ===================
# Top of the hierachy
# ===================

class PlainResOp(AbstractResOp):
    pass

class ResOpWithDescr(AbstractResOp):

    _descr = None

    def getdescr(self):
        return self._descr

    def getdescrclone(self):
        return self._descr.clone_if_mutable()

    def setdescr(self, descr):
        # for 'call', 'new', 'getfield_gc'...: the descr is a prebuilt
        # instance provided by the backend holding details about the type
        # of the operation.  It must inherit from AbstractDescr.  The
        # backend provides it with cpu.fielddescrof(), cpu.arraydescrof(),
        # cpu.calldescrof(), and cpu.typedescrof().
        self._check_descr(descr)
        self._descr = descr

    def cleardescr(self):
        self._descr = None

    def _check_descr(self, descr):
        if not we_are_translated() and getattr(descr, 'I_am_a_descr', False):
            return # needed for the mock case in oparser_model
        from pypy.jit.metainterp.history import check_descr
        check_descr(descr)


class GuardResOp(ResOpWithDescr):

    _fail_args = None

    def getfailargs(self):
        return self._fail_args

    def setfailargs(self, fail_args):
        self._fail_args = fail_args

# ============
# arity mixins
# ============

class NullaryOp(object):
    _mixin_ = True

    NUMARGS = 0

    def initarglist(self, args):
        assert len(args) == 0

    def getarglist(self):
        return []

    def numargs(self):
        return 0

    def getarg(self, i):
        raise IndexError

    def setarg(self, i, box):
        raise IndexError

    def foreach_arg(self, func):
        pass

    def clone(self):
        r = create_resop_0(self.opnum, self.getresult(), self.getdescrclone())
        if self.is_guard():
            r.setfailargs(self.getfailargs())
        return r

class UnaryOp(object):
    _mixin_ = True
    _arg0 = None

    NUMARGS = 1

    def initarglist(self, args):
        assert len(args) == 1
        self._arg0, = args

    def getarglist(self):
        return [self._arg0]

    def numargs(self):
        return 1

    def getarg(self, i):
        if i == 0:
            return self._arg0
        else:
            raise IndexError

    def setarg(self, i, box):
        if i == 0:
            self._arg0 = box
        else:
            raise IndexError

    @specialize.arg(1)
    def foreach_arg(self, func):
        func(self.getopnum(), 0, self._arg0)

    def clone(self):
        r = create_resop_1(self.opnum, self.getresult(), self._arg0,
                              self.getdescrclone())
        if self.is_guard():
            r.setfailargs(self.getfailargs())
        return r

class BinaryOp(object):
    _mixin_ = True
    _arg0 = None
    _arg1 = None

    NUMARGS = 2

    def initarglist(self, args):
        assert len(args) == 2
        self._arg0, self._arg1 = args

    def numargs(self):
        return 2

    def getarg(self, i):
        if i == 0:
            return self._arg0
        elif i == 1:
            return self._arg1
        else:
            raise IndexError

    def setarg(self, i, box):
        if i == 0:
            self._arg0 = box
        elif i == 1:
            self._arg1 = box
        else:
            raise IndexError

    def getarglist(self):
        return [self._arg0, self._arg1]

    @specialize.arg(1)
    def foreach_arg(self, func):
        func(self.getopnum(), 0, self._arg0)
        func(self.getopnum(), 1, self._arg1)

    def clone(self):
        r = create_resop_2(self.opnum, self.getresult(), self._arg0, self._arg1,
                           self.getdescrclone())
        if self.is_guard():
            r.setfailargs(self.getfailargs())
        return r


class TernaryOp(object):
    _mixin_ = True
    _arg0 = None
    _arg1 = None
    _arg2 = None

    NUMARGS = 3

    def initarglist(self, args):
        assert len(args) == 3
        self._arg0, self._arg1, self._arg2 = args

    def getarglist(self):
        return [self._arg0, self._arg1, self._arg2]

    def numargs(self):
        return 3

    def getarg(self, i):
        if i == 0:
            return self._arg0
        elif i == 1:
            return self._arg1
        elif i == 2:
            return self._arg2
        else:
            raise IndexError

    def setarg(self, i, box):
        if i == 0:
            self._arg0 = box
        elif i == 1:
            self._arg1 = box
        elif i == 2:
            self._arg2 = box
        else:
            raise IndexError

    @specialize.arg(1)
    def foreach_arg(self, func):
        func(self.getopnum(), 0, self._arg0)
        func(self.getopnum(), 1, self._arg1)
        func(self.getopnum(), 2, self._arg2)

    def clone(self):
        assert not self.is_guard()
        return create_resop_3(self.opnum, self.getresult(), self._arg0,
                              self._arg1, self._arg2, self.getdescrclone())
    

class N_aryOp(object):
    _mixin_ = True
    _args = None

    NUMARGS = -1

    def initarglist(self, args):
        self._args = args

    def getarglist(self):
        return self._args

    def numargs(self):
        return len(self._args)

    def getarg(self, i):
        return self._args[i]

    def setarg(self, i, box):
        self._args[i] = box

    @specialize.arg(1)
    def foreach_arg(self, func):
        for i, arg in enumerate(self._args):
            func(self.getopnum(), i, arg)

    def clone(self):
        assert not self.is_guard()
        return create_resop(self.opnum, self.getresult(), self._args[:],
                              self.getdescrclone())


# ____________________________________________________________

_oplist = [
    '_FINAL_FIRST',
    'JUMP/*d/N',
    'FINISH/*d/N',
    '_FINAL_LAST',

    'LABEL/*d/N',

    '_GUARD_FIRST',
    '_GUARD_FOLDABLE_FIRST',
    'GUARD_TRUE/1d/N',
    'GUARD_FALSE/1d/N',
    'GUARD_VALUE/2d/N',
    'GUARD_CLASS/2d/N',
    'GUARD_NONNULL/1d/N',
    'GUARD_ISNULL/1d/N',
    'GUARD_NONNULL_CLASS/2d/N',
    '_GUARD_FOLDABLE_LAST',
    'GUARD_NO_EXCEPTION/0d/N',   # may be called with an exception currently set
    'GUARD_EXCEPTION/1d/N',      # may be called with an exception currently set
    'GUARD_NO_OVERFLOW/0d/N',
    'GUARD_OVERFLOW/0d/N',
    'GUARD_NOT_FORCED/0d/N',     # may be called with an exception currently set
    'GUARD_NOT_INVALIDATED/0d/N',
    '_GUARD_LAST', # ----- end of guard operations -----

    '_NOSIDEEFFECT_FIRST', # ----- start of no_side_effect operations -----
    '_ALWAYS_PURE_FIRST', # ----- start of always_pure operations -----
    'INT_ADD/2/i',
    'INT_SUB/2/i',
    'INT_MUL/2/i',
    'INT_FLOORDIV/2/i',
    'UINT_FLOORDIV/2/i',
    'INT_MOD/2/i',
    'INT_AND/2/i',
    'INT_OR/2/i',
    'INT_XOR/2/i',
    'INT_RSHIFT/2/i',
    'INT_LSHIFT/2/i',
    'UINT_RSHIFT/2/i',
    'FLOAT_ADD/2/f',
    'FLOAT_SUB/2/f',
    'FLOAT_MUL/2/f',
    'FLOAT_TRUEDIV/2/f',
    'FLOAT_NEG/1/f',
    'FLOAT_ABS/1/f',
    'CAST_FLOAT_TO_INT/1/i',          # don't use for unsigned ints; we would
    'CAST_INT_TO_FLOAT/1/f',          # need some messy code in the backend
    'CAST_FLOAT_TO_SINGLEFLOAT/1/i',
    'CAST_SINGLEFLOAT_TO_FLOAT/1/f',
    'CONVERT_FLOAT_BYTES_TO_LONGLONG/1/f',
    'CONVERT_LONGLONG_BYTES_TO_FLOAT/1/f',
    #
    'INT_LT/2b/i',
    'INT_LE/2b/i',
    'INT_EQ/2b/i',
    'INT_NE/2b/i',
    'INT_GT/2b/i',
    'INT_GE/2b/i',
    'UINT_LT/2b/i',
    'UINT_LE/2b/i',
    'UINT_GT/2b/i',
    'UINT_GE/2b/i',
    'FLOAT_LT/2b/i',
    'FLOAT_LE/2b/i',
    'FLOAT_EQ/2b/i',
    'FLOAT_NE/2b/i',
    'FLOAT_GT/2b/i',
    'FLOAT_GE/2b/i',
    #
    'INT_IS_ZERO/1b/i',
    'INT_IS_TRUE/1b/i',
    'INT_NEG/1/i',
    'INT_INVERT/1/i',
    #
    'SAME_AS/1/*',      # gets a Const or a Box, turns it into another Box
    'CAST_PTR_TO_INT/1/i',
    'CAST_INT_TO_PTR/1/p',
    #
    'PTR_EQ/2b/i',
    'PTR_NE/2b/i',
    'INSTANCE_PTR_EQ/2b/i',
    'INSTANCE_PTR_NE/2b/i',
    #
    'ARRAYLEN_GC/1d/i',
    'STRLEN/1/i',
    'STRGETITEM/2/i',
    'GETFIELD_GC_PURE/1d/*',
    'GETFIELD_RAW_PURE/1d/*',
    'GETARRAYITEM_GC_PURE/2d/*',
    'UNICODELEN/1/i',
    'UNICODEGETITEM/2/i',
    #
    # ootype operations
    #'INSTANCEOF/1db',
    #'SUBCLASSOF/2b',
    #
    '_ALWAYS_PURE_LAST',  # ----- end of always_pure operations -----

    'GETARRAYITEM_GC/2d/*',
    'GETARRAYITEM_RAW/2d/*',
    'GETINTERIORFIELD_GC/2d/*',
    'GETINTERIORFIELD_RAW/2d/*',
    'GETFIELD_GC/1d/*',
    'GETFIELD_RAW/1d/*',
    '_MALLOC_FIRST',
    'NEW/0d/p',
    'NEW_WITH_VTABLE/1/p',
    'NEW_ARRAY/1d/p',
    'NEWSTR/1/p',
    'NEWUNICODE/1/p',
    '_MALLOC_LAST',
    'FORCE_TOKEN/0/i',
    'VIRTUAL_REF/2/i',         # removed before it's passed to the backend
    'READ_TIMESTAMP/0/f',
    'MARK_OPAQUE_PTR/1b/N',
    '_NOSIDEEFFECT_LAST', # ----- end of no_side_effect operations -----

    'SETARRAYITEM_GC/3d/N',
    'SETARRAYITEM_RAW/3d/N',
    'SETINTERIORFIELD_GC/3d/N',
    'SETINTERIORFIELD_RAW/3d/N',
    'SETFIELD_GC/2d/N',
    'SETFIELD_RAW/2d/N',
    'STRSETITEM/3/N',
    'UNICODESETITEM/3/N',
    #'RUNTIMENEW/1',     # ootype operation
    'COND_CALL_GC_WB/2d/N', # [objptr, newvalue] (for the write barrier)
    'COND_CALL_GC_WB_ARRAY/3d/N', # [objptr, arrayindex, newvalue] (write barr.)
    'DEBUG_MERGE_POINT/*/N',      # debugging only
    'JIT_DEBUG/*/N',              # debugging only
    'VIRTUAL_REF_FINISH/2/N',   # removed before it's passed to the backend
    'COPYSTRCONTENT/5/N',       # src, dst, srcstart, dststart, length
    'COPYUNICODECONTENT/5/N',
    'QUASIIMMUT_FIELD/1d/N',    # [objptr], descr=SlowMutateDescr
    'RECORD_KNOWN_CLASS/2/N',   # [objptr, clsptr]
    'KEEPALIVE/1/N',

    '_CANRAISE_FIRST', # ----- start of can_raise operations -----
    '_CALL_FIRST',
    'CALL/*d/*',
    'CALL_ASSEMBLER/*d/*',  # call already compiled assembler
    'CALL_MAY_FORCE/*d/*',
    'CALL_LOOPINVARIANT/*d/*',
    'CALL_RELEASE_GIL/*d/*',  # release the GIL and "close the stack" for asmgcc
    #'OOSEND',                     # ootype operation
    #'OOSEND_PURE',                # ootype operation
    'CALL_PURE/*d/*',             # removed before it's passed to the backend
    'CALL_MALLOC_GC/*d/p',      # like CALL, but NULL => propagate MemoryError
    'CALL_MALLOC_NURSERY/1/p',  # nursery malloc, const number of bytes, zeroed
    '_CALL_LAST',
    '_CANRAISE_LAST', # ----- end of can_raise operations -----

    '_OVF_FIRST', # ----- start of is_ovf operations -----
    'INT_ADD_OVF/2/i',
    'INT_SUB_OVF/2/i',
    'INT_MUL_OVF/2/i',
    '_OVF_LAST', # ----- end of is_ovf operations -----
    '_LAST',     # for the backend to add more internal operations
]

# ____________________________________________________________

class rop(object):
    pass

class rop_lowercase(object):
    pass # for convinience

opclasses = []   # mapping numbers to the concrete ResOp class
opname = {}      # mapping numbers to the original names, for debugging
oparity = []     # mapping numbers to the arity of the operation or -1
opwithdescr = [] # mapping numbers to a flag "takes a descr"
opboolresult= [] # mapping numbers to a flag "returns a boolean"
optp = []        # mapping numbers to typename of returnval 'i', 'p', 'N' or 'f'

class opgroups(object):
    pass

def setup(debug_print=False):
    i = 0
    for basename in _oplist:
        if '/' in basename:
            basename, arity, tp = basename.split('/')
            withdescr = 'd' in arity
            boolresult = 'b' in arity
            arity = arity.rstrip('db')
            if arity == '*':
                setattr(opgroups, basename, (basename + '_i', basename + '_N',
                                             basename + '_f', basename + '_p'))
                arity = -1
            else:
                arity = int(arity)
        else:
            arity, withdescr, boolresult, tp = -1, True, False, "N"  # default
        if not basename.startswith('_'):
            clss = create_classes_for_op(basename, i, arity, withdescr, tp)
        else:
            clss = [(None, basename, None)]
        for cls, name, tp in clss:
            if debug_print:
                print '%30s = %d' % (name, i)
            opname[i] = name
            setattr(rop, name, i)
            i += 1
            opclasses.append(cls)
            oparity.append(arity)
            opwithdescr.append(withdescr)
            opboolresult.append(boolresult)
            optp.append(tp)
            assert (len(opclasses)==len(oparity)==len(opwithdescr)
                    ==len(opboolresult))

    for k, v in rop.__dict__.iteritems():
        if not k.startswith('__'):
            setattr(rop_lowercase, k.lower(), v)

def get_base_class(mixin, tpmixin, base):
    try:
        return get_base_class.cache[(mixin, tpmixin, base)]
    except KeyError:
        arity_name = mixin.__name__[:-2]  # remove the trailing "Op"
        name = arity_name + base.__name__ + tpmixin.__name__[5:]
        # something like BinaryPlainResOpInt
        bases = (mixin, tpmixin, base)
        cls = type(name, bases, {})
        get_base_class.cache[(mixin, tpmixin, base)] = cls
        return cls
get_base_class.cache = {}

def create_classes_for_op(name, opnum, arity, withdescr, tp):
    arity2mixin = {
        0: NullaryOp,
        1: UnaryOp,
        2: BinaryOp,
        3: TernaryOp
        }
    tpmixin = {
        'N': ResOpNone,
        'i': ResOpInt,
        'f': ResOpFloat,
        'p': ResOpPointer,
    }

    is_guard = name.startswith('GUARD')
    if is_guard:
        assert withdescr
        baseclass = GuardResOp
    elif withdescr:
        baseclass = ResOpWithDescr
    else:
        baseclass = PlainResOp
    mixin = arity2mixin.get(arity, N_aryOp)

    if tp == '*':
        res = []
        for tp in ['f', 'p', 'i', 'N']:
            cls_name = '%s_OP_%s' % (name, tp)
            bases = (get_base_class(mixin, tpmixin[tp], baseclass),)
            dic = {'opnum': opnum}
            res.append((type(cls_name, bases, dic), name + '_' + tp, tp))
            opnum += 1
        return res   
    else:
        cls_name = '%s_OP' % name
        bases = (get_base_class(mixin, tpmixin[tp], baseclass),)
        dic = {'opnum': opnum}
        return [(type(cls_name, bases, dic), name, tp)]

setup(__name__ == '__main__')   # print out the table when run directly
del _oplist

opboolinvers = {
    rop.INT_EQ: rop.INT_NE,
    rop.INT_NE: rop.INT_EQ,
    rop.INT_LT: rop.INT_GE,
    rop.INT_GE: rop.INT_LT,
    rop.INT_GT: rop.INT_LE,
    rop.INT_LE: rop.INT_GT,

    rop.UINT_LT: rop.UINT_GE,
    rop.UINT_GE: rop.UINT_LT,
    rop.UINT_GT: rop.UINT_LE,
    rop.UINT_LE: rop.UINT_GT,

    rop.FLOAT_EQ: rop.FLOAT_NE,
    rop.FLOAT_NE: rop.FLOAT_EQ,
    rop.FLOAT_LT: rop.FLOAT_GE,
    rop.FLOAT_GE: rop.FLOAT_LT,
    rop.FLOAT_GT: rop.FLOAT_LE,
    rop.FLOAT_LE: rop.FLOAT_GT,

    rop.PTR_EQ: rop.PTR_NE,
    rop.PTR_NE: rop.PTR_EQ,
    }

opboolreflex = {
    rop.INT_EQ: rop.INT_EQ,
    rop.INT_NE: rop.INT_NE,
    rop.INT_LT: rop.INT_GT,
    rop.INT_GE: rop.INT_LE,
    rop.INT_GT: rop.INT_LT,
    rop.INT_LE: rop.INT_GE,

    rop.UINT_LT: rop.UINT_GT,
    rop.UINT_GE: rop.UINT_LE,
    rop.UINT_GT: rop.UINT_LT,
    rop.UINT_LE: rop.UINT_GE,

    rop.FLOAT_EQ: rop.FLOAT_EQ,
    rop.FLOAT_NE: rop.FLOAT_NE,
    rop.FLOAT_LT: rop.FLOAT_GT,
    rop.FLOAT_GE: rop.FLOAT_LE,
    rop.FLOAT_GT: rop.FLOAT_LT,
    rop.FLOAT_LE: rop.FLOAT_GE,

    rop.PTR_EQ: rop.PTR_EQ,
    rop.PTR_NE: rop.PTR_NE,
    }


def get_deep_immutable_oplist(operations):
    """
    When not we_are_translated(), turns ``operations`` into a frozenlist and
    monkey-patch its items to make sure they are not mutated.

    When we_are_translated(), do nothing and just return the old list.
    """
    from pypy.tool.frozenlist import frozenlist
    if we_are_translated():
        return operations
    #
    def setarg(*args):
        assert False, "operations cannot change at this point"
    def setdescr(*args):
        assert False, "operations cannot change at this point"
    newops = frozenlist(operations)
    for op in newops:
        op.setarg = setarg
        op.setdescr = setdescr
    return newops
