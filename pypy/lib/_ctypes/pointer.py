
import _ffi

class PointerType(type):
    def __new__(self, name, cls, typedict):
        d = dict(
            size   = _ffi.sizeof('P'),
            align  = _ffi.alignment('P'),
            length = 1
        )
        # XXX check if typedict['_type_'] is any sane
        # XXX remember about paramfunc
        obj = type.__new__(self, name, cls, typedict)
        for k, v in d.iteritems():
            setattr(obj, k, v)
        return obj

class _Pointer(object):
    __metaclass__ = PointerType

    def __init__(self, value=None):
        if value is None:
            self.is_null = True
        else:
            self.value = value
        # we should later check why exactly this is the case
        try:
            type(self).__dict__['_type_']
        except KeyError:
            raise TypeError("%s has no _type_" % self.__class__)
