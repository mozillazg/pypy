
""" Mutable subclasses for each of ResOperation.
"""

from pypy.jit.metainterp.resoperation import opclasses, opclasses_mutable

def create_mutable_subclasses():
    for i, cls in enumerate(opclasses):
        if cls is None:
            Mutable = None
        else:
            class Mutable(cls):
                is_mutable = True
            Mutable.__name__ = cls.__name__ + '_mutable'
        assert len(opclasses_mutable) == i
        opclasses_mutable.append(Mutable)

create_mutable_subclasses()
