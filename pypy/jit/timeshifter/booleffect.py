from pypy.jit.timeshifter import rvalue

class Effect(object):
    def learn_boolvalue(self, jitstate, boolval):
        if boolval:
            return self._apply(jitstate)
        else:
            return self._apply_reverse(jitstate)

    def _apply(self, jitstate):
        return True

    def _apply_reverse(self, jitstate):
        return True

class PtrIsNonZeroEffect(Effect):
    def __init__(self, ptrbox, reverse=False):
        assert isinstance(ptrbox, rvalue.AbstractPtrRedBox)
        self.ptrbox = ptrbox
        self.reverse = reverse

    def learn_boolvalue(self, jitstate, boolval):
        return self.ptrbox.learn_nonzeroness(jitstate, boolval ^ self.reverse)

    def copy(self, memo):
        return PtrIsNonZeroEffect(self.ptrbox.copy(memo), self.reverse)

