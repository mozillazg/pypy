
from pypy.jit.metainterp.resoperation import rop, opclasses

NEW_WITH_VTABLE = opclasses[rop.NEW_WITH_VTABLE]

class Virtual(NEW_WITH_VTABLE):
    is_mutable = True

    def __init__(self, pval):
        NEW_WITH_VTABLE.__init__(self, pval)
        self._fields = {} # XXX convert from dict to a list
        self._is_forced = False

    def getfield(self, ofs, default):
        return self._fields.get(ofs, default)

    def setfield(self, ofs, fieldvalue):
        self._fields[ofs] = fieldvalue

    def getknownclass(self):
        return self.getarg(0)

    def setknownclass(self, cls):
        pass # ignore

    def is_nonnull(self):
        return True

    def is_null(self):
        return False

    def _copy_extra_attrs(self, new):
        raise Exception("Virtual should not be forwarded")
    
    def force(self, optimizer):
        if not self._is_forced:
            optimizer.emit_operation(self)
            self._is_forced = True
        return self

    def is_virtual(self):
        return not self._is_forced

    def is_forced_virtual(self):
        return self._is_forced
