from pypy.interpreter.error import OperationError
from pypy.rpython.lltypesystem import rffi, lltype
from pypy.rlib.rarithmetic import r_singlefloat

from pypy.module.cppyy import helper, capi

_converters = {}

class TypeConverter(object):
    def convert_argument(self, space, w_obj):
        raise NotImplementedError("abstract base class")

    def free_argument(self, arg):
        lltype.free(arg, flavor='raw')


class VoidConverter(TypeConverter):
    def __init__(self, space, name):
        self.name = name

    def convert_argument(self, space, w_obj):
        raise OperationError(space.w_TypeError,
                             space.wrap('no converter available for type "%s"' % self.name))

class BoolConverter(TypeConverter):
    def convert_argument(self, space, w_obj):
        arg = space.c_int_w(w_obj)
        if arg != False and arg != True:
            raise OperationError(space.w_TypeError,
                                 space.wrap("boolean value should be bool, or integer 1 or 0"))
        x = lltype.malloc(rffi.LONGP.TO, 1, flavor='raw')
        x[0] = arg
        return rffi.cast(rffi.VOIDP, x)

class CharConverter(TypeConverter):
    def convert_argument(self, space, w_obj):
        arg = space.str_w(w_obj)
        if len(arg) != 1:
            raise OperationError(space.w_TypeError,
                                 space.wrap("char expecter, got string of size %d" % len(arg)))
        x = rffi.str2charp(arg)
        return rffi.cast(rffi.VOIDP, x)

class IntConverter(TypeConverter):
    def convert_argument(self, space, w_obj):
        arg = space.c_int_w(w_obj)
        x = lltype.malloc(rffi.LONGP.TO, 1, flavor='raw')
        x[0] = arg
        return rffi.cast(rffi.VOIDP, x)

class FloatConverter(TypeConverter):
    def convert_argument(self, space, w_obj):
        arg = space.float_w(w_obj)
        x = lltype.malloc(rffi.FLOATP.TO, 1, flavor='raw')
        x[0] = r_singlefloat(arg)
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
        if isinstance(obj, interp_cppyy.W_CPPInstance):
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
    #   6) void converter, which fails on use

    try:
        return _converters[name]
    except KeyError:
        pass

    compound = helper.compound(name)
    cpptype = interp_cppyy.type_byname(space, helper.clean_type(name))
    if compound == "*":
        return InstancePtrConverter(space, cpptype)

    # return a void converter here, so that the class can be build even
    # when some types are unknown; this overload will simply fail on use
    return VoidConverter(space, name)


_converters["bool"]                = BoolConverter()
_converters["char"]                = CharConverter()
_converters["unsigned char"]       = CharConverter()
_converters["int"]                 = IntConverter()
_converters["float"]               = FloatConverter()
_converters["double"]              = DoubleConverter()
_converters["const char*"]         = CStringConverter()
