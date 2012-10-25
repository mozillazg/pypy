
""" This files describes the model used in pyjitpl. Note that all of the
following are IMMUTABLE. That means that we cannot just randomly change
parameters, instead we need to create a new version and setup the correct
forwarding. Public interface:

* create_resop, create_resop_0, create_resop_1, create_resop_2, create_resop_3

  create resops of various amount of arguments

* ConstInt, ConstFloat, ConstPtr - constant versions of boxes

"""

from pypy.jit.codewriter import longlong
from pypy.jit.codewriter import heaptracker
from pypy.rpython.lltypesystem import lltype, llmemory, rffi
from pypy.rpython.ootypesystem import ootype
from pypy.rlib.rarithmetic import is_valid_int, intmask
from pypy.rlib.objectmodel import compute_identity_hash, newlist_hint,\
     compute_unique_id, Symbolic, we_are_translated, specialize
from pypy.tool.pairtype import extendabletype

INT   = 'i'
REF   = 'r'
FLOAT = 'f'
STRUCT = 's'
VOID  = 'v'
HOLE = '_'

def create_resop_dispatch(opnum, result, args, descr=None, mutable=False):
    """ NOT_RPYTHON this is for tests only!
    """
    cls = opclasses[opnum]
    if cls.NUMARGS == 0:
        return create_resop_0(opnum, result, descr, mutable=mutable)
    elif cls.NUMARGS == 1:
        return create_resop_1(opnum, result, args[0], descr, mutable=mutable)
    elif cls.NUMARGS == 2:
        return create_resop_2(opnum, result, args[0], args[1], descr,
                              mutable=mutable)
    elif cls.NUMARGS == 3:
        return create_resop_3(opnum, result, args[0], args[1], args[2], descr,
                              mutable=mutable)
    else:
        return create_resop(opnum, result, args, descr, mutable=mutable)

@specialize.memo()
def _getcls(opnum, mutable):
    if mutable:
        return opclasses_mutable[opnum]
    else:
        return opclasses[opnum]

@specialize.arg(0, 4)
def create_resop(opnum, result, args, descr=None, mutable=False):
    """ Create an N-args resop with given opnum and args
    """
    cls = _getcls(opnum, mutable)
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
    for _arg in args:
        assert _arg.type != VOID
    op._args = args
    if descr is not None:
        op.setdescr(descr)
    return op

@specialize.arg(0, 3)
def create_resop_0(opnum, result, descr=None, mutable=False):
    """ Create an 0-arg resop with given opnum and args
    """
    cls = _getcls(opnum, mutable)
    assert cls.NUMARGS == 0
    if result is None:
        op = cls()
    else:
        op = cls(result)
    if descr is not None:
        op.setdescr(descr)
    return op

@specialize.arg(0, 4)
def create_resop_1(opnum, result, arg0, descr=None, mutable=False):
    """ Create a 1-arg resop with given opnum and args
    """
    cls = _getcls(opnum, mutable)
    assert cls.NUMARGS == 1
    if (cls.is_always_pure() and
        opnum not in (rop.SAME_AS_i, rop.SAME_AS_f, rop.SAME_AS_r)):
        if arg0.is_constant():
            return cls.wrap_constant(result)
    if result is None:
        op = cls()
    else:
        op = cls(result)
    assert arg0.type != VOID
    op._arg0 = arg0
    if descr is not None:
        op.setdescr(descr)
    return op

@specialize.arg(0, 5)
def create_resop_2(opnum, result, arg0, arg1, descr=None, mutable=False):
    """ Create a 2-arg resop with given opnum and args
    """
    cls = _getcls(opnum, mutable)
    assert cls.NUMARGS == 2
    if cls.is_always_pure():
        if arg0.is_constant() and arg1.is_constant():
            return cls.wrap_constant(result)
    if result is None:
        op = cls()
    else:
        op = cls(result)
    assert arg0.type != VOID
    assert arg1.type != VOID
    op._arg0 = arg0
    op._arg1 = arg1
    if descr is not None:
        op.setdescr(descr)
    return op

@specialize.arg(0, 6)
def create_resop_3(opnum, result, arg0, arg1, arg2, descr=None, mutable=False):
    """ Create a 3-arg resop with given opnum and args
    """
    cls = _getcls(opnum, mutable)
    assert cls.NUMARGS == 3
    if cls.is_always_pure():
        if arg0.is_constant() and arg1.is_constant() and arg2.is_constant():
            return cls.wrap_constant(result)
    if result is None:
        op = cls()
    else:
        op = cls(result)
    assert arg0.type != VOID
    assert arg1.type != VOID
    assert arg2.type != VOID
    op._arg0 = arg0
    op._arg1 = arg1
    op._arg2 = arg2
    if descr is not None:
        op.setdescr(descr)
    return op

class AbstractValue(object):
    __slots__ = ()

    __metaclass__ = extendabletype

    def getint(self):
        """ Get an integer value, if the box supports it, otherwise crash
        """
        raise NotImplementedError

    def getfloatstorage(self):
        """ Get a floatstorage value, if the box supports it, otherwise crash.
        Floatstorage is either real float or longlong, depends on 32 vs 64bit
        """
        raise NotImplementedError

    def getfloat(self):
        """ Get a float value, if the box supports it, otherwise crash
        """
        return longlong.getrealfloat(self.getfloatstorage())

    def getlonglong(self):
        assert longlong.supports_longlong
        return self.getfloatstorage()

    def getref_base(self):
        """ Get a base pointer (to llmemory.GCREF) if the box is a pointer box,
        otherwise crash
        """
        raise NotImplementedError

    def getref(self, TYPE):
        """ Get a pointer to type TYPE if the box is a pointer box,
        otherwise crash
        """
        raise NotImplementedError
    getref._annspecialcase_ = 'specialize:arg(1)'

    def _get_hash_(self):
        """ Compute the hash of the value. Since values are immutable this
        is safe
        """
        return compute_identity_hash(self)

    def constbox(self):
        """ Return a constant value of the current box wrapped in an
        apropriate constant class
        """
        raise NotImplementedError

    def getaddr(self):
        raise NotImplementedError

    def sort_key(self):
        """ Key for sorting
        """
        raise NotImplementedError

    def nonnull(self):
        """ Is this pointer box nonnull?
        """
        raise NotImplementedError

    def repr_rpython(self):
        return '%s' % self

    def _get_str(self):
        raise NotImplementedError

    def eq(self, other):
        """ Equality on the same terms as _get_hash_. By default identity
        equality, overriden by Boxes and Consts
        """
        return self is other

    def is_constant(self):
        return False

    def get_key_op(self, optimizer):
        return self

def getkind(TYPE, supports_floats=True,
                  supports_longlong=True,
                  supports_singlefloats=True):
    if TYPE is lltype.Void:
        return "void"
    elif isinstance(TYPE, lltype.Primitive):
        if TYPE is lltype.Float and supports_floats:
            return 'float'
        if TYPE is lltype.SingleFloat and supports_singlefloats:
            return 'int'     # singlefloats are stored in an int
        if TYPE in (lltype.Float, lltype.SingleFloat):
            raise NotImplementedError("type %s not supported" % TYPE)
        # XXX fix this for oo...
        if (TYPE != llmemory.Address and
            rffi.sizeof(TYPE) > rffi.sizeof(lltype.Signed)):
            if supports_longlong:
                assert rffi.sizeof(TYPE) == 8
                return 'float'
            raise NotImplementedError("type %s is too large" % TYPE)
        return "int"
    elif isinstance(TYPE, lltype.Ptr):
        if TYPE.TO._gckind == 'raw':
            return "int"
        else:
            return "ref"
    elif isinstance(TYPE, ootype.OOType):
        return "ref"
    else:
        raise NotImplementedError("type %s not supported" % TYPE)
getkind._annspecialcase_ = 'specialize:memo'

def repr_pointer(box):
    from pypy.rpython.lltypesystem import rstr
    try:
        T = box.value._obj.container._normalizedcontainer(check=False)._TYPE
        if T is rstr.STR:
            return repr(box._get_str())
        return '*%s' % (T._name,)
    except AttributeError:
        return box.value


class Const(AbstractValue):
    __slots__ = ()

    _forwarded = None # always

    def constbox(self):
        return self

    def eq(self, other):
        return self.same_constant(other)

    def same_constant(self, other):
        raise NotImplementedError

    def __repr__(self):
        return 'Const(%s)' % self._getrepr_()

    def is_constant(self):
        return True

def repr_rpython(box, typechars):
    return '%s/%s%d' % (box._get_hash_(), typechars,
                        compute_unique_id(box))


def repr_object(box):
    try:
        TYPE = box.value.obj._TYPE
        if TYPE is ootype.String:
            return '(%r)' % box.value.obj._str
        if TYPE is ootype.Class or isinstance(TYPE, ootype.StaticMethod):
            return '(%r)' % box.value.obj
        if isinstance(box.value.obj, ootype._view):
            return repr(box.value.obj._inst._TYPE)
        else:
            return repr(TYPE)
    except AttributeError:
        return box.value

def make_hashable_int(i):
    from pypy.rpython.lltypesystem.ll2ctypes import NotCtypesAllocatedStructure
    if not we_are_translated() and isinstance(i, llmemory.AddressAsInt):
        # Warning: such a hash changes at the time of translation
        adr = heaptracker.int2adr(i)
        try:
            return llmemory.cast_adr_to_int(adr, "emulated")
        except NotCtypesAllocatedStructure:
            return 12345 # use an arbitrary number for the hash
    return i

class ConstInt(Const):
    type = INT
    value = 0
    _attrs_ = ('value',)

    def __init__(self, value):
        if not we_are_translated():
            if is_valid_int(value):
                value = int(value)    # bool -> int
            else:
                assert isinstance(value, Symbolic)
        self.value = value

    def getint(self):
        return self.value

    def eq_value(self, other):
        return self.value == other.getint() # crash if incompatible type

    def getaddr(self):
        return heaptracker.int2adr(self.value)

    def _get_hash_(self):
        return make_hashable_int(self.value)

    def same_constant(self, other):
        if isinstance(other, ConstInt):
            return self.value == other.value
        return False

    def nonnull(self):
        return self.value != 0

    def _getrepr_(self):
        return self.value

    def repr_rpython(self):
        return repr_rpython(self, 'ci')

    def getboolbox(self):
        return False # for optimization

CONST_FALSE = ConstInt(0)
CONST_TRUE  = ConstInt(1)

class ConstFloat(Const):
    type = FLOAT
    value = longlong.ZEROF
    _attrs_ = ('value',)

    def __init__(self, valuestorage):
        assert lltype.typeOf(valuestorage) is longlong.FLOATSTORAGE
        self.value = valuestorage

    def getfloatstorage(self):
        return self.value

    def eq_value(self, other):
        return self.value == other.getfloatstorage()
    # crash if incompatible type

    def _get_hash_(self):
        return longlong.gethash(self.value)

    def same_constant(self, other):
        if isinstance(other, ConstFloat):
            return self.value == other.value
        return False

    def nonnull(self):
        return self.value != longlong.ZEROF

    def _getrepr_(self):
        return self.getfloat()

    def repr_rpython(self):
        return repr_rpython(self, 'cf')

CONST_FZERO = ConstFloat(longlong.ZEROF)

class ConstPtr(Const):
    type = REF
    value = lltype.nullptr(llmemory.GCREF.TO)
    _attrs_ = ('value',)

    def __init__(self, value):
        assert lltype.typeOf(value) == llmemory.GCREF
        self.value = value

    def getref_base(self):
        return self.value

    def getref(self, PTR):
        return lltype.cast_opaque_ptr(PTR, self.getref_base())
    getref._annspecialcase_ = 'specialize:arg(1)'

    def eq_value(self, other):
        return self.value == other.getref_base()
    # crash if incompatible type

    def _get_hash_(self):
        if self.value:
            return lltype.identityhash(self.value)
        else:
            return 0

    def getaddr(self):
        return llmemory.cast_ptr_to_adr(self.value)

    def same_constant(self, other):
        if isinstance(other, ConstPtr):
            return self.value == other.value
        return False

    def nonnull(self):
        return bool(self.value)

    _getrepr_ = repr_pointer

    def repr_rpython(self):
        return repr_rpython(self, 'cp')

    def _get_str(self):    # for debugging only
        from pypy.rpython.annlowlevel import hlstr
        from pypy.rpython.lltypesystem import rstr
        try:
            return hlstr(lltype.cast_opaque_ptr(lltype.Ptr(rstr.STR),
                                                self.value))
        except lltype.UninitializedMemoryAccess:
            return '<uninitialized string>'

CONST_NULL = ConstPtr(ConstPtr.value)

class AbstractResOp(AbstractValue):
    """The central ResOperation class, representing one operation."""

    # debug
    _name = ""
    _pc = 0
    _counter = 0

    _hash = 0
    opnum = 0

    is_mutable = False
    _forwarded = None    

    @classmethod
    def getopnum(cls):
        return cls.opnum

    def __hash__(self):
        # XXX this is a hack kill me
        import sys
        co_fname = sys._getframe(1).f_code.co_filename
        if co_fname.endswith('resume.py') or co_fname.endswith('optimizeopt/util.py') or 'backend/llgraph' in co_fname or 'backend/test' in co_fname or 'test/test_util' in co_fname:
            return object.__hash__(self)
        raise Exception("Should not hash resops, use get/set extra instead")

    def _get_hash_(self):
        """ rpython level implementation of hash, cache it because computations
        depending on the arguments might be a little tricky
        """
        if self._hash != 0:
            return self._hash
        hash = (self.getopnum() ^
                intmask(self.get_result_hash() << 4) ^
                self.get_descr_hash() ^
                intmask(self.get_arg_hash() << 1))
        if hash == 0:
            hash = -1
        self._hash = hash
        return hash

    def eq(self, other):
        """ ResOp is equal when the number is equal, all arguments and the
        actual numeric value of result
        """
        if self is other:
            return True
        if self.__class__ != other.__class__:
            # note that this checks for opnum already
            return False
        descr = self.getdescr()
        if descr is not None:
            if other.getdescr() is not descr:
                return False
        if not self.eq_value(other):
            return False
        if not self.args_eq(other):
            return False
        return True

    # methods implemented by the arity mixins
    # ---------------------------------------

    def getarglist(self):
        raise NotImplementedError

    def getarg(self, i):
        raise NotImplementedError

    def numargs(self):
        raise NotImplementedError

    # methods implemented by ResOpWithDescr
    # -------------------------------------

    def getdescr(self):
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

    def __str__(self):
        if not hasattr(self, '_str'):
            if self.type == INT:
                t = 'i'
            elif self.type == FLOAT:
                t = 'f'
            else:
                t = 'p'
            self._str = '%s%d' % (t, AbstractResOp._counter)
            AbstractResOp._counter += 1
        return self._str

    def repr(self, graytext=False):
        # RPython-friendly version
        args = self.getarglist()
        argsrepr = ', '.join([str(a) for a in args])
        resultrepr = self.getresultrepr()
        if resultrepr is not None:
            sres = '%s = ' % (str(self),)
        else:
            sres = ''
        if self._name:
            prefix = "%s:%s   " % (self._name, self._pc)
            if graytext:
                prefix = "\f%s\f" % prefix
        else:
            prefix = ""
        descr = self.getdescr()
        if descr is None or we_are_translated():
            return '%s%s%s(%s)' % (prefix, sres, self.getopname(), argsrepr)
        else:
            return '%s%s%s(%s, descr=%r)' % (prefix, sres, self.getopname(),
                                             argsrepr, descr)

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

    def _copy_extra_attrs(self, new):
        pass
    
    # some debugging help

    def __setattr__(self, attr, val):
        if attr not in ['_hash', '_str', '_forwarded']:
            assert self._forwarded is None
        object.__setattr__(self, attr, val)

    def __getattribute__(self, attr):
        if not attr.startswith('_') and attr != 'type':
            # methods are fine
            if not callable(getattr(self.__class__, attr, None)):
                try:
                    assert self._forwarded is None
                except AssertionError:
                    import pdb
                    pdb.set_trace()
        return object.__getattribute__(self, attr)

    def getforwarded(self):
        value = self._forwarded
        if value is None:
            # we only need to make a new copy if the old one is immutable
            if self.is_mutable:
                value = self
            else:
                value = self.make_forwarded_copy()
        else:
            if value._forwarded:
                while value._forwarded:
                    value = value._forwarded
                to_patch = self
                while to_patch._forwarded:
                    next = to_patch._forwarded
                    to_patch._forwarded = value
                    to_patch = next
        #self.ensure_imported(value)
        return value

# ===========
# type mixins
# ===========

class ResOpNone(object):
    _mixin_ = True
    type = VOID
    
    def __init__(self):
        pass # no return value

    def getresult(self):
        return None

    def getresultrepr(self):
        return None

    def get_result_hash(self):
        return 0

    def eq_value(self, other):
        return True

class ResOpInt(object):
    _mixin_ = True
    type = INT

    def __init__(self, intval):
        if not we_are_translated():
            if is_valid_int(intval):
                intval = int(intval)
            else:
                assert isinstance(intval, Symbolic)
        self._intval = intval

    def getint(self):
        return self._intval
    getresult = getint

    def getresultrepr(self):
        return str(self._intval)

    @staticmethod
    def wrap_constant(intval):
        return ConstInt(intval)

    def constbox(self):
        return ConstInt(self._intval)

    def get_result_hash(self):
        return make_hashable_int(self._intval)

    def eq_value(self, other):
        return self._intval == other.getint()

class ResOpFloat(object):
    _mixin_ = True
    type = FLOAT

    def __init__(self, floatval):
        #assert isinstance(floatval, float)
        # XXX not sure between float or float storage
        self._floatval = floatval

    def getresultrepr(self):
        return str(self._floatval)

    def getfloatstorage(self):
        return self._floatval
    getresult = getfloatstorage

    @staticmethod
    def wrap_constant(floatval):
        return ConstFloat(floatval)

    def constbox(self):
        return ConstFloat(self._floatval)

    def get_result_hash(self):
        return longlong.gethash(self._floatval)

    def eq_value(self, other):
        return self._floatval == other.getfloatstorage()

class ResOpPointer(object):
    _mixin_ = True
    type = REF

    def __init__(self, pval):
        assert lltype.typeOf(pval) == llmemory.GCREF
        self._pval = pval

    def getref_base(self):
        return self._pval
    getresult = getref_base

    def getref(self, TYPE):
        return lltype.cast_opaque_ptr(TYPE, self.getref_base())

    def getresultrepr(self):
        # XXX what do we want to put in here?
        return str(self._pval)

    def get_result_hash(self):
        if self._pval:
            return lltype.identityhash(self._pval)
        else:
            return 0

    @staticmethod
    def wrap_constant(pval):
        return ConstPtr(pval)

    def constbox(self):
        return ConstPtr(self._pval)

    def eq_value(self, other):
        return self._pval == other.getref_base()

# ===================
# Top of the hierachy
# ===================

class PlainResOp(AbstractResOp):
    def get_descr_hash(self):
        return 0

class ResOpWithDescr(AbstractResOp):

    _descr = None

    def getdescr(self):
        return self._descr

    def setdescr(self, descr):
        # for 'call', 'new', 'getfield_gc'...: the descr is a prebuilt
        # instance provided by the backend holding details about the type
        # of the operation.  It must inherit from AbstractDescr.  The
        # backend provides it with cpu.fielddescrof(), cpu.arraydescrof(),
        # cpu.calldescrof(), and cpu.typedescrof().
        self._check_descr(descr)
        if self._descr is not None and not self.is_mutable:
            raise Exception("descr already set!")
        self._descr = descr

    def cleardescr(self):
        self._descr = None

    def _check_descr(self, descr):
        if not we_are_translated() and getattr(descr, 'I_am_a_descr', False):
            return # needed for the mock case in oparser_model
        from pypy.jit.metainterp.history import check_descr
        check_descr(descr)

    def get_descr_hash(self):
        if self._descr is None:
            return 0 # for tests
        return compute_identity_hash(self._descr)

class GuardResOp(PlainResOp):

    # gathered during tracing
    _rd_snapshot = None
    _rd_frame_info_list = None

    def get_rd_snapshot(self):
        return self._rd_snapshot

    def set_rd_snapshot(self, rd_snapshot):
        if self._rd_snapshot is not None:
            raise Exception("rd_snapshot already set")
        self._rd_snapshot = rd_snapshot

    def get_rd_frame_info_list(self):
        return self._rd_frame_info_list

    def set_rd_frame_info_list(self, rd_frame_info_list):
        if self._rd_frame_info_list is not None:
            raise Exception("rd_frame_info_list already set")
        self._rd_frame_info_list = rd_frame_info_list

    def invent_descr(self, jitdriver_sd, metainterp_sd):
        from pypy.jit.metainterp import compile
        
        opnum = self.getopnum()
        if opnum == rop.GUARD_NOT_FORCED:
            descr = compile.ResumeGuardForcedDescr(metainterp_sd, jitdriver_sd)
        elif opnum == rop.GUARD_NOT_INVALIDATED:
            descr = compile.ResumeGuardNotInvalidated()
        else:
            descr = compile.ResumeGuardDescr()
        descr.rd_snapshot = self._rd_snapshot
        descr.rd_frame_info_list = self._rd_frame_info_list
        return descr

    def _copy_extra_attrs(self, res):
        res.set_rd_frame_info_list(self.get_rd_frame_info_list())
        res.set_rd_snapshot(self.get_rd_snapshot())

# ============
# arity mixins
# ============

class NullaryOp(object):
    _mixin_ = True

    NUMARGS = 0

    def getarglist(self):
        return []

    def numargs(self):
        return 0

    def getarg(self, i):
        raise IndexError

    def setarg(self, i, v):
        raise IndexError

    def foreach_arg(self, func, arg):
        pass        

    @specialize.arg(1)
    def make_forwarded_copy(self, newopnum=-1, descr=None):
        if newopnum == -1:
            newopnum = self.getopnum()
        res = create_resop_0(newopnum, self.getresult(),
                             descr or self.getdescr(), mutable=True)
        assert not self._forwarded
        self._forwarded = res
        self._copy_extra_attrs(res)
        return res

    def get_key_op(self, opt):
        return self

    def get_arg_hash(self):
        return 0

    def args_eq(self, other):
        return True

class UnaryOp(object):
    _mixin_ = True
    _arg0 = None

    NUMARGS = 1

    def getarglist(self):
        return [self._arg0]

    def numargs(self):
        return 1

    def getarg(self, i):
        if i == 0:
            return self._arg0
        else:
            raise IndexError

    def setarg(self, i, v):
        if i == 0:
            self._arg0 = v
        else:
            raise IndexError

    @specialize.arg(1)
    def foreach_arg(self, func, arg):
        func(arg, self.getopnum(), 0, self._arg0)

    def get_key_op(self, opt):
        new_arg = opt.getvalue(self._arg0).get_key_box()
        if new_arg is self._arg0:
            return self
        res = create_resop_1(self.opnum, self.getresult(), new_arg,
                             self.getdescr())
        return res        

    @specialize.arg(1)
    def make_forwarded_copy(self, newopnum=-1, arg0=None, descr=None):
        if newopnum == -1:
            newopnum = self.getopnum()
        res = create_resop_1(newopnum, self.getresult(), arg0 or self._arg0,
                             descr or self.getdescr(), mutable=True)
        assert not self._forwarded
        self._forwarded = res
        self._copy_extra_attrs(res)
        return res

    def get_arg_hash(self):
        return self._arg0._get_hash_()

    def args_eq(self, other):
        assert isinstance(other, self.__class__)
        return self._arg0.eq(other._arg0)

class BinaryOp(object):
    _mixin_ = True
    _arg0 = None
    _arg1 = None

    NUMARGS = 2

    def numargs(self):
        return 2

    def getarg(self, i):
        if i == 0:
            return self._arg0
        elif i == 1:
            return self._arg1
        else:
            raise IndexError

    def setarg(self, i, v):
        if i == 0:
            self._arg0 = v
        elif i == 1:
            self._arg1 = v
        else:
            raise IndexError

    def getarglist(self):
        return [self._arg0, self._arg1]

    @specialize.arg(1)
    def foreach_arg(self, func, arg):
        func(arg, self.getopnum(), 0, self._arg0)
        func(arg, self.getopnum(), 1, self._arg1)

    @specialize.argtype(1)
    def get_key_op(self, opt):
        new_arg0 = opt.getvalue(self._arg0).get_key_box()
        new_arg1 = opt.getvalue(self._arg1).get_key_box()
        if new_arg0 is self._arg0 and new_arg1 is self._arg0:
            return self
        return create_resop_2(self.opnum, self.getresult(),
                              new_arg0, new_arg1, self.getdescr())

    @specialize.arg(1)
    def make_forwarded_copy(self, newopnum=-1, arg0=None, arg1=None, descr=None):
        if newopnum == -1:
            newopnum = self.getopnum()
        res = create_resop_2(newopnum, self.getresult(), arg0 or self._arg0,
                             arg1 or self._arg1,
                             descr or self.getdescr(),
                             mutable=True)
        if self.is_guard():
            res.set_rd_frame_info_list(self.get_rd_frame_info_list())
            res.set_rd_snapshot(self.get_rd_snapshot())
        assert not self._forwarded
        self._forwarded = res
        self._copy_extra_attrs(res)
        return res

    def get_arg_hash(self):
        return (intmask(self._arg0._get_hash_() << 3) ^
                self._arg1._get_hash_())

    def args_eq(self, other):
        assert isinstance(other, self.__class__)
        return self._arg0.eq(other._arg0) and self._arg1.eq(other._arg1)

class TernaryOp(object):
    _mixin_ = True
    _arg0 = None
    _arg1 = None
    _arg2 = None

    NUMARGS = 3

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

    def setarg(self, i, v):
        if i == 0:
            self._arg0 = v
        elif i == 1:
            self._arg1 = v
        elif i == 2:
            self._arg2 = v
        else:
            raise IndexError

    @specialize.arg(1)
    def foreach_arg(self, func, arg):
        func(arg, self.getopnum(), 0, self._arg0)
        func(arg, self.getopnum(), 1, self._arg1)
        func(arg, self.getopnum(), 2, self._arg2)

    @specialize.argtype(1)
    def get_key_op(self, opt):
        new_arg0 = opt.getvalue(self._arg0).get_key_box()
        new_arg1 = opt.getvalue(self._arg1).get_key_box()
        new_arg2 = opt.getvalue(self._arg2).get_key_box()
        if (new_arg0 is self._arg0 and new_arg1 is self._arg1 and
            new_arg2 is self._arg2):
            return self
        return create_resop_3(self.opnum, self.getresult(),
                              new_arg0, new_arg1, new_arg2, self.getdescr())

    @specialize.arg(1)
    def make_forwarded_copy(self, newopnum=-1, arg0=None, arg1=None, arg2=None,
                     descr=None):
        if newopnum == -1:
            newopnum = self.getopnum()
        r = create_resop_3(newopnum, self.getresult(), arg0 or self._arg0,
                           arg1 or self._arg1, arg2 or self._arg2,
                           descr or self.getdescr(), mutable=True)
        assert not self._forwarded
        self._forwarded = r
        self._copy_extra_attrs(r)
        return r

    def get_arg_hash(self):
        return (intmask(self._arg0._get_hash_() << 5) ^
                intmask(self._arg1._get_hash_() << 2) ^
                self._arg2._get_hash_())

    def args_eq(self, other):
        assert isinstance(other, self.__class__)
        return (self._arg0.eq(other._arg0) and self._arg1.eq(other._arg1) and
                self._arg2.eq(other._arg2))

class N_aryOp(object):
    _mixin_ = True
    _args = None

    NUMARGS = -1

    def getarglist(self):
        return self._args

    def numargs(self):
        return len(self._args)

    def getarg(self, i):
        return self._args[i]

    def setarg(self, i, v):
        self._args[i] = v

    @specialize.arg(1)
    def foreach_arg(self, func, func_arg):
        for i, arg in enumerate(self._args):
            func(func_arg, self.getopnum(), i, arg)

    @specialize.argtype(1)
    def get_key_op(self, opt):
        newargs = None
        for i, arg in enumerate(self._args):
            new_arg = opt.getvalue(arg).get_key_box()
            if new_arg is not arg:
                if newargs is None:
                    newargs = newlist_hint(len(self._args))
                    for k in range(i):
                        newargs.append(self._args[k])
                newargs.append(new_arg)
            elif newargs is not None:
                newargs.append(arg)
        if newargs is None:
            return self
        return create_resop(self.opnum, self.getresult(),
                            newargs, self.getdescr())        

    @specialize.arg(1)
    def make_forwarded_copy(self, newopnum=-1, newargs=None, descr=None):
        if newopnum == -1:
            newopnum = self.getopnum()
        r = create_resop(newopnum, self.getresult(),
                         newargs or self.getarglist(),
                         descr or self.getdescr(), mutable=True)
        assert not self._forwarded
        self._copy_extra_attrs(r)
        self._forwarded = r
        return r

    def get_arg_hash(self):
        hash = 0
        for i, arg in enumerate(self._args):
            hash ^= intmask(arg._get_hash_() << (i & 15))
        return hash

    def args_eq(self, other):
        for i, arg in enumerate(self._args):
            if not arg.eq(other._args[i]):
                return False
        return True

# ____________________________________________________________

_oplist = [
    # key:
    # _<something> means just a marker
    # OPNAME/<number-of-parameters-or-*>[d]/T
    # where:
    #  "*" in parameter list means any number
    #  "d" means if there is a descr associated with a resop
    # T can be one of "r", "i", "f", "v", "*" or "?"
    # "r", "i", "f" - normal return, appropriate type
    # "v" - void return type
    # "*" - four variants will be generated, "r", "i", "f", "v"
    # "?" - three variants will be generated, "r", "i", "f"
    
    '_FINAL_FIRST',
    'JUMP/*d/v',
    'FINISH/*d/v',
    '_FINAL_LAST',

    'LABEL/*d/v',
    'INPUT/0/?',

    '_GUARD_FIRST',
    '_GUARD_FOLDABLE_FIRST',
    'GUARD_TRUE/1/v',
    'GUARD_FALSE/1/v',
    'GUARD_VALUE/2/v',
    'GUARD_CLASS/2/v',
    'GUARD_NONNULL/1/v',
    'GUARD_ISNULL/1/v',
    'GUARD_NONNULL_CLASS/2/v',
    '_GUARD_FOLDABLE_LAST',
    'GUARD_NO_EXCEPTION/0/v',   # may be called with an exception currently set
    'GUARD_EXCEPTION/1/r',      # may be called with an exception currently set
    'GUARD_NO_OVERFLOW/0/v',
    'GUARD_OVERFLOW/0/v',
    'GUARD_NOT_FORCED/0/v',     # may be called with an exception currently set
    'GUARD_NOT_INVALIDATED/0/v',
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
    'CONVERT_FLOAT_BYTES_TO_LONGLONG/1/L', # float on 32bit, int on 64bit
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
    'INT_FORCE_GE_ZERO/1/i',
    #
    'SAME_AS/1/?',      # gets a Const or a Box, turns it into another Box
    '_ALWAYS_PURE_NO_PTR_LAST',
    'CAST_PTR_TO_INT/1/i',
    'CAST_INT_TO_PTR/1/r',
    #
    'PTR_EQ/2b/i',
    'PTR_NE/2b/i',
    'INSTANCE_PTR_EQ/2b/i',
    'INSTANCE_PTR_NE/2b/i',
    #
    'ARRAYLEN_GC/1d/i',
    'STRLEN/1/i',
    'STRGETITEM/2/i',
    'GETFIELD_GC_PURE/1d/?',
    'GETFIELD_RAW_PURE/1d/?',
    'GETARRAYITEM_GC_PURE/2d/?',
    'GETARRAYITEM_RAW_PURE_i/2d/i',
    'GETARRAYITEM_RAW_PURE_f/2d/f',
    'UNICODELEN/1/i',
    'UNICODEGETITEM/2/i',
    #
    # ootype operations
    #'INSTANCEOF/1db',
    #'SUBCLASSOF/2b',
    #
    '_ALWAYS_PURE_LAST',  # ----- end of always_pure operations -----

    'GETARRAYITEM_GC/2d/?',
    'GETARRAYITEM_RAW_i/2d/i',
    'GETARRAYITEM_RAW_f/2d/f',
    'GETINTERIORFIELD_GC/2d/?',
    'GETINTERIORFIELD_RAW_i/2d/i',
    'GETINTERIORFIELD_RAW_f/2d/f',
    'RAW_LOAD_i/2d/i',
    'RAW_LOAD_f/2d/f',
    'GETFIELD_GC/1d/?',
    'GETFIELD_RAW_i/1d/i',
    'GETFIELD_RAW_f/1d/f',
    '_MALLOC_FIRST',
    'NEW/0d/r',
    'NEW_WITH_VTABLE/1/r',
    'NEW_ARRAY/1d/r',
    'NEWSTR/1/r',
    'NEWUNICODE/1/r',
    '_MALLOC_LAST',
    'JIT_FRAME/0/r',
    'VIRTUAL_REF/2/i',         # removed before it's passed to the backend
    'READ_TIMESTAMP/0/L',      # float on 32bit, int on 64bit
    'MARK_OPAQUE_PTR/1b/v',
    '_NOSIDEEFFECT_LAST', # ----- end of no_side_effect operations -----

    'ESCAPE/1/v', # tests
    'ESCAPE_r/1/r', # tests
    'ESCAPE_f/1/f', # tests
    'FORCE_SPILL/1/v', # tests

    'SETARRAYITEM_GC/3d/v',
    'SETARRAYITEM_RAW/3d/v',
    'SETINTERIORFIELD_GC/3d/v',
    'SETINTERIORFIELD_RAW/3d/v', # only used by llsupport/rewrite.py
    'RAW_STORE/3d/v',
    'SETFIELD_GC/2d/v',
    'SETFIELD_RAW/2d/v',
    'STRSETITEM/3/v',
    'UNICODESETITEM/3/v',
    #'RUNTIMENEW/1',     # ootype operation
    'COND_CALL_GC_WB/2d/v', # [objptr, newvalue] (for the write barrier)
    'COND_CALL_GC_WB_ARRAY/3d/v', # [objptr, arrayindex, newvalue] (write barr.)
    'DEBUG_MERGE_POINT/*/v',      # debugging only
    'JIT_DEBUG/*/v',              # debugging only
    'VIRTUAL_REF_FINISH/2/v',   # removed before it's passed to the backend
    'COPYSTRCONTENT/5/v',       # src, dst, srcstart, dststart, length
    'COPYUNICODECONTENT/5/v',
    'QUASIIMMUT_FIELD/1d/v',    # [objptr], descr=SlowMutateDescr
    'RECORD_KNOWN_CLASS/2/v',   # [objptr, clsptr]

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
    'CALL_MALLOC_GC/*d/r',      # like CALL, but NULL => propagate MemoryError
    'CALL_MALLOC_NURSERY/1/r',  # nursery malloc, const number of bytes, zeroed
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
                 # mapping numbers to the concrete ResOp, mutable version
opclasses_mutable = []
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
                cur = len(opclasses)
                setattr(opgroups, basename, (cur, cur + 1, cur + 2, cur + 3))
                arity = -1
            else:
                arity = int(arity)
        else:
            arity, withdescr, boolresult, tp = -1, True, False, "v"  # default
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

    ALLCALLS = []
    for k, v in rop.__dict__.iteritems():
        if k.startswith('CALL'):
            ALLCALLS.append(v)
    opgroups.ALLCALLS = tuple(ALLCALLS)

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
        'v': ResOpNone,
        'i': ResOpInt,
        'f': ResOpFloat,
        'r': ResOpPointer,
    }

    is_guard = name.startswith('GUARD')
    if is_guard:
        baseclass = GuardResOp
    elif withdescr:
        baseclass = ResOpWithDescr
    else:
        baseclass = PlainResOp
    mixin = arity2mixin.get(arity, N_aryOp)

    if tp in '*?':
        res = []
        if tp == '*':
            lst = ['i', 'r', 'f', 'v']
        else:
            lst = ['i', 'r', 'f']
        for tp in lst:
            cls_name = '%s_OP_%s' % (name, tp)
            bases = (get_base_class(mixin, tpmixin[tp], baseclass),)
            dic = {'opnum': opnum}
            res.append((type(cls_name, bases, dic), name + '_' + tp, tp))
            opnum += 1
        return res
    else:
        if tp == 'L':
            if longlong.is_64_bit:
                tp = 'i'
            else:
                tp = 'f'
        cls_name = '%s_OP' % name
        bases = (get_base_class(mixin, tpmixin[tp], baseclass),)
        dic = {'opnum': opnum}
        return [(type(cls_name, bases, dic), name, tp)]

setup(__name__ == '__main__')   # print out the table when run directly
del _oplist

_opboolinvers = {
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

_opboolreflex = {
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

@specialize.memo()
def example_for_opnum(opnum):
    if opclasses[opnum].type == INT:
        return 0
    elif opclasses[opnum].type == FLOAT:
        return 0.0
    else:
        return lltype.nullptr(llmemory.GCREF.TO)

opboolinvers = [-1] * len(opclasses)
opboolreflex = [-1] * len(opclasses)
for k, v in _opboolreflex.iteritems():
    opboolreflex[k] = v
for k, v in _opboolinvers.iteritems():
    opboolinvers[k] = v
