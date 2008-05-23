
from struct import pack, unpack
from pypy.rpython.extregistry import ExtRegistryEntry

class UnpackEntry(ExtRegistryEntry):
    _about_ = unpack

    def compute_result_annotation(self, s_fmt, s_s):
        from pypy.annotation import model as annmodel
        if not isinstance(s_s, annmodel.SomeString):
            raise TypeError("Got %s, string expected" % (s_s,))
        if not s_fmt.is_constant():
            raise ValueError("Can only use struct.unpack with first argument constant in RPython")
        
