from pypy.rpython.lltypesystem import rffi, lltype

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

def get_converter(name):
    try:
        return _converters[name]
    except KeyError:
        pass
    
    raise TypeError("no clue what %s is" % name)

_converters["int"]                 = IntConverter()
_converters["double"]              = DoubleConverter()
_converters["const char*"]         = CStringConverter()
