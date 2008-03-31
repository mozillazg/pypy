"""<arigato> [merge point including x]
<arigato> promote(x)
<cfbolz> then the frozen x has a futureusage
<arigato> yes
<cfbolz> isn't this example too easy?
<cfbolz> I mean, in which case would we want to prevent a merge?
<arigato> it's a start
<arigato> no, it shows the essential bit
<arigato> if x was initially a constant(5), then we don't want to merge with any other value
<arigato> if x was initially a variable, then we don't want to merge with any constant at all
"""

import py
from pypy.rpython.lltypesystem import lltype
from pypy.jit.timeshifter import rvalue, rcontainer
from pypy.jit.timeshifter.test.support import FakeJITState, FakeGenVar
from pypy.jit.timeshifter.test.support import FakeGenConst
from pypy.jit.timeshifter.test.support import signed_kind
from pypy.jit.timeshifter.test.support import vmalloc, makebox
from pypy.jit.timeshifter.test.support import getfielddesc


class TestMerging:

    def setup_class(cls):
        cls.STRUCT = lltype.GcStruct("S", ("x", lltype.Signed))
        cls.fielddesc = getfielddesc(cls.STRUCT, "x")
        FORWARD = lltype.GcForwardReference()
        cls.NESTEDSTRUCT = lltype.GcStruct('dummy', ("foo", lltype.Signed),
                                                    ('next', lltype.Ptr(FORWARD)))
        FORWARD.become(cls.NESTEDSTRUCT)

    def test_promote_const(self):
        gc = FakeGenConst(42)
        box = rvalue.IntRedBox(gc)
        frozen = box.freeze(rvalue.freeze_memo())
        frozen_timestamp = 0
        assert box.future_usage is not None    # attached by freeze()
        box.future_usage.see_promote(timestamp=1)

        memo = rvalue.exactmatch_memo(frozen_timestamp=frozen_timestamp)
        gv = FakeGenVar()
        newbox = rvalue.IntRedBox(gv)
        assert not frozen.exactmatch(newbox, [], memo)

        memo = rvalue.exactmatch_memo(frozen_timestamp=frozen_timestamp)
        gc2 = FakeGenConst(43)
        newbox = rvalue.IntRedBox(gc2)
        py.test.raises(rvalue.DontMerge, frozen.exactmatch, newbox, [], memo)

    def test_promote_var(self):
        gv = FakeGenVar()
        box = rvalue.IntRedBox(gv)
        frozen = box.freeze(rvalue.freeze_memo())
        frozen_timestamp = 0
        assert box.future_usage is not None    # attached by freeze()
        box.future_usage.see_promote(timestamp=1)

        memo = rvalue.exactmatch_memo(frozen_timestamp=frozen_timestamp)
        gv2 = FakeGenVar()
        newbox = rvalue.IntRedBox(gv2)
        assert frozen.exactmatch(newbox, [], memo)

        memo = rvalue.exactmatch_memo(frozen_timestamp=frozen_timestamp)
        gc = FakeGenConst(43)
        newbox = rvalue.IntRedBox(gc)
        py.test.raises(rvalue.DontMerge, frozen.exactmatch, newbox, [], memo)

    def test_promotebefore_freeze_const(self):
        gc = FakeGenConst(42)
        box = rvalue.IntRedBox(gc)
        box.freeze(rvalue.freeze_memo())
        assert box.future_usage is not None    # attached by freeze()
        box.future_usage.see_promote(timestamp=1)

        frozen_timestamp = 2
        frozen = box.freeze(rvalue.freeze_memo())

        memo = rvalue.exactmatch_memo(frozen_timestamp=frozen_timestamp)
        gv = FakeGenVar()
        newbox = rvalue.IntRedBox(gv)
        assert not frozen.exactmatch(newbox, [], memo)

        memo = rvalue.exactmatch_memo(frozen_timestamp=frozen_timestamp)
        gc2 = FakeGenConst(43)
        newbox = rvalue.IntRedBox(gc2)
        assert not frozen.exactmatch(newbox, [], memo)
