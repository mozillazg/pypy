
""" Mutable subclasses for each of ResOperation.
"""

from pypy.tool.sourcetools import func_with_new_name
from pypy.jit.metainterp.resoperation import opclasses, opclasses_mutable, rop

def create_mutable_subclasses():
    def addattr(cls, attr, default_value=None):
        def getter(self):
            return getattr(self, '_' + attr)
        def setter(self, value):
            setattr(self, '_' + attr, value)
        setattr(cls, '_' + attr, default_value)
        setattr(cls, 'get' + attr, func_with_new_name(getter, 'get' + attr))
        setattr(cls, 'set' + attr, func_with_new_name(setter, 'set' + attr))

    for i, cls in enumerate(opclasses):
        if cls is None:
            Mutable = None
        else:
            class Mutable(cls):
                is_mutable = True
            if cls.is_guard() or cls.getopnum() == rop.FINISH:
                addattr(Mutable, 'failargs')
            if cls.is_guard():
                addattr(Mutable, 'descr') # mutable guards have descrs
            Mutable.__name__ = cls.__name__ + '_mutable'
        assert len(opclasses_mutable) == i
        opclasses_mutable.append(Mutable)
    assert len(opclasses) == len(opclasses_mutable)

create_mutable_subclasses()
