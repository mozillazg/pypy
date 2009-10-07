import weakref
from pypy.rpython.lltypesystem import lltype, llmemory, rffi


class GroupType(lltype.ContainerType):
    """A 'group' that stores static structs together in memory.
    The point is that they can be referenced by a GroupMemberOffset
    which only takes 2 bytes (a USHORT), so the total size of a group
    is limited to 18 or 19 bits (= the 16 bits in a USHORT, plus 2 or
    3 bits at the end that are zero and so don't need to be stored).
    """

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
        self.members.append(struct)
        _membership[struct] = self

def member_of_group(structptr):
    return _membership.get(structptr._as_obj(), None)

_membership = weakref.WeakKeyDictionary()


class GroupMemberOffset(llmemory.Symbolic):
    """The offset of a struct inside a group, stored compactly in a USHORT.
    Can only be used by the lloperation 'get_group_member'.
    """
    def annotation(self):
        from pypy.annotation import model
        return model.SomeInteger(knowntype=rffi.r_ushort)

    def lltype(self):
        return rffi.USHORT

    def __init__(self, grp, member):
        assert lltype.typeOf(grp) == Group
        assert member._as_obj() in grp.members
        self.grpptr = grp._as_ptr()
        self.member = member._as_ptr()

    def _get_group_member(self, grpptr):
        assert grpptr == self.grpptr, "get_group_member: wrong group!"
        return self.member
