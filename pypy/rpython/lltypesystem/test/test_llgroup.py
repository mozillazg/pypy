from pypy.rpython.lltypesystem.llgroup import *
from pypy.rpython.lltypesystem.lloperation import llop
from pypy.rpython.test.test_llinterp import interpret


class TestLLGroup(object):

    def _freeze_(self):
        return True

    def build(self):
        grp = group('testing')
        S1 = lltype.Struct('S1', ('x', lltype.Signed))
        S2 = lltype.Struct('S2', ('y', lltype.Signed), ('z', lltype.Signed))
        p1a = lltype.malloc(S1, immortal=True, zero=True)
        p1b = lltype.malloc(S1, immortal=True, zero=True)
        p2a = lltype.malloc(S2, immortal=True, zero=True)
        p2b = lltype.malloc(S2, immortal=True, zero=True)
        p1a.x = 123
        p1b.x = 456
        p2a.y = 789
        p2b.z = -12
        grp.add_member(p1a)
        grp.add_member(p2a)
        grp.add_member(p2b)
        grp.add_member(p1b)
        self.g1a = GroupMemberOffset(grp, p1a)
        self.g1b = GroupMemberOffset(grp, p1b)
        self.g2a = GroupMemberOffset(grp, p2a)
        self.g2b = GroupMemberOffset(grp, p2b)
        self.p1a = p1a
        self.p1b = p1b
        self.p2a = p2a
        self.p2b = p2b
        self.S1 = S1
        self.S2 = S2
        self.grp = grp
        self.grpptr = grp._as_ptr()

    def test_simple(self):
        self.build()
        grpptr = self.grpptr
        S1 = self.S1
        S2 = self.S2
        Ptr = lltype.Ptr
        assert llop.get_group_member(Ptr(S1), grpptr, self.g1a) == self.p1a
        assert llop.get_group_member(Ptr(S1), grpptr, self.g1b) == self.p1b
        assert llop.get_group_member(Ptr(S2), grpptr, self.g2a) == self.p2a
        assert llop.get_group_member(Ptr(S2), grpptr, self.g2b) == self.p2b

    def test_member_of_group(self):
        self.build()
        assert member_of_group(self.p1a) == self.grp
        assert member_of_group(self.p2b) == self.grp
        pnew = lltype.malloc(self.S2, immortal=True)
        assert member_of_group(pnew) is None

    def test_rpython(self):
        self.build()
        grpptr = self.grpptr
        def f():
            p = llop.get_group_member(lltype.Ptr(self.S1), grpptr, self.g1a)
            assert p == self.p1a
            p = llop.get_group_member(lltype.Ptr(self.S1), grpptr, self.g1b)
            assert p == self.p1b
            p = llop.get_group_member(lltype.Ptr(self.S2), grpptr, self.g2a)
            assert p == self.p2a
            p = llop.get_group_member(lltype.Ptr(self.S2), grpptr, self.g2b)
            assert p == self.p2b
            return 3
        assert interpret(f, []) == 3
