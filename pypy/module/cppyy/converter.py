from pypy.interpreter.error import OperationError
from pypy.rpython.lltypesystem import rffi, lltype

from pypy.module.cppyy import helper, capi

_converters = {}

class TypeConverter(object):
    def convert_argument(self, space, w_obj):
        raise NotImplementedError("abstract base class")

    def free_argument(self, arg):
        lltype.free(arg, flavor='raw')


class IntConverter(TypeConverter):
    def convert_argument(self, space, w_obj):
        arg = space.c_int_w(w_obj)
        x = lltype.malloc(rffi.LONGP.TO, 1, flavor='raw')
        x[0] = arg
        return rffi.cast(rffi.VOIDP, x)        

class DoubleConverter(TypeConverter):
    def convert_argument(self, space, w_obj):
        arg = space.float_w(w_obj)
        x = lltype.malloc(rffi.DOUBLEP.TO, 1, flavor='raw')
        x[0] = arg
        return rffi.cast(rffi.VOIDP, x)        

class CStringConverter(TypeConverter):
    def convert_argument(self, space, w_obj):
        arg = space.str_w(w_obj)
        x = rffi.str2charp(arg)
        return rffi.cast(rffi.VOIDP, x)

class InstancePtrConverter(TypeConverter):
    _immutable_ = True
    def __init__(self, space, cpptype):
        self.cpptype = cpptype

    def convert_argument(self, space, w_obj):
        from pypy.module.cppyy import interp_cppyy
        w_cppinstance = space.findattr(w_obj, space.wrap("_cppinstance"))
        if w_cppinstance is not None:
            w_obj = w_cppinstance
        obj = space.interpclass_w(w_obj)
        if isinstance(obj, interp_cppyy.W_CCPInstance):
            if capi.c_is_subtype(obj.cppclass.handle, self.cpptype.handle):
                return obj.rawobject
        raise OperationError(space.w_TypeError,
                             space.wrap("cannot pass %s as %s" % (
                                 space.type(w_obj).getname(space, "?"),
                                 self.cpptype.name)))
    def free_argument(self, arg):
        pass
        

def get_converter(space, name):
    from pypy.module.cppyy import interp_cppyy
    # The matching of the name to a converter should follow:
    #   1) full, exact match
    #   2) match of decorated, unqualified type
    #   3) accept const ref as by value
    #   4) accept ref as pointer
    #   5) generalized cases (covers basically all user classes)

    try:
        return _converters[name]
    except KeyError:
        pass

    compound = helper.compound(name)
    cpptype = interp_cppyy.type_byname(space, helper.clean_type(name))
    if compound == "*":
        return InstancePtrConverter(space, cpptype)

    raise OperationError(space.w_TypeError, space.wrap("no clue what %s is" % name))

_converters["int"]                 = IntConverter()
_converters["double"]              = DoubleConverter()
_converters["const char*"]         = CStringConverter()
