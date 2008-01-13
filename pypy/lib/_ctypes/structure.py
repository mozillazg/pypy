
from _ctypes.basics import _CData, _CDataMeta

class StructureMeta(_CDataMeta):
    def __new__(self, name, cls, typedict):
        return type.__new__(self, name, cls, typedict)

class Structure(_CData):
    __metaclass__ = StructureMeta
