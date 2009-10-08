import weakref
from pypy.rpython.lltypesystem import lltype, llmemory, rffi


class GroupType(lltype.ContainerType):
    """A 'group' that stores static structs together in memory.
    The point is that they can be referenced by a GroupMemberOffset
    which only takes 2 bytes (a USHORT), so the total size of a group
    is limited to 18 or 19 bits (= the 16 bits in a USHORT, plus 2 or
    3 bits at the end that are zero and so don't need to be stored).
    """
    _gckind = 'raw'

Group = GroupType()


class group(lltype._container):
    _TYPE = Group

    def __init__(self, name):
        self.name = name
        self.members = []

    def add_member(self, structptr):
        TYPE = lltype.typeOf(structptr)
        assert isinstance(TYPE.TO, lltype.Struct)
        assert TYPE.TO._gckind == 'raw'
        struct = structptr._as_obj()
        assert struct not in _membership,"cannot be a member of several groups"
        assert struct._parentstructure() is None
        index = len(self.members)
        self.members.append(struct)
        _membership[struct] = self
        return GroupMemberOffset(self, index)

def member_of_group(structptr):
    return _membership.get(structptr._as_obj(), None)

_membership = weakref.WeakValueDictionary()


class GroupMemberOffset(llmemory.Symbolic):
    """The offset of a struct inside a group, stored compactly in a USHORT.
    Can only be used by the lloperation 'get_group_member'.
    """
    def annotation(self):
        from pypy.annotation import model
        return model.SomeInteger(knowntype=rffi.r_ushort)

    def lltype(self):
        return rffi.USHORT

    def __init__(self, grp, memberindex):
        assert lltype.typeOf(grp) == Group
        self.grpptr = grp._as_ptr()
        self.index = memberindex
        self.member = grp.members[memberindex]._as_ptr()

    def _get_group_member(self, grpptr):
        assert grpptr == self.grpptr, "get_group_member: wrong group!"
        return self.member

    def _get_next_group_member(self, grpptr, skipoffset):
        # ad-hoc: returns a pointer to the group member that follows this one,
        # given information in 'skipoffset' about how much to skip -- which
        # is the size of the current member.
        assert grpptr == self.grpptr, "get_next_group_member: wrong group!"
        assert isinstance(skipoffset, llmemory.ItemOffset)
        assert skipoffset.TYPE == lltype.typeOf(self.member).TO
        assert skipoffset.repeat == 1
        return self.grpptr._as_obj().members[self.index + 1]._as_ptr()
