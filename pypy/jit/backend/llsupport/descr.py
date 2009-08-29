import weakref
from pypy.rpython.lltypesystem import lltype
from pypy.jit.backend.llsupport import symbolic
from pypy.jit.metainterp.history import AbstractDescr

# The point of the class organization in this file is to make instances
# as compact as possible.  This is done by not storing the field size or
# the 'is_pointer_field' flag in the instance itself but in the class
# (in methods actually) using a few classes instead of just one.


# ____________________________________________________________
# FieldDescrs

class AbstractFieldDescr(AbstractDescr):

    def __init__(self, offset):
        self.offset = offset

    def sort_key(self):
        return self.offset

    def get_field_size(self, translate_support_code):
        raise NotImplementedError

    def is_pointer_field(self):
        return False        # unless overridden by GcPtrFieldDescr


class NonGcPtrFieldDescr(AbstractFieldDescr):
    def get_field_size(self, translate_support_code):
        return symbolic.get_size_of_ptr(translate_support_code)

class GcPtrFieldDescr(NonGcPtrFieldDescr):
    def is_pointer_field(self):
        return True

def getFieldDescrClass(TYPE):
    return getDescrClass(TYPE, AbstractFieldDescr, GcPtrFieldDescr,
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


class AbstractArrayDescr(AbstractDescr):

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


class NonGcPtrArrayDescr(AbstractArrayDescr):
    def get_item_size(self, translate_support_code):
        return symbolic.get_size_of_ptr(translate_support_code)

class GcPtrArrayDescr(NonGcPtrArrayDescr):
    def is_array_of_pointers(self):
        return True

def getArrayDescrClass(ARRAY):
    return getDescrClass(ARRAY.OF, AbstractArrayDescr, GcPtrArrayDescr,
                         NonGcPtrArrayDescr, 'Array')

def get_array_descr(ARRAY, _cache=weakref.WeakKeyDictionary()):
    try:
        return _cache[ARRAY]
    except KeyError:
        arraydescr = getArrayDescrClass(ARRAY)()
        _cache[ARRAY] = arraydescr
        return arraydescr


# ____________________________________________________________

def getDescrClass(TYPE, AbstractDescr, GcPtrDescr, NonGcPtrDescr,
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
        class Descr(AbstractDescr):
            def get_field_size(self, translate_support_code):
                return symbolic.get_size(TYPE, translate_support_code)
            get_item_size = get_field_size
        #
        Descr.__name__ = '%s%sDescr' % (TYPE._name, nameprefix)
        _cache[nameprefix, TYPE] = Descr
        return Descr
