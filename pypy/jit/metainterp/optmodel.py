
""" Mutable subclasses for each of ResOperation.
"""

from pypy.tool.sourcetools import func_with_new_name
from pypy.jit.metainterp.resoperation import opclasses, opclasses_mutable

def create_mutable_subclasses():
    def addattr(cls, attr, default_value=None):
        def getter(self):
            return getattr(self, '_' + attr)
        def setter(self, value):
            setattr(self, '_' + attr, value)
        setattr(cls, '_' + attr, default_value)
        setattr(cls, 'get_' + attr, func_with_new_name(getter, 'get_' + attr))
        setattr(cls, 'set_' + attr, func_with_new_name(setter, 'set_' + attr))

    for i, cls in enumerate(opclasses):
        if cls is None:
            Mutable = None
        else:
            class Mutable(cls):
                is_mutable = True
            if cls.is_guard():
                addattr(Mutable, 'failargs')
            Mutable.__name__ = cls.__name__ + '_mutable'
        assert len(opclasses_mutable) == i
        opclasses_mutable.append(Mutable)
    assert len(opclasses) == len(opclasses_mutable)

create_mutable_subclasses()
