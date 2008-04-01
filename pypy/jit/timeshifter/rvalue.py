from pypy.rpython.lltypesystem import lltype, llmemory
from pypy.rpython.ootypesystem import ootype

class Memo(object):
    _annspecialcase_ = 'specialize:ctr_location'

    def __init__(self):
        self.boxes = {}
        self.containers = {}

def enter_block_memo():
    return Memo()

def freeze_memo():
    return Memo()

def exactmatch_memo(force_merge=False):
    memo = Memo()
    memo.partialdatamatch = {}
    memo.forget_nonzeroness = {}
    memo.force_merge=force_merge
    return memo

def copy_memo():
    return Memo()

def unfreeze_memo():
    return Memo()

def make_vrti_memo():
    return Memo()

class DontMerge(Exception):
    pass

class LLTypeMixin(object):
    _mixin_ = True

    def _revealconst(self, gv):
        return gv.revealconst(llmemory.Address)

class OOTypeMixin(object):
    _mixin_ = True

    def _revealconst(self, gv):
        return gv.revealconst(ootype.Object)


class RedBox(object):
    _attrs_ = ['genvar', 'most_recent_frozen']
    most_recent_frozen = None

    def __init__(self, genvar=None):
        self.genvar = genvar    # None or a genvar

    def __repr__(self):
        if not self.genvar:
            return '<dummy>'
        else:
            return '<%r>' % (self.genvar,)

    def is_constant(self):
        return bool(self.genvar) and self.genvar.is_const
    
    def getkind(self):
        if self.genvar is None:
            return None
        return self.genvar.getkind()

    def getgenvar(self, jitstate):
        return self.genvar

    def setgenvar(self, newgenvar):
        assert not self.is_constant()
        self.genvar = newgenvar

    def learn_boolvalue(self, jitstate, boolval):
        return True

    def enter_block(self, incoming, memo):
        memo = memo.boxes
        if not self.is_constant() and self not in memo:
            incoming.append(self)
            memo[self] = None

    def forcevar(self, jitstate, memo, forget_nonzeroness):
        if self.is_constant():
            # cannot mutate constant boxes in-place
            builder = jitstate.curbuilder
            box = self.copy(memo)
            box.genvar = builder.genop_same_as(self.genvar)
            return box
        else:
            return self

    def replace(self, memo):
        memo = memo.boxes
        return memo.setdefault(self, self)

    def see_promote(self):
        if self.most_recent_frozen is not None:
            self.most_recent_frozen.will_be_promoted = True
            self.most_recent_frozen = None


def ll_redboxcls(TYPE):
    assert TYPE is not lltype.Void, "cannot make red boxes of voids"
    return ll_redboxbuilder(TYPE)

def redboxbuilder_void(gv_value): return None
def redboxbuilder_int(gv_value): return IntRedBox(gv_value)
def redboxbuilder_dbl(gv_value): return DoubleRedBox(gv_value)
def redboxbuilder_ptr(gv_value): return PtrRedBox(gv_value)
def redboxbuilder_inst(gv_value): return InstanceRedBox(gv_value)
def redboxbuilder_bool(gv_value): return BoolRedBox(gv_value)

def ll_redboxbuilder(TYPE):
    if TYPE is lltype.Void:
        return redboxbuilder_void
    elif isinstance(TYPE, lltype.Ptr):
        return redboxbuilder_ptr
    elif TYPE is lltype.Float:
        return redboxbuilder_dbl
    elif isinstance(TYPE, ootype.OOType):
        return redboxbuilder_inst
    elif TYPE == lltype.Bool:
        return redboxbuilder_bool
    else:
        assert isinstance(TYPE, lltype.Primitive)
        # XXX what about long longs?
        return redboxbuilder_int

def ll_fromvalue(jitstate, value):
    "Make a constant RedBox from a low-level value."
    gv = ll_gv_fromvalue(jitstate, value)
    T = lltype.typeOf(value)
    cls = ll_redboxcls(T)
    return cls(gv)

def redbox_from_prebuilt_value(RGenOp, value):
    T = lltype.typeOf(value)
    gv = RGenOp.constPrebuiltGlobal(value)
    cls = ll_redboxcls(T)
    return cls(gv)

def ll_gv_fromvalue(jitstate, value):
    rgenop = jitstate.curbuilder.rgenop
    gv = rgenop.genconst(value)
    return gv

def ll_getvalue(box, T):
    "Return the content of a known-to-be-constant RedBox."
    return box.genvar.revealconst(T)


class IntRedBox(RedBox):
    "A red box that contains a constant integer-like value."

    def learn_boolvalue(self, jitstate, boolval):
        if self.is_constant():
            return self.genvar.revealconst(lltype.Bool) == boolval
        else:
            self.setgenvar(ll_gv_fromvalue(jitstate, boolval))
            return True

    def copy(self, memo):
        memo = memo.boxes
        try:
            return memo[self]
        except KeyError:
            result = memo[self] = IntRedBox(self.genvar)
            return result

    def freeze(self, memo):
        memo = memo.boxes
        try:
            return memo[self]
        except KeyError:
            result = self.most_recent_frozen
            if result is None:
                if self.is_constant():
                    result = FrozenIntConst(self.genvar)
                else:
                    result = FrozenIntVar()
                self.most_recent_frozen = result
            memo[self] = result
            return result

class BoolRedBox(RedBox):
    # XXX make true and false singletons?

    def __init__(self, genvar):
        RedBox.__init__(self, genvar)
        self.iftrue = []

    def learn_boolvalue(self, jitstate, boolval):
        if self.is_constant():
            return self.genvar.revealconst(lltype.Bool) == boolval
        else:
            self.setgenvar(ll_gv_fromvalue(jitstate, boolval))
            result = True
            for effect in self.iftrue:
                result = effect.learn_boolvalue(jitstate, boolval) and result
            self.iftrue = []
            return result
            
    def copy(self, memo):
        memoboxes = memo.boxes
        try:
            return memoboxes[self]
        except KeyError:
            result = memoboxes[self] = BoolRedBox(self.genvar)
            result.iftrue = [effect.copy(memo) for effect in self.iftrue]
            return result

    def freeze(self, memo):
        memo = memo.boxes
        try:
            return memo[self]
        except KeyError:
            if self.is_constant():
                result = FrozenBoolConst(self.genvar)
            else:
                result = FrozenBoolVar()
            memo[self] = result
            return result

class DoubleRedBox(RedBox):
    "A red box that contains a constant double-precision floating point value."

    def copy(self, memo):
        memo = memo.boxes
        try:
            return memo[self]
        except KeyError:
            result = memo[self] = DoubleRedBox(self.genvar)
            return result

    def freeze(self, memo):
        memo = memo.boxes
        try:
            return memo[self]
        except KeyError:
            if self.is_constant():
                result = FrozenDoubleConst(self.genvar)
            else:
                result = FrozenDoubleVar()
            memo[self] = result
            return result


class AccessInfo(object):
    def __init__(self):
        self.read_fields = 0
        self.write_fields = 0
        # XXX what else is needed?

    def __repr__(self):
        return "<AccessInfo read_fields=%s, write_fields=%s>" % (
                self.read_fields, self.write_fields)

    def copy(self):
        result = AccessInfo()
        result.read_fields = self.read_fields
        result.write_fields = self.write_fields


class AbstractPtrRedBox(RedBox):
    """
    Base class for PtrRedBox (lltype) and InstanceRedBox (ootype)
    """

    content = None   # or an AbstractContainer

    def __init__(self, genvar=None, known_nonzero=False):
        self.genvar = genvar    # None or a genvar
        if genvar is not None and genvar.is_const:
            known_nonzero = bool(self._revealconst(genvar))
        self.known_nonzero = known_nonzero
        self.access_info = AccessInfo()

    def setgenvar(self, newgenvar):
        RedBox.setgenvar(self, newgenvar)
        self.known_nonzero = (newgenvar.is_const and
                              bool(self._revealconst(newgenvar)))

    def setgenvar_hint(self, newgenvar, known_nonzero):
        RedBox.setgenvar(self, newgenvar)
        self.known_nonzero = known_nonzero

    def learn_nonzeroness(self, jitstate, nonzeroness):
        ok = True
        if nonzeroness:
            if self.is_constant():
                ok = self.known_nonzero   # not ok if constant zero
            else:
                self.known_nonzero = True
        else:
            if self.known_nonzero:
                ok = False
            elif not self.is_constant():
                assert self.genvar is not None
                kind = self.genvar.getkind()
                gv_null = jitstate.curbuilder.rgenop.genzeroconst(kind)
                self.setgenvar_hint(gv_null, known_nonzero=False)
        return ok

    learn_boolvalue = learn_nonzeroness

    def __repr__(self):
        if not self.genvar and self.content is not None:
            return '<virtual %s>' % (self.content,)
        else:
            return RedBox.__repr__(self)

    def copy(self, memo):
        boxmemo = memo.boxes
        try:
            result = boxmemo[self]
        except KeyError:
            result = self.__class__(self.genvar, self.known_nonzero)
            boxmemo[self] = result
            if self.content:
                result.content = self.content.copy(memo)
            # XXX is this correct?
            result.access_info = self.access_info
        assert isinstance(result, AbstractPtrRedBox)
        return result

    def replace(self, memo):
        boxmemo = memo.boxes
        try:
            result = boxmemo[self]
        except KeyError:
            boxmemo[self] = self
            if self.content:
                self.content.replace(memo)
            result = self
        assert isinstance(result, AbstractPtrRedBox)
        return result

    def freeze(self, memo):
        boxmemo = memo.boxes
        try:
            return boxmemo[self]
        except KeyError:
            future_usage = self.retrieve_future_usage()
            content = self.content
            if not self.genvar:
                from pypy.jit.timeshifter import rcontainer
                assert isinstance(content, rcontainer.VirtualContainer)
                result = self.FrozenPtrVirtual(future_usage)
                boxmemo[self] = result
                result.fz_content = content.freeze(memo)
                return result
            elif self.genvar.is_const:
                result = self.FrozenPtrConst(future_usage, self.genvar)
            elif content is None:
                result = self.FrozenPtrVar(future_usage, self.known_nonzero)
            else:
                # if self.content is not None, it's a PartialDataStruct
                from pypy.jit.timeshifter import rcontainer
                assert isinstance(content, rcontainer.PartialDataStruct)
                result = self.FrozenPtrVarWithPartialData(future_usage,
                                                          known_nonzero=True)
                boxmemo[self] = result
                result.fz_partialcontent = content.partialfreeze(memo)
                return result
            result.fz_access_info = self.access_info.copy()
            boxmemo[self] = result
            return result

    def getgenvar(self, jitstate):
        if not self.genvar:
            content = self.content
            from pypy.jit.timeshifter import rcontainer
            if isinstance(content, rcontainer.VirtualizableStruct):
                return content.getgenvar(jitstate)
            assert isinstance(content, rcontainer.VirtualContainer)
            content.force_runtime_container(jitstate)
            assert self.genvar
        return self.genvar

    def forcevar(self, jitstate, memo, forget_nonzeroness):
        from pypy.jit.timeshifter import rcontainer
        # xxx
        assert not isinstance(self.content, rcontainer.VirtualizableStruct)
        if self.is_constant():
            # cannot mutate constant boxes in-place
            builder = jitstate.curbuilder
            box = self.copy(memo)
            box.genvar = builder.genop_same_as(self.genvar)
        else:
            # force virtual containers
            self.getgenvar(jitstate)
            box = self

        if forget_nonzeroness:
            box.known_nonzero = False
        return box

    def enter_block(self, incoming, memo):
        if self.genvar:
            RedBox.enter_block(self, incoming, memo)
        if self.content:
            self.content.enter_block(incoming, memo)

    def op_getfield(self, jitstate, fielddesc):
        self.access_info.read_fields += 1
        self.learn_nonzeroness(jitstate, True)
        if self.content is not None:
            box = self.content.op_getfield(jitstate, fielddesc)
            if box is not None:
                return box
        gv_ptr = self.getgenvar(jitstate)
        box = fielddesc.generate_get(jitstate, gv_ptr)
        if fielddesc.immutable:
            self.remember_field(fielddesc, box)
        return box

    def op_setfield(self, jitstate, fielddesc, valuebox):
        self.access_info.write_fields += 1
        self.learn_nonzeroness(jitstate, True)
        gv_ptr = self.genvar
        if gv_ptr:
            fielddesc.generate_set(jitstate, gv_ptr,
                                   valuebox.getgenvar(jitstate))
        else:
            assert self.content is not None
            self.content.op_setfield(jitstate, fielddesc, valuebox)

    def remember_field(self, fielddesc, box):
        if self.genvar.is_const:
            return      # no point in remembering field then
        if self.content is None:
            from pypy.jit.timeshifter import rcontainer
            self.content = rcontainer.PartialDataStruct()
        self.content.remember_field(fielddesc, box)


class PtrRedBox(AbstractPtrRedBox, LLTypeMixin):

    def op_getsubstruct(self, jitstate, fielddesc):
        self.learn_nonzeroness(jitstate, True)
        gv_ptr = self.genvar
        if gv_ptr:
            return fielddesc.generate_getsubstruct(jitstate, gv_ptr)
        else:
            assert self.content is not None
            return self.content.op_getsubstruct(jitstate, fielddesc)


class InstanceRedBox(AbstractPtrRedBox, OOTypeMixin):
    pass


# ____________________________________________________________

class FrozenValue(object):
    """An abstract value frozen in a saved state.
    """
    will_be_promoted = False

    def is_constant_equal(self, box):
        return False

    def is_constant_nullptr(self):
        return False


class FrozenConst(FrozenValue):

    def exactmatch(self, box, outgoingvarboxes, memo):
        if self.is_constant_equal(box):
            return True
        else:
            if self.will_be_promoted and box.is_constant():
                raise DontMerge
            outgoingvarboxes.append(box)
            return False


class FrozenVar(FrozenValue):

    def exactmatch(self, box, outgoingvarboxes, memo):
        if self.will_be_promoted and box.is_constant():
            raise DontMerge
        memo = memo.boxes
        if self not in memo:
            memo[self] = box
            outgoingvarboxes.append(box)
            return True
        elif memo[self] is box:
            return True
        else:
            outgoingvarboxes.append(box)
            return False


class FrozenIntConst(FrozenConst):

    def __init__(self, gv_const):
        self.gv_const = gv_const

    def is_constant_equal(self, box):
        return (box.is_constant() and
                self.gv_const.revealconst(lltype.Signed) ==
                box.genvar.revealconst(lltype.Signed))

    def unfreeze(self, incomingvarboxes, memo):
        # XXX could return directly the original IntRedBox
        return IntRedBox(self.gv_const)


class FrozenIntVar(FrozenVar):

    def unfreeze(self, incomingvarboxes, memo):
        memo = memo.boxes
        if self not in memo:
            newbox = IntRedBox(None)
            incomingvarboxes.append(newbox)
            memo[self] = newbox
            return newbox
        else:
            return memo[self]


class FrozenBoolConst(FrozenConst):

    def __init__(self, gv_const):
        self.gv_const = gv_const

    def is_constant_equal(self, box):
        return (box.is_constant() and
                self.gv_const.revealconst(lltype.Bool) ==
                box.genvar.revealconst(lltype.Bool))

    def unfreeze(self, incomingvarboxes, memo):
        return BoolRedBox(self.gv_const)


class FrozenBoolVar(FrozenVar):

    def unfreeze(self, incomingvarboxes, memo):
        memo = memo.boxes
        if self not in memo:
            newbox = BoolRedBox(None)
            incomingvarboxes.append(newbox)
            memo[self] = newbox
            return newbox
        else:
            return memo[self]

class FrozenDoubleConst(FrozenConst):

    def __init__(self, gv_const):
        self.gv_const = gv_const

    def is_constant_equal(self, box):
        return (box.is_constant() and
                self.gv_const.revealconst(lltype.Float) ==
                box.genvar.revealconst(lltype.Float))

    def unfreeze(self, incomingvarboxes, memo):
        return DoubleRedBox(self.gv_const)


class FrozenDoubleVar(FrozenVar):

    def unfreeze(self, incomingvarboxes, memo):
        memo = memo.boxes
        if self not in memo:
            newbox = DoubleRedBox(None)
            incomingvarboxes.append(newbox)
            memo[self] = newbox
            return newbox
        else:
            return memo[self]


class FrozenAbstractPtrConst(FrozenConst):

    def __init__(self, future_usage, gv_const):
        FrozenConst.__init__(self, future_usage)
        self.gv_const = gv_const

    def is_constant_equal(self, box):
        return (box.is_constant() and
                self._revealconst(self.gv_const) ==
                self._revealconst(box.genvar))

    def is_constant_nullptr(self):
        return not self._revealconst(self.gv_const)

    def exactmatch(self, box, outgoingvarboxes, memo):
        assert isinstance(box, AbstractPtrRedBox)
        memo.partialdatamatch[box] = None     # could do better
        if self.is_constant_nullptr():
            memo.forget_nonzeroness[box] = None
        match = FrozenConst.exactmatch(self, box, outgoingvarboxes, memo)
        #if not memo.force_merge and not match:
        #    from pypy.jit.timeshifter.rcontainer import VirtualContainer
        #    if isinstance(box.content, VirtualContainer):
        #        raise DontMerge   # XXX recursive data structures?
        return match

    def unfreeze(self, incomingvarboxes, memo):
        return self.PtrRedBox(self.gv_const)


class FrozenPtrConst(FrozenAbstractPtrConst, LLTypeMixin):
    PtrRedBox = PtrRedBox

class FrozenInstanceConst(FrozenAbstractPtrConst, OOTypeMixin):
    PtrRedBox = InstanceRedBox


class AbstractFrozenPtrVar(FrozenVar):

    def __init__(self, future_usage, known_nonzero):
        FrozenVar.__init__(self, future_usage)
        self.known_nonzero = known_nonzero

    def exactmatch(self, box, outgoingvarboxes, memo):
        from pypy.jit.timeshifter.rcontainer import VirtualContainer
        assert isinstance(box, AbstractPtrRedBox)
        memo.partialdatamatch[box] = None
        if not self.known_nonzero:
            memo.forget_nonzeroness[box] = None
        match = FrozenVar.exactmatch(self, box, outgoingvarboxes, memo)
        if self.known_nonzero and not box.known_nonzero:
            match = False
        if not memo.force_merge:
            if isinstance(box.content, VirtualContainer):
                # heuristic: if a virtual is neither written to, nor read from
                # it might not be "important enough" to keep it virtual
                if not box.access_info.read_fields:
                    return match
                raise DontMerge   # XXX recursive data structures?
        return match

    def unfreeze(self, incomingvarboxes, memo):
        memo = memo.boxes
        if self not in memo:
            newbox = self.PtrRedBox(None, self.known_nonzero)
            incomingvarboxes.append(newbox)
            memo[self] = newbox
            return newbox
        else:
            return memo[self]

class FrozenPtrVar(AbstractFrozenPtrVar, LLTypeMixin):
    PtrRedBox = PtrRedBox

class FrozenInstanceVar(AbstractFrozenPtrVar, OOTypeMixin):
    PtrRedBox = InstanceRedBox


class FrozenPtrVarWithPartialData(FrozenPtrVar):

    def exactmatch(self, box, outgoingvarboxes, memo):
        if self.fz_partialcontent is None:
            return FrozenPtrVar.exactmatch(self, box, outgoingvarboxes, memo)
        assert isinstance(box, PtrRedBox)
        partialdatamatch = self.fz_partialcontent.match(box,
                                                        memo.partialdatamatch)
        # skip the parent's exactmatch()!
        exact = FrozenVar.exactmatch(self, box, outgoingvarboxes, memo)
        match = exact and partialdatamatch
        if not memo.force_merge and not match:
            # heuristic: if a virtual is neither written to, nor read from
            # it might not be "important enough" to keep it virtual
            from pypy.jit.timeshifter.rcontainer import VirtualContainer
            if isinstance(box.content, VirtualContainer):
                if not box.access_info.read_fields:
                    return match
                raise DontMerge   # XXX recursive data structures?
        return match


class FrozenPtrVirtual(FrozenValue):

    def exactmatch(self, box, outgoingvarboxes, memo):
        assert isinstance(box, PtrRedBox)
        if box.genvar:
            # XXX should we consider self.access_info here too?
            raise DontMerge
        else:
            assert box.content is not None
            match = self.fz_content.exactmatch(box.content, outgoingvarboxes,
                                              memo)
        return match
    
    def unfreeze(self, incomingvarboxes, memo):
        return self.fz_content.unfreeze(incomingvarboxes, memo)


##class FrozenPtrVarWithData(FrozenValue):

##    def exactmatch(self, box, outgoingvarboxes, memo):
##        memo = memo.boxes
##        if self not in memo:
##            memo[self] = box
##            outgoingvarboxes.append(box)
##            return True
##        elif memo[self] is box:
##            return True
##        else:
##            outgoingvarboxes.append(box)
##            return False

PtrRedBox.FrozenPtrVirtual = FrozenPtrVirtual
PtrRedBox.FrozenPtrConst = FrozenPtrConst
PtrRedBox.FrozenPtrVar = FrozenPtrVar
PtrRedBox.FrozenPtrVarWithPartialData = FrozenPtrVarWithPartialData

InstanceRedBox.FrozenPtrVirtual = None
InstanceRedBox.FrozenPtrConst = FrozenInstanceConst
InstanceRedBox.FrozenPtrVar = FrozenInstanceVar
InstanceRedBox.FrozenPtrVarWithPartialData = None
