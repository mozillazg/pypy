
""" Mutable subclasses for each of ResOperation.
"""

from pypy.tool.sourcetools import func_with_new_name
from pypy.jit.metainterp.resoperation import opclasses, opclasses_mutable, rop,\
     INT, REF, ConstInt, Const, ConstPtr
from pypy.jit.metainterp.optimizeopt.intutils import ImmutableIntUnbounded,\
     ConstantIntBound, IntBound
from pypy.jit.metainterp.virtualmodel import Virtual

class __extend__(ConstInt):
    def getintbound(self):
        return ConstantIntBound(self.getint())

    def getboolres(self):
        return False # for optimization

class __extend__(ConstPtr):
    def is_virtual(self):
        return False

    def is_forced_virtual(self):
        return False

class __extend__(Const):
    def getlastguardpos(self):
        return -1

    def force(self, _):
        return self

    def is_nonnull(self):
        return self.nonnull()

    def is_null(self):
        return not self.nonnull()

opclasses_mutable[rop.NEW_WITH_VTABLE] = Virtual

def create_mutable_subclasses():
    def addattr(cls, attr, default_value=None):
        if hasattr(cls, 'attributes_to_copy'):
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

    def int_is_null(self):
        return False

    def int_is_nonnull(self):
        intbound = self.getintbound()
        if intbound is not None:
            if intbound.known_gt(IntBound(0, 0)) or \
               intbound.known_lt(IntBound(0, 0)):
                return True
            return False
        return False

    def ref_is_null(self):
        return False

    def ref_is_nonnull(self):
        return self.getknownclass() is not None or self.getknownnonnull()

    imm_int_unbound = ImmutableIntUnbounded()
    for i, cls in enumerate(opclasses):
        if cls is None:
            continue
        elif opclasses_mutable[cls.getopnum()] is not None:
            addattr(opclasses_mutable[cls.getopnum()], 'lastguardpos')
            continue
        else:
            class Mutable(cls):
                is_mutable = True
                attributes_to_copy = []

                def force(self, _):
                    return self
                def is_virtual(self):
                    return False
                def is_forced_virtual(self):
                    return False

            if cls.is_guard() or cls.getopnum() == rop.FINISH:
                addattr(Mutable, 'failargs')
            if cls.is_guard():
                addattr(Mutable, 'descr') # mutable guards have descrs
            if cls.type == INT:
                # all the integers have bounds
                addattr(Mutable, 'intbound', imm_int_unbound)
                addattr(Mutable, 'boolres', False)
                Mutable.is_nonnull = int_is_nonnull
                Mutable.is_null = int_is_null
            elif cls.type == REF:
                addattr(Mutable, 'knownclass', None)
                addattr(Mutable, 'knownnonnull', False)
                Mutable.is_nonnull = ref_is_nonnull
                Mutable.is_null = ref_is_null
            # for tracking last guard and merging GUARD_VALUE with
            # GUARD_NONNULL etc
            addattr(Mutable, 'lastguardpos', -1)
            Mutable.__name__ = cls.__name__ + '_mutable'
            if Mutable.attributes_to_copy:
                make_new_copy_function(Mutable, cls)
            opclasses_mutable[i] = Mutable

create_mutable_subclasses()
