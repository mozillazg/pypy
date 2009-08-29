import weakref
from pypy.rpython.lltypesystem import lltype
from pypy.jit.backend.llsupport import symbolic
from pypy.jit.metainterp.history import AbstractDescr, getkind, BoxInt, BoxPtr
from pypy.jit.metainterp.history import TreeLoop
from pypy.jit.metainterp.resoperation import ResOperation, rop

# The point of the class organization in this file is to make instances
# as compact as possible.  This is done by not storing the field size or
# the 'is_pointer_field' flag in the instance itself but in the class
# (in methods actually) using a few classes instead of just one.


# ____________________________________________________________
# SizeDescrs

class SizeDescr(AbstractDescr):
    def __init__(self, size):
        self.size = size

    def repr_of_descr(self):
        return '<SizeDescr %s>' % self.size

BaseSizeDescr = SizeDescr

def get_size_descr(STRUCT, translate_support_code,
                   _cache=weakref.WeakKeyDictionary()):
    try:
        return _cache[STRUCT][translate_support_code]
    except KeyError:
        size = symbolic.get_size(STRUCT, translate_support_code)
        sizedescr = SizeDescr(size)
        cachedict = _cache.setdefault(STRUCT, {})
        cachedict[translate_support_code] = sizedescr
        return sizedescr


# ____________________________________________________________
# FieldDescrs

class BaseFieldDescr(AbstractDescr):

    def __init__(self, offset):
        self.offset = offset

    def sort_key(self):
        return self.offset

    def get_field_size(self, translate_support_code):
        raise NotImplementedError

    def is_pointer_field(self):
        return False        # unless overridden by GcPtrFieldDescr

    def repr_of_descr(self):
        return '<%s %s>' % (self._clsname, self.offset)


class NonGcPtrFieldDescr(BaseFieldDescr):
    _clsname = 'NonGcPtrFieldDescr'
    def get_field_size(self, translate_support_code):
        return symbolic.get_size_of_ptr(translate_support_code)

class GcPtrFieldDescr(NonGcPtrFieldDescr):
    _clsname = 'GcPtrFieldDescr'
    def is_pointer_field(self):
        return True

def getFieldDescrClass(TYPE):
    return getDescrClass(TYPE, BaseFieldDescr, GcPtrFieldDescr,
                         NonGcPtrFieldDescr, 'Field')

def get_field_descr(STRUCT, fieldname, translate_support_code,
                    _cache=weakref.WeakKeyDictionary()):
    try:
        return _cache[STRUCT][fieldname, translate_support_code]
    except KeyError:
        offset, _ = symbolic.get_field_token(STRUCT, fieldname,
                                             translate_support_code)
        FIELDTYPE = getattr(STRUCT, fieldname)
        fielddescr = getFieldDescrClass(FIELDTYPE)(offset)
        cachedict = _cache.setdefault(STRUCT, {})
        cachedict[fieldname, translate_support_code] = fielddescr
        return fielddescr


# ____________________________________________________________
# ArrayDescrs

_A = lltype.GcArray(lltype.Signed)     # a random gcarray


class BaseArrayDescr(AbstractDescr):

    def get_base_size(self, translate_support_code):
        basesize, _, _ = symbolic.get_array_token(_A, translate_support_code)
        return basesize

    def get_ofs_length(self, translate_support_code):
        _, _, ofslength = symbolic.get_array_token(_A, translate_support_code)
        return ofslength

    def get_item_size(self, translate_support_code):
        raise NotImplementedError

    def is_array_of_pointers(self):
        return False        # unless overridden by GcPtrArrayDescr

    def repr_of_descr(self):
        return '<%s>' % self._clsname


class NonGcPtrArrayDescr(BaseArrayDescr):
    _clsname = 'NonGcPtrArrayDescr'
    def get_item_size(self, translate_support_code):
        return symbolic.get_size_of_ptr(translate_support_code)

class GcPtrArrayDescr(NonGcPtrArrayDescr):
    _clsname = 'GcPtrArrayDescr'
    def is_array_of_pointers(self):
        return True

def getArrayDescrClass(ARRAY):
    return getDescrClass(ARRAY.OF, BaseArrayDescr, GcPtrArrayDescr,
                         NonGcPtrArrayDescr, 'Array')

def get_array_descr(ARRAY, _cache=weakref.WeakKeyDictionary()):
    try:
        return _cache[ARRAY]
    except KeyError:
        arraydescr = getArrayDescrClass(ARRAY)()
        # verify basic assumption that all arrays' basesize and ofslength
        # are equal
        basesize, itemsize, ofslength = symbolic.get_array_token(ARRAY, False)
        assert basesize == arraydescr.get_base_size(False)
        assert itemsize == arraydescr.get_item_size(False)
        assert ofslength == arraydescr.get_ofs_length(False)
        _cache[ARRAY] = arraydescr
        return arraydescr


# ____________________________________________________________
# CallDescrs

class BaseCallDescr(AbstractDescr):
    call_loop = None

    def __init__(self, arg_classes):
        self.arg_classes = arg_classes    # list of BoxInt/BoxPtr classes

    def returns_a_pointer(self):
        return False         # unless overridden by GcPtrCallDescr

    def get_result_size(self, translate_support_code):
        raise NotImplementedError

    def get_loop_for_call(self, cpu):
        if self.call_loop is not None:
            return self.call_loop
        args = [BoxInt()] + [cls() for cls in self.arg_classes]
        if self.get_result_size(cpu.translate_support_code) == 0:
            result = None
            result_list = []
        else:
            if self.returns_a_pointer():
                result = BoxPtr()
            else:
                result = BoxInt()
            result_list = [result]
        operations = [
            ResOperation(rop.CALL, args, result, self),
            ResOperation(rop.GUARD_NO_EXCEPTION, [], None),
            ResOperation(rop.FAIL, result_list, None)]
        operations[1].suboperations = [ResOperation(rop.FAIL, [], None)]
        loop = TreeLoop('call')
        loop.inputargs = args
        loop.operations = operations
        cpu.compile_operations(loop)
        self.call_loop = loop
        return loop


class GcPtrCallDescr(BaseCallDescr):
    def returns_a_pointer(self):
        return True

    def get_result_size(self, translate_support_code):
        return symbolic.get_size_of_ptr(translate_support_code)

class IntCallDescr(BaseCallDescr):
    def __init__(self, arg_classes, result_size):
        BaseCallDescr.__init__(self, arg_classes)
        self.result_size = result_size

    def get_result_size(self, translate_support_code):
        return self.result_size


def get_call_descr(ARGS, RESULT, translate_support_code, cache):
    arg_classes = []
    for ARG in ARGS:
        kind = getkind(ARG)
        if   kind == 'int': arg_classes.append(BoxInt)
        elif kind == 'ptr': arg_classes.append(BoxPtr)
        else:
            raise NotImplementedError('ARG = %r' % (ARG,))
    if RESULT is lltype.Void:
        result_size = 0
    else:
        result_size = symbolic.get_size(RESULT, translate_support_code)
    ptr = isinstance(RESULT, lltype.Ptr) and RESULT.TO._gckind == 'gc'
    key = (translate_support_code, tuple(arg_classes), result_size, ptr)
    try:
        return cache[key]
    except KeyError:
        if ptr:
            calldescr = GcPtrCallDescr(arg_classes)
        else:
            calldescr = IntCallDescr(arg_classes, result_size)
        cache[key] = calldescr
        return calldescr


# ____________________________________________________________

def getDescrClass(TYPE, BaseDescr, GcPtrDescr, NonGcPtrDescr,
                  nameprefix, _cache={}):
    if isinstance(TYPE, lltype.Ptr):
        if TYPE.TO._gckind == 'gc':
            return GcPtrDescr
        else:
            return NonGcPtrDescr
    try:
        return _cache[nameprefix, TYPE]
    except KeyError:
        #
        class Descr(BaseDescr):
            _clsname = '%s%sDescr' % (TYPE._name, nameprefix)
            def get_field_size(self, translate_support_code):
                return symbolic.get_size(TYPE, translate_support_code)
            get_item_size = get_field_size
        #
        Descr.__name__ = Descr._clsname
        _cache[nameprefix, TYPE] = Descr
        return Descr
