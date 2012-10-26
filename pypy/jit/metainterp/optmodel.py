
""" Mutable subclasses for each of ResOperation.
"""

from pypy.tool.sourcetools import func_with_new_name
from pypy.jit.metainterp.resoperation import opclasses, opclasses_mutable, rop,\
     INT, REF, ConstInt, Const
from pypy.jit.metainterp.optimizeopt.intutils import ImmutableIntUnbounded,\
     ConstantIntBound

class __extend__(ConstInt):
    def getintbound(self):
        return ConstantIntBound(self.getint())

    def getboolbox(self):
        return False # for optimization

class __extend__(Const):
    def getlastguardpos(self):
        return -1

    def force(self, _):
        return self

def create_mutable_subclasses():
    def addattr(cls, attr, default_value=None):
        cls.attributes_to_copy.append('_' + attr)
        def getter(self):
            return getattr(self, '_' + attr)
        def setter(self, value):
            setattr(self, '_' + attr, value)
        setattr(cls, '_' + attr, default_value)
        setattr(cls, 'get' + attr, func_with_new_name(getter, 'get' + attr))
        setattr(cls, 'set' + attr, func_with_new_name(setter, 'set' + attr))

    def make_new_copy_function(cls, paren_cls):
        def _copy_extra_attrs(self, new):
            paren_cls._copy_extra_attrs(self, new)
            for attr in cls.attributes_to_copy:
                setattr(new, attr, getattr(self, attr))
        cls._copy_extra_attrs = _copy_extra_attrs

    imm_int_unbound = ImmutableIntUnbounded()
    for i, cls in enumerate(opclasses):
        if cls is None:
            Mutable = None
        else:
            class Mutable(cls):
                is_mutable = True
                attributes_to_copy = []

                if cls.getopnum() in (rop.NEW_WITH_VTABLE, rop.NEW):
                    def force(self, optimizer):
                        optimizer.emit_operation(self)
                        return self
                else:
                    def force(self, _):
                        return self
            if cls.is_guard() or cls.getopnum() == rop.FINISH:
                addattr(Mutable, 'failargs')
            if cls.is_guard():
                addattr(Mutable, 'descr') # mutable guards have descrs
            if cls.type == INT:
                # all the integers have bounds
                addattr(Mutable, 'intbound', imm_int_unbound)
                addattr(Mutable, 'boolbox', False)
            elif cls.type == REF:
                addattr(Mutable, 'knownclass', None)
            # for tracking last guard and merging GUARD_VALUE with
            # GUARD_NONNULL etc
            addattr(Mutable, 'lastguardpos', -1)
            Mutable.__name__ = cls.__name__ + '_mutable'
            if Mutable.attributes_to_copy:
                make_new_copy_function(Mutable, cls)
        assert len(opclasses_mutable) == i
        opclasses_mutable.append(Mutable)
    assert len(opclasses) == len(opclasses_mutable)

create_mutable_subclasses()
