"""
<cfbolz> so, we have a frozen _variable_ s
<cfbolz> and do promote(s.x)
<cfbolz> and try to merge it with a virtual s
<arigato> it looks a bit strange but I suppose that 's.x' should also create {'x': FutureUsage()} in the FutureUsage() of s
<cfbolz> yes, I fear so
<arigato> so, we get a virtual s to merge...
"""

import py
from pypy.rpython.lltypesystem import lltype
from pypy.jit.timeshifter import rvalue, rcontainer, rtimeshift
from pypy.jit.timeshifter.test.support import FakeJITState, FakeGenVar
from pypy.jit.timeshifter.test.support import FakeGenConst, FakeRGenOp
from pypy.jit.timeshifter.test.support import signed_kind
from pypy.jit.timeshifter.test.support import vmalloc, makebox
from pypy.jit.timeshifter.test.support import getfielddesc


class TestMerging:

    def setup_class(cls):
        cls.STRUCT = lltype.GcStruct("S", ("x", lltype.Signed),
                                     hints={'immutable': True})
        cls.fielddesc = getfielddesc(cls.STRUCT, "x")
        FORWARD = lltype.GcForwardReference()
        cls.NESTEDSTRUCT = lltype.GcStruct('dummy', ("foo", lltype.Signed),
                                                    ('next', lltype.Ptr(FORWARD)))
        FORWARD.become(cls.NESTEDSTRUCT)

    def test_promote_const(self):
        """We have a frozen constant 42 which gets a (no-op) promotion after
        it is frozen.  Then it should fail to merge with a live constant 43.
        """
        gc = FakeGenConst(42)
        box = rvalue.IntRedBox(gc)
        frozen = box.freeze(rvalue.freeze_memo())
        assert box.most_recent_frozen is not None    # attached by freeze()
        box.see_promote()

        memo = rvalue.exactmatch_memo()
        gv = FakeGenVar()
        newbox = rvalue.IntRedBox(gv)
        assert not frozen.exactmatch(newbox, [], memo)

        memo = rvalue.exactmatch_memo()
        gc2 = FakeGenConst(43)
        newbox = rvalue.IntRedBox(gc2)
        py.test.raises(rvalue.DontMerge, frozen.exactmatch, newbox, [], memo)

        memo = rvalue.exactmatch_memo()
        gc3 = FakeGenConst(42)
        newbox = rvalue.IntRedBox(gc3)
        assert frozen.exactmatch(newbox, [], memo)

    def test_promote_var(self):
        """We have a frozen variable which gets promoted after
        it is frozen.  Then it should fail to merge with any live constant.
        """
        gv = FakeGenVar()
        box = rvalue.IntRedBox(gv)
        frozen = box.freeze(rvalue.freeze_memo())
        assert box.most_recent_frozen is not None    # attached by freeze()
        box.see_promote()

        memo = rvalue.exactmatch_memo()
        gv2 = FakeGenVar()
        newbox = rvalue.IntRedBox(gv2)
        assert frozen.exactmatch(newbox, [], memo)

        memo = rvalue.exactmatch_memo()
        gc = FakeGenConst(43)
        newbox = rvalue.IntRedBox(gc)
        py.test.raises(rvalue.DontMerge, frozen.exactmatch, newbox, [], memo)

    def test_promotebefore_freeze_const(self):
        """In the merging logic, frozen boxes ignore promotions that
        occurred before the freezing.
        """
        gc = FakeGenConst(42)
        box = rvalue.IntRedBox(gc)
        box.freeze(rvalue.freeze_memo())
        assert box.most_recent_frozen is not None    # attached by freeze()
        box.see_promote()

        frozen = box.freeze(rvalue.freeze_memo())

        memo = rvalue.exactmatch_memo()
        gv = FakeGenVar()
        newbox = rvalue.IntRedBox(gv)
        assert not frozen.exactmatch(newbox, [], memo)

        memo = rvalue.exactmatch_memo()
        gc2 = FakeGenConst(43)
        newbox = rvalue.IntRedBox(gc2)
        assert not frozen.exactmatch(newbox, [], memo)

    def test_promote_field_of_constant_immutable(self):
        """We freeze s then promote s.x.  This should prevent a merge where
        there is an incoming live s2 for which we already know the value of
        s2.x, and for which the merge would loose that information.
        """
        prebuilt_s = lltype.malloc(self.STRUCT)
        prebuilt_s.x = 42

        gc = FakeGenConst(prebuilt_s)
        box = rvalue.PtrRedBox(gc)
        frozen = box.freeze(rvalue.freeze_memo())
        assert box.most_recent_frozen is not None # attached by freeze

        jitstate = FakeJITState()

        x_box = rtimeshift.gengetfield(jitstate, False, self.fielddesc, box)
        assert x_box.genvar.revealconst(lltype.Signed) == 42
        assert x_box.future_usage is not None   # attached by gengetfield()
        x_box.see_promote()

        memo = rvalue.exactmatch_memo()
        assert frozen.exactmatch(box, [], memo)

        prebuilt_s2 = lltype.malloc(self.STRUCT)
        prebuilt_s2.x = 42
        box2 = rvalue.PtrRedBox(FakeGenConst(prebuilt_s2))
        memo = rvalue.exactmatch_memo()
        assert not frozen.exactmatch(box2, [], memo)
        # ^^^no DontMerge because box2.x is equal, so we don't loose its value

        prebuilt_s3 = lltype.malloc(self.STRUCT)
        prebuilt_s3.x = 43
        box3 = rvalue.PtrRedBox(FakeGenConst(prebuilt_s3))
        memo = rvalue.exactmatch_memo()
        py.test.raises(rvalue.DontMerge, frozen.exactmatch, box3, [], memo)
