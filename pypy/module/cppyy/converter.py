from pypy.rpython.lltypesystem import rffi, lltype

class TypeConverter(object):
    def convert_argument(self, space, w_obj):
        raise NotImplementedError("abstract base class")


class IntConverter(TypeConverter):
    def convert_argument(self, space, w_obj):
        arg = space.int_w(w_obj)
        x = lltype.malloc(rffi.LONGP.TO, 1, flavor='raw')
        x[0] = arg
        return rffi.cast(rffi.VOIDP, x)        

class DoubleConverter(TypeConverter):
    def convert_argument(self, space, w_obj):
        arg = space.float_w(w_obj)
        x = lltype.malloc(rffi.DOUBLEP.TO, 1, flavor='raw')
        x[0] = arg
        return rffi.cast(rffi.VOIDP, x)        

def get_converter(name):
    if name == "int":
        return IntConverter()
    if name == "double":
        return DoubleConverter()
    raise TypeError("no clue what %s is" % name)
