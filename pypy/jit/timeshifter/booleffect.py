from pypy.jit.timeshifter import rvalue

class Effect(object):
    def __init__(self, reverse):
        self.reverse = reverse

    def learn_boolvalue(self, jitstate, boolval):
        if boolval ^ self.reverse:
            return self._apply(jitstate)
        else:
            return self._apply_reverse(jitstate)

    def _apply(self, jitstate):
        return True

    def _apply_reverse(self, jitstate):
        return True

class PtrIsNonZeroEffect(Effect):
    def __init__(self, ptrbox, reverse=False):
        Effect.__init__(self, reverse)
        assert isinstance(ptrbox, rvalue.AbstractPtrRedBox)
        self.ptrbox = ptrbox

    def learn_boolvalue(self, jitstate, boolval):
        return self.ptrbox.learn_nonzeroness(jitstate, boolval ^ self.reverse)

    def copy(self, memo):
        return PtrIsNonZeroEffect(self.ptrbox.copy(memo), self.reverse)

class PtrEqualEffect(Effect):
    def __init__(self, ptrbox1, ptrbox2, reverse=False):
        Effect.__init__(self, reverse)
        assert isinstance(ptrbox1, rvalue.AbstractPtrRedBox)
        assert isinstance(ptrbox2, rvalue.AbstractPtrRedBox)
        self.ptrbox1 = ptrbox1
        self.ptrbox2 = ptrbox2

    def _apply(self, jitstate):
        # the pointers _are_ equal
        if self.ptrbox1.is_constant():
            self.ptrbox2.genvar = self.ptrbox1.genvar
            return True
        if self.ptrbox2.is_constant():
            self.ptrbox1.genvar = self.ptrbox2.genvar
            return True
        # XXX can do more?
        return True

    def copy(self, memo):
        return PtrEqualEffect(self.ptrbox1.copy(memo),
                              self.ptrbox2.copy(memo), self.reverse)
