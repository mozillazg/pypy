
import _rawffi
from _ctypes.basics import _CData, _CDataMeta, keepalive_key,\
     store_reference, ensure_objects, CArgObject
import inspect

def round_up(size, alignment):
    return (size + alignment - 1) & -alignment

def size_alignment_pos(fields, is_union=False):
    import ctypes
    size = 0
    alignment = 1
    pos = []
    for field in fields:
        fieldname = field[0]
        ctype = field[1]
        fieldsize = ctypes.sizeof(ctype)
        fieldalignment = ctypes.alignment(ctype)
        alignment = max(alignment, fieldalignment)
        if is_union:
            pos.append(0)
            size = max(size, fieldsize)
        else:
            size = round_up(size, fieldalignment)
            pos.append(size)
            size += fieldsize
    size = round_up(size, alignment)
    return size, alignment, pos

def names_and_fields(_fields_, superclass, zero_offset=False, anon=None,
                     is_union=False):
    # _fields_: list of (name, ctype, [optional_bitfield])
    if isinstance(_fields_, tuple):
        _fields_ = list(_fields_)
    for f in _fields_:
        tp = f[1]
        if not isinstance(tp, _CDataMeta):
            raise TypeError("Expected CData subclass, got %s" % (tp,))
        if isinstance(tp, StructOrUnionMeta):
            tp._make_final()
    import ctypes
    all_fields = []
    for cls in inspect.getmro(superclass):
        all_fields += getattr(cls, '_fields_', [])
    all_fields += _fields_
    names = [f[0] for f in all_fields]
    rawfields = [(f[0], f[1]._ffishape)
                 for f in all_fields]
    if not zero_offset:
        _, _, pos = size_alignment_pos(all_fields, is_union)
    else:
        pos = [0] * len(all_fields)
    fields = {}
    for i, field in enumerate(all_fields):
        name = field[0]
        ctype = field[1]
        fields[name] = Field(name, pos[i], ctypes.sizeof(ctype), ctype, i)
    if anon:
        resnames = []
        for i, (name, value) in enumerate(all_fields):
            if name in anon:
                for subname in value._names:
                    resnames.append(subname)
                    relpos = pos[i] + value._fieldtypes[subname].offset
                    subvalue = value._fieldtypes[subname].ctype
                    fields[subname] = Field(subname, relpos,
                                            ctypes.sizeof(subvalue), subvalue,
                                            i)
                    # XXX we never set rawfields here, let's wait for a test
            else:
                resnames.append(name)
        names = resnames
    return names, rawfields, fields

class Field(object):
    def __init__(self, name, offset, size, ctype, num):
        for k in ('name', 'offset', 'size', 'ctype', 'num'):
            self.__dict__[k] = locals()[k]

    def __setattr__(self, name, value):
        raise AttributeError(name)

    def __repr__(self):
        return "<Field '%s' offset=%d size=%d>" % (self.name, self.offset,
                                                   self.size)

# ________________________________________________________________

def _set_shape(tp, rawfields, is_union=False):
    tp._ffistruct = _rawffi.Structure(rawfields, is_union)
    tp._ffiargshape = tp._ffishape = (tp._ffistruct, 1)
    tp._fficompositesize = tp._ffistruct.size

def struct_getattr(self, name):
    if name not in ('_fields_', '_fieldtypes'):
        if hasattr(self, '_fieldtypes') and name in self._fieldtypes:
            return self._fieldtypes[name]
    return _CDataMeta.__getattribute__(self, name)

def struct_setattr(self, name, value):
    if name == '_fields_':
        if self.__dict__.get('_fields_', None) is not None:
            raise AttributeError("_fields_ is final")
        if self in [v for k, v in value]:
            raise AttributeError("Structure or union cannot contain itself")
        self._names, rawfields, self._fieldtypes = names_and_fields(
            value, self.__bases__[0], False,
            self.__dict__.get('_anonymous_', None), self._is_union)
        _CDataMeta.__setattr__(self, '_fields_', value)
        _set_shape(self, rawfields, self._is_union)
        return
    _CDataMeta.__setattr__(self, name, value)

class StructOrUnionMeta(_CDataMeta):

    def __new__(self, name, cls, typedict):
        res = type.__new__(self, name, cls, typedict)
        if isinstance(cls[0], StructOrUnionMeta):
            cls[0]._make_final()
        if '_fields_' in typedict:
            if not hasattr(typedict.get('_anonymous_', []), '__iter__'):
                raise TypeError("Anonymous field must be iterable")
            for item in typedict.get('_anonymous_', []):
                if item not in dict(typedict['_fields_']):
                    raise AttributeError("Anonymous field not found")
            res._names, rawfields, res._fieldtypes = names_and_fields(
                typedict['_fields_'], cls[0], False,
                typedict.get('_anonymous_', None), self._is_union)
            _set_shape(res, rawfields, self._is_union)

        return res

    def _make_final(self):
        if self is StructOrUnion:
            return
        if '_fields_' not in self.__dict__:
            self._fields_ = []
            self._names = []
            self._fieldtypes = {}
            _set_shape(self, [], self._is_union)

    __getattr__ = struct_getattr
    __setattr__ = struct_setattr

    def from_address(self, address):
        instance = self.__new__(self)
        instance.__dict__['_buffer'] = self._ffistruct.fromaddress(address)
        return instance

    def _sizeofinstances(self):
        if not hasattr(self, '_ffistruct'):
            return 0
        return self._ffistruct.size

    def _alignmentofinstances(self):
        return self._ffistruct.alignment

    def from_param(self, value):
        if isinstance(value, tuple):
            try:
                value = self(*value)
            except Exception, e:
                # XXX CPython does not even respect the exception type
                raise RuntimeError("(%s) %s: %s" % (self.__name__, type(e), e))
        return _CDataMeta.from_param(self, value)

    def _CData_output(self, resarray, base=None, index=-1):
        res = self.__new__(self)
        ffistruct = self._ffistruct.fromaddress(resarray.buffer)
        res.__dict__['_buffer'] = ffistruct
        res.__dict__['_base'] = base
        res.__dict__['_index'] = index
        return res
    
    def _CData_retval(self, resbuffer):
        res = self.__new__(self)
        res.__dict__['_buffer'] = resbuffer
        res.__dict__['_base'] = None
        res.__dict__['_index'] = -1
        return res

class StructOrUnion(_CData):
    __metaclass__ = StructOrUnionMeta

    def __new__(cls, *args, **kwds):
        self = super(_CData, cls).__new__(cls, *args, **kwds)
        if hasattr(cls, '_ffistruct'):
            self.__dict__['_buffer'] = self._ffistruct(autofree=True)
        return self

    def __init__(self, *args, **kwds):
        type(self)._make_final()
        if len(args) > len(self._names):
            raise TypeError("too many initializers")
        for name, arg in zip(self._names, args):
            if name in kwds:
                raise TypeError("duplicate value for argument %r" % (
                    name,))
            self.__setattr__(name, arg)
        for name, arg in kwds.items():
            self.__setattr__(name, arg)

    def _subarray(self, fieldtype, name):
        """Return a _rawffi array of length 1 whose address is the same as
        the address of the field 'name' of self."""
        address = self._buffer.fieldaddress(name)
        A = _rawffi.Array(fieldtype._ffishape)
        return A.fromaddress(address, 1)

    def __setattr__(self, name, value):
        try:
            field = self._fieldtypes[name]
        except KeyError:
            return _CData.__setattr__(self, name, value)
        fieldtype = field.ctype
        cobj = fieldtype.from_param(value)
        if ensure_objects(cobj) is not None:
            key = keepalive_key(field.num)
            store_reference(self, key, cobj._objects)
        arg = cobj._get_buffer_value()
        if fieldtype._fficompositesize is not None:
            from ctypes import memmove
            dest = self._buffer.fieldaddress(name)
            memmove(dest, arg, fieldtype._fficompositesize)
        else:
            self._buffer.__setattr__(name, arg)

    def __getattribute__(self, name):
        if name == '_fieldtypes':
            return _CData.__getattribute__(self, '_fieldtypes')
        try:
            field = self._fieldtypes[name]
        except KeyError:
            return _CData.__getattribute__(self, name)
        fieldtype = field.ctype
        offset = field.num
        suba = self._subarray(fieldtype, name)
        return fieldtype._CData_output(suba, self, offset)

    def _get_buffer_for_param(self):
        return self

    def _get_buffer_value(self):
        return self._buffer.buffer


class StructureMeta(StructOrUnionMeta):
    _is_union = False

class Structure(StructOrUnion):
    __metaclass__ = StructureMeta
