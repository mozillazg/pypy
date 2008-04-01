import py

from pypy.rpython.lltypesystem import lltype
from pypy.jit.timeshifter import rvalue, rcontainer
from pypy.jit.timeshifter.test.support import FakeJITState, FakeGenVar
from pypy.jit.timeshifter.test.support import FakeGenConst, FakeRGenOp
from pypy.jit.timeshifter.test.support import signed_kind
from pypy.jit.timeshifter.test.support import vmalloc, makebox
from pypy.jit.timeshifter.test.support import getfielddesc


class TestVirtualStruct:

    def setup_class(cls):
        cls.STRUCT = lltype.GcStruct("dummy", ("foo", lltype.Signed))
        cls.fielddesc = getfielddesc(cls.STRUCT, "foo")
        FORWARD = lltype.GcForwardReference()
        cls.NESTEDSTRUCT = lltype.GcStruct('dummy', ("foo", lltype.Signed),
                                                    ('x', lltype.Ptr(FORWARD)))
        FORWARD.become(cls.NESTEDSTRUCT)

    def test_virtualstruct_get_set_field(self):
        V42 = FakeGenVar(42)
        box = vmalloc(self.STRUCT, makebox(V42))
        assert box.known_nonzero
        jitstate = FakeJITState()
        box2 = box.op_getfield(jitstate, self.fielddesc)
        assert box2.genvar is V42
        assert jitstate.curbuilder.ops == []

    def test_virtualstruct_escape(self):
        V42 = FakeGenVar(42)
        box = vmalloc(self.STRUCT, makebox(V42))
        jitstate = FakeJITState()
        V1 = box.getgenvar(jitstate)     # forcing
        assert jitstate.curbuilder.ops == [
            ('malloc_fixedsize', (('alloc', self.STRUCT),), V1),
            ('setfield', (('field', self.STRUCT, 'foo'), V1, V42), None)]

    def match(self, frozenbox, box, expected_outgoing):
        # In case of exact match, expected_outgoing is the list of subboxes
        # of 'box' that correspond to FrozenVar placeholders in frozenbox.
        # Otherwise, it is the list of subboxes of 'box' that should be
        # generalized to become variables.
        rgenop = FakeRGenOp()
        outgoingvarboxes = []
        res = frozenbox.exactmatch(box, outgoingvarboxes,
                                   rvalue.exactmatch_memo(rgenop))
        assert outgoingvarboxes == expected_outgoing
        return res

    def test_simple_merge(self):
        V42 = FakeGenVar(42)
        oldbox = vmalloc(self.STRUCT, makebox(V42))
        frozenbox = oldbox.freeze(rvalue.freeze_memo())
        # check that frozenbox matches oldbox exactly
        jitstate = FakeJITState()
        fieldbox = oldbox.content.op_getfield(jitstate, self.fielddesc)
        assert self.match(frozenbox, oldbox, [fieldbox])

        constbox23 = makebox(23)
        newbox = vmalloc(self.STRUCT, constbox23)
        # check that frozenbox also matches newbox exactly
        assert self.match(frozenbox, newbox, [constbox23])

    def test_simple_merge_generalize(self):
        S = self.STRUCT
        constbox20 = makebox(20)
        oldbox = vmalloc(S, constbox20)
        frozenbox = oldbox.freeze(rvalue.freeze_memo())
        # check that frozenbox matches oldbox exactly
        assert self.match(frozenbox, oldbox, [])      # there is no FrozenVar

        constbox23 = makebox(23)
        newbox = vmalloc(S, constbox23)
        # non-exact match: a different constant box in the virtual struct field
        assert not self.match(frozenbox, newbox, [constbox23])
        #  constbox23 is what should be generalized with forcevar()
        #  in order to get something that is at least as general as
        #  both oldbox and newbox

        jitstate = FakeJITState()
        replace_memo = rvalue.copy_memo()
        forcedbox = constbox23.forcevar(jitstate, replace_memo, False)
        assert not forcedbox.is_constant()
        assert jitstate.curbuilder.ops == [
            ('same_as', (constbox23.genvar, ), forcedbox.genvar)]
        assert replace_memo.boxes == {constbox23: forcedbox}

        # change constbox to forcedbox inside newbox
        newbox.replace(replace_memo)
        assert (newbox.content.op_getfield(jitstate, self.fielddesc) is
                forcedbox)

        # check that now newbox really generalizes oldbox
        newfrozenbox = newbox.freeze(rvalue.freeze_memo())
        assert self.match(newfrozenbox, oldbox, [constbox20])
        #       ^^^ the FrozenVar() in newfrozenbox corresponds to
        #           constbox20 in oldbox.


    def test_merge_with_ptrvar(self):
        DontMerge = rvalue.DontMerge
        V0 = FakeGenVar()
        ptrbox = rvalue.PtrRedBox(V0)
        jitstate = FakeJITState()
        S = self.STRUCT
        constbox20 = makebox(20)
        oldbox = vmalloc(S, constbox20)

        # do a getfield to prevent a merge
        box2 = oldbox.op_getfield(jitstate, self.fielddesc)
        assert box2 is constbox20
        assert oldbox.access_info.read_fields == 1
        frozenbox = oldbox.freeze(rvalue.freeze_memo())
        # check that ptrbox does not match the frozen virtual struct ever
        py.test.raises(DontMerge, self.match, frozenbox, ptrbox, [ptrbox])

        # try it the other way round
        frozenptrbox = ptrbox.freeze(rvalue.freeze_memo())
        py.test.raises(DontMerge, self.match, frozenptrbox, oldbox, [oldbox])

    def test_merge_with_ptrvar_virtual_never_read(self):
        DontMerge = rvalue.DontMerge
        V0 = FakeGenVar()
        ptrbox = rvalue.PtrRedBox(V0)
        jitstate = FakeJITState()
        S = self.STRUCT
        constbox20 = makebox(20)
        oldbox = vmalloc(S, constbox20)

        frozenptrbox = ptrbox.freeze(rvalue.freeze_memo())
        assert self.match(frozenptrbox, oldbox, [oldbox])

        # try it the other way round
        # XXX what should happen here?
        #frozenbox = oldbox.freeze(rvalue.freeze_memo())
        #self.match(frozenbox, ptrbox, [ptrbox])

    def test_nested_structure_no_vars(self):
        NESTED = self.NESTEDSTRUCT
        constbox30 = makebox(30)
        constbox20 = makebox(20)
        oldbox = vmalloc(NESTED, constbox20, vmalloc(NESTED, constbox30))

        jitstate = FakeJITState()
        frozenbox = oldbox.freeze(rvalue.freeze_memo())
        # check that frozenbox matches oldbox exactly
        assert self.match(frozenbox, oldbox, [])     # there is no FrozenVar


    def test_nested_structures_variables(self):
        NESTED = self.NESTEDSTRUCT
        varbox42 = makebox(FakeGenVar(42))
        constbox20 = makebox(20)
        oldbox = vmalloc(NESTED, constbox20, vmalloc(NESTED, varbox42))
        jitstate = FakeJITState()
        frozenbox = oldbox.freeze(rvalue.freeze_memo())
        # check that frozenbox matches oldbox exactly
        assert self.match(frozenbox, oldbox, [varbox42])

        constbox30 = makebox(30)
        newbox = vmalloc(NESTED, constbox20, vmalloc(NESTED, constbox30))
        # check that frozenbox also matches newbox exactly
        assert self.match(frozenbox, newbox, [constbox30])
