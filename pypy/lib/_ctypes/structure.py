
from _ctypes.basics import _CData

class StructureMeta(type):
    def __new__(self, name, cls, typedict):
        return type.__new__(self, name, cls, typedict)

class Structure(_CData):
    __metaclass__ = StructureMeta
