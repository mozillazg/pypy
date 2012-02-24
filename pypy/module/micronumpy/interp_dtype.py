import sys

from pypy.interpreter.baseobjspace import Wrappable
from pypy.interpreter.buffer import Buffer
from pypy.interpreter.error import OperationError, operationerrfmt
from pypy.interpreter.gateway import interp2app, unwrap_spec
from pypy.interpreter.typedef import (TypeDef, GetSetProperty,
    interp_attrproperty, interp_attrproperty_w)
from pypy.module.micronumpy import types, interp_boxes
from pypy.rlib.objectmodel import specialize
from pypy.rlib.rarithmetic import LONG_BIT, r_longlong, r_ulonglong


UNSIGNEDLTR = "u"
SIGNEDLTR = "i"
BOOLLTR = "b"
FLOATINGLTR = "f"
VOIDLTR = 'V'
STRINGLTR = 'S'
UNICODELTR = 'U'

class W_Dtype(Wrappable):
    _immutable_fields_ = ["itemtype", "num", "kind"]

    def __init__(self, itemtype, num, kind, name, char, w_box_type,
                 byteorder="=", builtin_type=None, fields=None, fieldnames=None):
        self.itemtype = itemtype
        self.num = num
        self.kind = kind
        self.name = name
        self.char = char
        self.w_box_type = w_box_type
        self.byteorder = byteorder
        self.builtin_type = builtin_type
        self.fields = fields
        self.fieldnames = fieldnames

    @specialize.argtype(1)
    def box(self, value):
        return self.itemtype.box(value)

    def coerce(self, space, w_item):
        return self.itemtype.coerce(space, self, w_item)

    def getitem(self, arr, i):
        return self.itemtype.read(arr, 1, i, 0)

    def getitem_bool(self, arr, i):
        return self.itemtype.read_bool(arr, 1, i, 0)

    def setitem(self, arr, i, box):
        self.itemtype.store(arr, 1, i, 0, box)

    def fill(self, storage, box, start, stop):
        self.itemtype.fill(storage, self.get_size(), box, start, stop, 0)

    def descr_str(self, space):
        return space.wrap(self.name)

    def descr_repr(self, space):
        return space.wrap("dtype('%s')" % self.name)

    def descr_get_itemsize(self, space):
        return space.wrap(self.itemtype.get_element_size())

    def descr_get_alignment(self, space):
        return space.wrap(self.itemtype.alignment)

    def descr_get_shape(self, space):
        return space.newtuple([])

    def eq(self, space, w_other):
        w_other = space.call_function(space.gettypefor(W_Dtype), w_other)
        return space.is_w(self, w_other)

    def descr_eq(self, space, w_other):
        return space.wrap(self.eq(space, w_other))

    def descr_ne(self, space, w_other):
        return space.wrap(not self.eq(space, w_other))

    def descr_get_fields(self, space):
        if self.fields is None:
            return space.w_None
        w_d = space.newdict()
        for name, (offset, subdtype) in self.fields.iteritems():
            space.setitem(w_d, space.wrap(name), space.newtuple([subdtype,
                                                                 space.wrap(offset)]))
        return w_d

    def descr_get_names(self, space):
        if self.fieldnames is None:
            return space.w_None
        return space.newtuple([space.wrap(name) for name in self.fieldnames])

    def descr_get_str(self, space):
        byteorder = self.byteorder
        if self.byteorder == "=":
            byteorder = "<"
        return space.wrap("%s%s%d" % (byteorder, self.kind, self.itemtype.get_element_size()))

    @unwrap_spec(item=str)
    def descr_getitem(self, space, item):
        if self.fields is None:
            raise OperationError(space.w_KeyError, space.wrap("There are no keys in dtypes %s" % self.name))
        try:
            return self.fields[item][1]
        except KeyError:
            raise OperationError(space.w_KeyError, space.wrap("Field named %s not found" % item))

    def is_int_type(self):
        return (self.kind == SIGNEDLTR or self.kind == UNSIGNEDLTR or
                self.kind == BOOLLTR)

    def is_signed(self):
        return self.kind == SIGNEDLTR

    def is_bool_type(self):
        return self.kind == BOOLLTR

    def is_record_type(self):
        return self.fields is not None

    def __repr__(self):
        if self.fields is not None:
            return '<DType %r>' % self.fields
        return '<DType %r>' % self.itemtype

    def get_size(self):
        return self.itemtype.get_element_size()


def invalid_dtype(space, w_obj):
    if space.isinstance_w(w_obj, space.w_str):
        raise operationerrfmt(space.w_TypeError,
            'data type "%s" not understood', space.str_w(w_obj)
        )
    else:
        raise OperationError(space.w_TypeError, space.wrap("data type not understood"))

def dtype_from_list(space, items_w):
    pass

def is_byteorder(ch):
    return ch == ">" or ch == "<" or ch == "|" or ch == "="

def is_commastring(typestr):
    # Number at the start of the string.
    if ((typestr[0] >= "0" and typestr[0] <= "9") or
        (len(typestr) > 1 and is_byteorder(typestr[0]) and
            (typestr[1] >= "0" and typestr[1] <= "9"))):
        return True

    # Starts with an empty tuple.
    if ((len(typestr) > 1 and typestr[0] == "(" and typestr[1] == ")") or
        (len(typestr) > 3 and is_byteorder(typestr[0]) and
            (typestr[1] == "(" and typestr[2] == ")"))):
        return True

    # Commas outside of []
    sqbracket = 0
    for i in xrange(1, len(typestr)):
        ch = typestr[i]
        if ch == ",":
            if not sqbracket:
                return True
        elif ch == "[":
            sqbracket += 1
        elif ch == "]":
            sqbracket -= 1
    return False

def dtype_from_object(space, w_obj):
    cache = get_dtype_cache(space)

    if space.is_w(w_obj, space.w_None):
        return cache.w_float64dtype

    if space.isinstance_w(w_obj, space.gettypefor(W_Dtype)):
        return w_obj

    if space.isinstance_w(w_obj, space.w_type):
        for dtype in cache.builtin_dtypes:
            if (space.is_w(w_obj, dtype.w_box_type) or
                dtype.builtin_type is not None and space.is_w(w_obj, dtype.builtin_type)):
                return dtype
        raise invalid_dtype(space, w_obj)

    elif (space.isinstance_w(w_obj, space.w_str) or
        space.isinstance_w(w_obj, space.w_unicode)):

        typestr = space.str_w(w_obj)
        w_base_dtype = None
        elsize = -1

        if not typestr:
            raise invalid_dtype(space, w_obj)

        if is_commastring(typestr):
            return dtype_from_commastring(space, typestr)

        if is_byteorder(typestr[0]):
            endian = typestr[0]
            if endian == "|":
                endian = "="
            typestr = typestr[1:]
        else:
            endian = "="

        if not typestr:
            raise invalid_dtype(space, w_obj)

        if len(typestr) == 1:
            try:
                w_base_dtype = cache.dtypes_by_name[typestr]
            except KeyError:
                raise invalid_dtype(space, w_obj)
        else:
            # Something like f8
            try:
                elsize = int(typestr[1:])
            except ValueError:
                pass
            else:
                kind = typestr[0]
                if kind == STRINGLTR:
                    w_base_dtype = cache.w_stringdtype
                elif kind == UNICODELTR:
                    w_base_dtype = cache.w_unicodedtype
                elif kind == VOIDLTR:
                    w_base_dtype = cache.w_voiddtype
                else:
                    for dtype in cache.builtin_dtypes:
                        if (dtype.kind == kind and
                            dtype.itemtype.get_element_size() == elsize):
                            w_base_dtype = dtype
                            elsize = -1
                            break
                    else:
                        raise invalid_dtype(space, w_obj)

        if w_base_dtype is not None:
            if elsize != -1:
                itemtype = w_base_dtype.itemtype.array(elsize)
                w_base_dtype = W_Dtype(
                    itemtype, w_base_dtype.num, w_base_dtype.kind,
                    w_base_dtype.name + str(itemtype.get_element_size() * 8),
                    w_base_dtype.char, w_base_dtype.w_box_type,
                    byteorder=w_base_dtype.byteorder,
                    builtin_type=w_base_dtype.builtin_type
                )
            if endian != "=" and endian != nonnative_byteorder_prefix:
                endian = "="
            if (endian != "=" and w_base_dtype.byteorder != "|" and
                w_base_dtype.byteorder != endian):
                return W_Dtype(
                    cache.nonnative_dtypes[w_base_dtype], w_base_dtype.num,
                    w_base_dtype.kind, w_base_dtype.name, w_base_dtype.char,
                    w_base_dtype.w_box_type, byteorder=endian,
                    builtin_type=w_base_dtype.builtin_type
                )
            else:
                return w_base_dtype

    elif space.isinstance_w(w_obj, space.w_tuple):
        return dtype_from_tuple(space, space.listview(w_obj))

    elif space.isinstance_w(w_obj, space.w_list):
        return dtype_from_list(space, space.listview(w_obj))

    elif space.isinstance_w(w_obj, space.w_dict):
        return dtype_from_dict(space, w_obj)

    else:
        raise invalid_dtype(space, w_obj)

    w_type_dict = cache.w_type_dict
    w_result = None
    if w_type_dict is not None:
        try:
            w_result = space.getitem(w_type_dict, w_obj)
        except OperationError, e:
            if not e.match(space, space.w_KeyError):
                raise
            if space.isinstance_w(w_obj, space.w_str):
                w_key = space.call_method(w_obj, "decode", space.wrap("ascii"))
                try:
                    w_result = space.getitem(w_type_dict, w_key)
                except OperationError, e:
                    if not e.match(space, space.w_KeyError):
                        raise
        if w_result is not None:
            return dtype_from_object(space, w_result)

    raise invalid_dtype(space, w_obj)

def descr__new__(space, w_subtype, w_dtype):
    w_dtype = dtype_from_object(space, w_dtype)
    return w_dtype


W_Dtype.typedef = TypeDef("dtype",
    __module__ = "numpypy",
    __new__ = interp2app(descr__new__),

    __str__= interp2app(W_Dtype.descr_str),
    __repr__ = interp2app(W_Dtype.descr_repr),
    __eq__ = interp2app(W_Dtype.descr_eq),
    __ne__ = interp2app(W_Dtype.descr_ne),
    __getitem__ = interp2app(W_Dtype.descr_getitem),

    num = interp_attrproperty("num", cls=W_Dtype),
    kind = interp_attrproperty("kind", cls=W_Dtype),
    char = interp_attrproperty("char", cls=W_Dtype),
    type = interp_attrproperty_w("w_box_type", cls=W_Dtype),
    itemsize = GetSetProperty(W_Dtype.descr_get_itemsize),
    alignment = GetSetProperty(W_Dtype.descr_get_alignment),
    shape = GetSetProperty(W_Dtype.descr_get_shape),
    name = interp_attrproperty('name', cls=W_Dtype),
    fields = GetSetProperty(W_Dtype.descr_get_fields),
    names = GetSetProperty(W_Dtype.descr_get_names),
    str = GetSetProperty(W_Dtype.descr_get_str),
)
W_Dtype.typedef.acceptable_as_base_class = False

if sys.byteorder == 'little':
    byteorder_prefix = '<'
    nonnative_byteorder_prefix = '>'
else:
    byteorder_prefix = '>'
    nonnative_byteorder_prefix = '<'


def set_typeDict(space, w_type_dict):
    cache = get_dtype_cache(space)
    cache.w_type_dict = w_type_dict

class DtypeCache(object):
    w_type_dict = None

    def __init__(self, space):
        self.w_booldtype = W_Dtype(
            types.Bool(),
            num=0,
            kind=BOOLLTR,
            name="bool",
            char="?",
            w_box_type=space.gettypefor(interp_boxes.W_BoolBox),
            builtin_type=space.w_bool,
        )
        self.w_int8dtype = W_Dtype(
            types.Int8(),
            num=1,
            kind=SIGNEDLTR,
            name="int8",
            char="b",
            w_box_type=space.gettypefor(interp_boxes.W_Int8Box)
        )
        self.w_uint8dtype = W_Dtype(
            types.UInt8(),
            num=2,
            kind=UNSIGNEDLTR,
            name="uint8",
            char="B",
            w_box_type=space.gettypefor(interp_boxes.W_UInt8Box),
        )
        self.w_int16dtype = W_Dtype(
            types.Int16(),
            num=3,
            kind=SIGNEDLTR,
            name="int16",
            char="h",
            w_box_type=space.gettypefor(interp_boxes.W_Int16Box),
        )
        self.w_uint16dtype = W_Dtype(
            types.UInt16(),
            num=4,
            kind=UNSIGNEDLTR,
            name="uint16",
            char="H",
            w_box_type=space.gettypefor(interp_boxes.W_UInt16Box),
        )
        self.w_int32dtype = W_Dtype(
            types.Int32(),
            num=5,
            kind=SIGNEDLTR,
            name="int32",
            char="i",
            w_box_type=space.gettypefor(interp_boxes.W_Int32Box),
       )
        self.w_uint32dtype = W_Dtype(
            types.UInt32(),
            num=6,
            kind=UNSIGNEDLTR,
            name="uint32",
            char="I",
            w_box_type=space.gettypefor(interp_boxes.W_UInt32Box),
        )
        if LONG_BIT == 32:
            name = "int32"
        elif LONG_BIT == 64:
            name = "int64"
        self.w_longdtype = W_Dtype(
            types.Long(),
            num=7,
            kind=SIGNEDLTR,
            name=name,
            char="l",
            w_box_type=space.gettypefor(interp_boxes.W_LongBox),
            builtin_type=space.w_int,
        )
        self.w_ulongdtype = W_Dtype(
            types.ULong(),
            num=8,
            kind=UNSIGNEDLTR,
            name="u" + name,
            char="L",
            w_box_type=space.gettypefor(interp_boxes.W_ULongBox),
        )
        self.w_int64dtype = W_Dtype(
            types.Int64(),
            num=9,
            kind=SIGNEDLTR,
            name="int64",
            char="q",
            w_box_type=space.gettypefor(interp_boxes.W_Int64Box),
        )
        self.w_uint64dtype = W_Dtype(
            types.UInt64(),
            num=10,
            kind=UNSIGNEDLTR,
            name="uint64",
            char="Q",
            w_box_type=space.gettypefor(interp_boxes.W_UInt64Box),
        )
        self.w_float32dtype = W_Dtype(
            types.Float32(),
            num=11,
            kind=FLOATINGLTR,
            name="float32",
            char="f",
            w_box_type=space.gettypefor(interp_boxes.W_Float32Box),
        )
        self.w_float64dtype = W_Dtype(
            types.Float64(),
            num=12,
            kind=FLOATINGLTR,
            name="float64",
            char="d",
            w_box_type = space.gettypefor(interp_boxes.W_Float64Box),
            builtin_type=space.w_float,
        )
        self.w_longlongdtype = W_Dtype(
            types.Int64(),
            num=9,
            kind=SIGNEDLTR,
            name='int64',
            char='q',
            w_box_type = space.gettypefor(interp_boxes.W_LongLongBox),
            builtin_type=space.w_long,
        )
        self.w_ulonglongdtype = W_Dtype(
            types.UInt64(),
            num=10,
            kind=UNSIGNEDLTR,
            name='uint64',
            char='Q',
            w_box_type = space.gettypefor(interp_boxes.W_ULongLongBox),
        )
        self.w_stringdtype = W_Dtype(
            types.StringType(0),
            num=18,
            kind=STRINGLTR,
            name='string',
            char='S',
            w_box_type = space.gettypefor(interp_boxes.W_StringBox),
            builtin_type=space.w_str,
        )
        self.w_unicodedtype = W_Dtype(
            types.UnicodeType(0),
            num=19,
            kind=UNICODELTR,
            name='unicode',
            char='U',
            w_box_type = space.gettypefor(interp_boxes.W_UnicodeBox),
            builtin_type=space.w_unicode,
        )
        self.w_voiddtype = W_Dtype(
            types.VoidType(0),
            num=20,
            kind=VOIDLTR,
            name='void',
            char='V',
            w_box_type = space.gettypefor(interp_boxes.W_VoidBox),
            builtin_type=space.gettypefor(Buffer),
        )
        self.builtin_dtypes = [
            self.w_booldtype, self.w_int8dtype, self.w_uint8dtype,
            self.w_int16dtype, self.w_uint16dtype, self.w_int32dtype,
            self.w_uint32dtype, self.w_longdtype, self.w_ulongdtype,
            self.w_longlongdtype, self.w_ulonglongdtype,
            self.w_float32dtype,
            self.w_float64dtype, self.w_stringdtype, self.w_unicodedtype,
            self.w_voiddtype,
        ]
        self.dtypes_by_num_bytes = sorted(
            (dtype.itemtype.get_element_size(), dtype)
            for dtype in self.builtin_dtypes
        )
        self.dtypes_by_name = {}
        for dtype in self.builtin_dtypes:
            self.dtypes_by_name[dtype.char] = dtype
        self.dtypes_by_name["p"] = self.w_longdtype
        self.nonnative_dtypes = {
            self.w_booldtype: types.NonNativeBool(),
            self.w_int16dtype: types.NonNativeInt16(),
            self.w_int32dtype: types.NonNativeInt32(),
            self.w_longdtype: types.NonNativeLong(),
        }

        typeinfo_full = {
            'LONGLONG': self.w_int64dtype,
            'SHORT': self.w_int16dtype,
            'VOID': self.w_voiddtype,
            #'LONGDOUBLE':,
            'UBYTE': self.w_uint8dtype,
            'UINTP': self.w_ulongdtype,
            'ULONG': self.w_ulongdtype,
            'LONG': self.w_longdtype,
            'UNICODE': self.w_unicodedtype,
            #'OBJECT',
            'ULONGLONG': self.w_ulonglongdtype,
            'STRING': self.w_stringdtype,
            #'CDOUBLE',
            #'DATETIME',
            'UINT': self.w_uint32dtype,
            'INTP': self.w_longdtype,
            #'HALF',
            'BYTE': self.w_int8dtype,
            #'CFLOAT': ,
            #'TIMEDELTA',
            'INT': self.w_int32dtype,
            'DOUBLE': self.w_float64dtype,
            'USHORT': self.w_uint16dtype,
            'FLOAT': self.w_float32dtype,
            'BOOL': self.w_booldtype,
            #, 'CLONGDOUBLE']
        }
        typeinfo_partial = {
            'Generic': interp_boxes.W_GenericBox,
            'Character': interp_boxes.W_CharacterBox,
            'Flexible': interp_boxes.W_FlexibleBox,
            'Inexact': interp_boxes.W_InexactBox,
            'Integer': interp_boxes.W_IntegerBox,
            'SignedInteger': interp_boxes.W_SignedIntegerBox,
            'UnsignedInteger': interp_boxes.W_UnsignedIntegerBox,
            #'ComplexFloating',
            'Number': interp_boxes.W_NumberBox,
            'Floating': interp_boxes.W_FloatingBox
        }
        w_typeinfo = space.newdict()
        for k, v in typeinfo_partial.iteritems():
            space.setitem(w_typeinfo, space.wrap(k), space.gettypefor(v))
        for k, dtype in typeinfo_full.iteritems():
            itemsize = dtype.itemtype.get_element_size()
            items_w = [space.wrap(dtype.char),
                       space.wrap(dtype.num),
                       space.wrap(itemsize * 8), # in case of changing
                       # number of bits per byte in the future
                       space.wrap(itemsize or 1)]
            if dtype.is_int_type():
                if dtype.kind == BOOLLTR:
                    w_maxobj = space.wrap(1)
                    w_minobj = space.wrap(0)
                elif dtype.is_signed():
                    w_maxobj = space.wrap(r_longlong((1 << (itemsize*8 - 1))
                                          - 1))
                    w_minobj = space.wrap(r_longlong(-1) << (itemsize*8 - 1))
                else:
                    w_maxobj = space.wrap(r_ulonglong(1 << (itemsize*8)) - 1)
                    w_minobj = space.wrap(0)
                items_w = items_w + [w_maxobj, w_minobj]
            items_w = items_w + [dtype.w_box_type]

            w_tuple = space.newtuple(items_w)
            space.setitem(w_typeinfo, space.wrap(k), w_tuple)
        self.w_typeinfo = w_typeinfo

def get_dtype_cache(space):
    return space.fromcache(DtypeCache)
