from pypy.conftest import gettestobjspace
from pypy.objspace.std.test.test_dictmultiobject import FakeSpace, W_DictMultiObject
from pypy.objspace.std.mapdict import *

space = FakeSpace()

class FakeMember(object):
    def __init__(self, name, index=0):
        self.name = name
        self.index = index

class Class(object):
    def __init__(self, hasdict=True):
        self.hasdict = True
        if hasdict:
            self.terminator = DictTerminator(self, space)
        else:
            self.terminator = NoDictTerminator(self, space)

    def instantiate(self, sp=None):
        if sp is None:
            sp = space
        result = Object()
        result.user_setup(sp, self)
        return result

class Object(Object):
    class typedef:
        hasdict = False

def test_plain_attribute():
    aa = PlainAttribute(("b", DICT), PlainAttribute(("a", DICT), Terminator(None, None)))
    obj = Object()
    obj.map, obj.storage = aa, [10, 20]
    assert obj.getdictvalue(space, "a") == 10
    assert obj.getdictvalue(space, "b") == 20
    assert obj.getdictvalue(space, "c") is None

    obj = Object()
    obj.map, obj.storage = aa, [30, 40]
    obj.setdictvalue(space, "a", 50)
    assert obj.storage == [50, 40]
    assert obj.getdictvalue(space, "a") == 50
    obj.setdictvalue(space, "b", 60)
    assert obj.storage == [50, 60]
    assert obj.getdictvalue(space, "b") == 60

    assert aa.length() == 2

    assert aa.get_terminator() is aa.back.back

def test_search():
    aa = PlainAttribute(("b", DICT), PlainAttribute(("a", DICT), Terminator(None, None)))
    assert aa.search(DICT) is aa
    assert aa.search(SLOTS_STARTING_FROM) is None
    assert aa.search(SPECIAL) is None
    bb = PlainAttribute(("C", SPECIAL), PlainAttribute(("A", SLOTS_STARTING_FROM), aa))
    assert bb.search(DICT) is aa
    assert bb.search(SLOTS_STARTING_FROM) is bb.back
    assert bb.search(SPECIAL) is bb

def test_add_attribute():
    cls = Class()
    obj = cls.instantiate()
    obj.setdictvalue(space, "a", 10)
    assert obj.storage == [10]
    assert obj.getdictvalue(space, "a") == 10
    assert obj.getdictvalue(space, "b") is None
    assert obj.getdictvalue(space, "c") is None
    obj.setdictvalue(space, "a", 20)
    assert obj.getdictvalue(space, "a") == 20
    assert obj.getdictvalue(space, "b") is None
    assert obj.getdictvalue(space, "c") is None

    obj.setdictvalue(space, "b", 30)
    assert obj.storage == [20, 30]
    assert obj.getdictvalue(space, "a") == 20
    assert obj.getdictvalue(space, "b") == 30
    assert obj.getdictvalue(space, "c") is None
    obj.setdictvalue(space, "b", 40)
    assert obj.getdictvalue(space, "a") == 20
    assert obj.getdictvalue(space, "b") == 40
    assert obj.getdictvalue(space, "c") is None

    obj2 = cls.instantiate()
    obj2.setdictvalue(space, "a", 50)
    obj2.setdictvalue(space, "b", 60)
    assert obj2.getdictvalue(space, "a") == 50
    assert obj2.getdictvalue(space, "b") == 60
    assert obj2.map is obj.map

def test_delete():
    for i, dattr in enumerate(["a", "b", "c"]):
        c = Class()
        obj = c.instantiate()
        obj.setdictvalue(space, "a", 50)
        obj.setdictvalue(space, "b", 60)
        obj.setdictvalue(space, "c", 70)
        assert obj.storage == [50, 60, 70]
        res = obj.deldictvalue(space, dattr)
        assert res
        s = [50, 60, 70]
        del s[i]
        assert obj.storage == s

    obj = c.instantiate()
    obj.setdictvalue(space, "a", 50)
    obj.setdictvalue(space, "b", 60)
    obj.setdictvalue(space, "c", 70)
    assert not obj.deldictvalue(space, "d")


def test_class():
    c = Class()
    obj = c.instantiate()
    assert obj.getclass(space) is c
    obj.setdictvalue(space, "a", 50)
    assert obj.getclass(space) is c
    obj.setdictvalue(space, "b", 60)
    assert obj.getclass(space) is c
    obj.setdictvalue(space, "c", 70)
    assert obj.getclass(space) is c

    c2 = Class()
    obj.setclass(space, c2)
    assert obj.getclass(space) is c2
    assert obj.storage == [50, 60, 70]

def test_special():
    from pypy.module._weakref.interp__weakref import WeakrefLifeline
    lifeline1 = WeakrefLifeline(space)
    lifeline2 = WeakrefLifeline(space)
    c = Class()
    obj = c.instantiate()
    assert obj.getweakref() is None
    obj.setdictvalue(space, "a", 50)
    obj.setdictvalue(space, "b", 60)
    obj.setdictvalue(space, "c", 70)
    obj.setweakref(space, lifeline1)
    assert obj.getdictvalue(space, "a") == 50
    assert obj.getdictvalue(space, "b") == 60
    assert obj.getdictvalue(space, "c") == 70
    assert obj.storage == [50, 60, 70, lifeline1]
    assert obj.getweakref() is lifeline1

    obj2 = c.instantiate()
    obj2.setdictvalue(space, "a", 150)
    obj2.setdictvalue(space, "b", 160)
    obj2.setdictvalue(space, "c", 170)
    obj2.setweakref(space, lifeline2)
    assert obj2.storage == [150, 160, 170, lifeline2]
    assert obj2.getweakref() is lifeline2

    assert obj2.map is obj.map

    assert obj.getdictvalue(space, "weakref") is None
    obj.setdictvalue(space, "weakref", 41)
    assert obj.getweakref() is lifeline1
    assert obj.getdictvalue(space, "weakref") == 41


def test_slots():
    cls = Class()
    obj = cls.instantiate()
    a =  FakeMember("a")
    b =  FakeMember("b")
    c =  FakeMember("c")
    obj.setslotvalue(a, 50)
    obj.setslotvalue(b, 60)
    obj.setslotvalue(c, 70)
    assert obj.getslotvalue(a) == 50
    assert obj.getslotvalue(b) == 60
    assert obj.getslotvalue(c) == 70
    assert obj.storage == [50, 60, 70]

    obj.setdictvalue(space, "a", 5)
    obj.setdictvalue(space, "b", 6)
    obj.setdictvalue(space, "c", 7)
    assert obj.getdictvalue(space, "a") == 5
    assert obj.getdictvalue(space, "b") == 6
    assert obj.getdictvalue(space, "c") == 7
    assert obj.getslotvalue(a) == 50
    assert obj.getslotvalue(b) == 60
    assert obj.getslotvalue(c) == 70
    assert obj.storage == [50, 60, 70, 5, 6, 7]

    obj2 = cls.instantiate()
    obj2.setslotvalue(a, 501)
    obj2.setslotvalue(b, 601)
    obj2.setslotvalue(c, 701)
    obj2.setdictvalue(space, "a", 51)
    obj2.setdictvalue(space, "b", 61)
    obj2.setdictvalue(space, "c", 71)
    assert obj2.storage == [501, 601, 701, 51, 61, 71]
    assert obj.map is obj2.map

def test_slots_same_name():
    cls = Class()
    obj = cls.instantiate()
    a =  FakeMember("a")
    b =  FakeMember("a", 1)
    c =  FakeMember("a", 2)
    obj.setslotvalue(a, 50)
    obj.setslotvalue(b, 60)
    obj.setslotvalue(c, 70)
    assert obj.getslotvalue(a) == 50
    assert obj.getslotvalue(b) == 60
    assert obj.getslotvalue(c) == 70
    assert obj.storage == [50, 60, 70]


def test_slots_no_dict():
    cls = Class(hasdict=False)
    obj = cls.instantiate()
    a =  FakeMember("a")
    b =  FakeMember("b")
    c =  FakeMember("c")
    obj.setslotvalue(a, 50)
    obj.setslotvalue(b, 60)
    assert obj.getslotvalue(a) == 50
    assert obj.getslotvalue(b) == 60
    assert obj.storage == [50, 60]
    assert not obj.setdictvalue(space, "a", 70)

def test_getdict():
    cls = Class()
    obj = cls.instantiate()
    obj.setdictvalue(space, "a", 51)
    obj.setdictvalue(space, "b", 61)
    obj.setdictvalue(space, "c", 71)
    assert obj.getdict() is obj.getdict()
    assert obj.getdict().length() == 3


def test_materialize_r_dict():
    cls = Class()
    obj = cls.instantiate()
    a =  FakeMember("a")
    b =  FakeMember("b")
    c =  FakeMember("c")
    obj.setslotvalue(a, 50)
    obj.setslotvalue(b, 60)
    obj.setslotvalue(c, 70)
    obj.setdictvalue(space, "a", 5)
    obj.setdictvalue(space, "b", 6)
    obj.setdictvalue(space, "c", 7)
    assert obj.storage == [50, 60, 70, 5, 6, 7]

    class FakeDict(W_DictMultiObject):
        def __init__(self, d):
            self.r_dict_content = d

    d = {}
    w_d = FakeDict(d)
    flag = obj.map.write(obj, ("dict", SPECIAL), w_d)
    assert flag
    materialize_r_dict(space, obj, w_d)
    assert d == {"a": 5, "b": 6, "c": 7}
    assert obj.storage == [50, 60, 70, w_d]


def test_size_prediction():
    for i in range(10):
        c = Class()
        assert c.terminator.size_estimate() == 0
        for j in range(1000):
            obj = c.instantiate()
            for a in "abcdefghij"[:i]:
                obj.setdictvalue(space, a, 50)
        assert c.terminator.size_estimate() == i
    for i in range(1, 10):
        c = Class()
        assert c.terminator.size_estimate() == 0
        for j in range(1000):
            obj = c.instantiate()
            for a in "abcdefghij"[:i]:
                obj.setdictvalue(space, a, 50)
            obj = c.instantiate()
            for a in "klmnopqars":
                obj.setdictvalue(space, a, 50)
        assert c.terminator.size_estimate() in [(i + 10) // 2, (i + 11) // 2]

# ___________________________________________________________
# dict tests

from pypy.objspace.std.test.test_dictmultiobject import BaseTestRDictImplementation, BaseTestDevolvedDictImplementation
def get_impl(self):
    cls = Class()
    w_obj = cls.instantiate(self.fakespace)
    return w_obj.getdict()
class TestMapDictImplementation(BaseTestRDictImplementation):
    ImplementionClass = MapDictImplementation
    get_impl = get_impl
class TestDevolvedMapDictImplementation(BaseTestDevolvedDictImplementation):
    get_impl = get_impl
    ImplementionClass = MapDictImplementation

# ___________________________________________________________
# tests that check the obj interface after the dict has devolved

def devolve_dict(obj):
    w_d = obj.getdict()
    w_d._as_rdict()

def test_get_setdictvalue_after_devolve():
    cls = Class()
    obj = cls.instantiate()
    a =  FakeMember("a")
    b =  FakeMember("b")
    c =  FakeMember("c")
    obj.setslotvalue(a, 50)
    obj.setslotvalue(b, 60)
    obj.setslotvalue(c, 70)
    obj.setdictvalue(space, "a", 5)
    obj.setdictvalue(space, "b", 6)
    obj.setdictvalue(space, "c", 7)
    obj.setdictvalue(space, "weakref", 42)
    devolve_dict(obj)
    assert obj.getdictvalue(space, "a") == 5
    assert obj.getdictvalue(space, "b") == 6
    assert obj.getdictvalue(space, "c") == 7
    assert obj.getslotvalue(a) == 50
    assert obj.getslotvalue(b) == 60
    assert obj.getslotvalue(c) == 70
    assert obj.getdictvalue(space, "weakref") == 42
    assert obj.getweakref() is None

    obj.setslotvalue(a, 501)
    obj.setslotvalue(b, 601)
    obj.setslotvalue(c, 701)
    res = obj.setdictvalue(space, "a", 51)
    assert res
    obj.setdictvalue(space, "b", 61)
    obj.setdictvalue(space, "c", 71)
    assert obj.getdictvalue(space, "a") == 51
    assert obj.getdictvalue(space, "b") == 61
    assert obj.getdictvalue(space, "c") == 71
    assert obj.getslotvalue(a) == 501
    assert obj.getslotvalue(b) == 601
    assert obj.getslotvalue(c) == 701
    res = obj.deldictvalue(space, "a")
    assert res
    assert obj.getdictvalue(space, "a") is None
    assert obj.getdictvalue(space, "b") == 61
    assert obj.getdictvalue(space, "c") == 71
    assert obj.getslotvalue(a) == 501
    assert obj.getslotvalue(b) == 601
    assert obj.getslotvalue(c) == 701

def test_setdict():
    cls = Class()
    obj = cls.instantiate()
    obj.setdictvalue(space, "a", 5)
    obj.setdictvalue(space, "b", 6)
    obj.setdictvalue(space, "c", 7)
    w_d = obj.getdict()
    obj2 = cls.instantiate()
    obj2.setdictvalue(space, "d", 8)
    obj.setdict(space, obj2.getdict())
    assert obj.getdictvalue(space, "a") is None
    assert obj.getdictvalue(space, "b") is None
    assert obj.getdictvalue(space, "c") is None
    assert obj.getdictvalue(space, "d") == 8
    assert w_d.getitem_str("a") == 5
    assert w_d.getitem_str("b") == 6
    assert w_d.getitem_str("c") == 7

# ___________________________________________________________
# integration tests

# XXX write more

class AppTestWithMapDict(object):
    def setup_class(cls):
        cls.space = gettestobjspace(**{"objspace.std.withmapdict": True})

    def test_simple(self):
        class A(object):
            pass
        a = A()
        a.x = 5
        a.y = 6
        a.zz = 7
        assert a.x == 5
        assert a.y == 6
        assert a.zz == 7

    def test_read_write_dict(self):
        class A(object):
            pass
        a = A()
        a.x = 5
        a.y = 6
        a.zz = 7
        d = a.__dict__
        assert d == {"x": 5, "y": 6, "zz": 7}
        d['dd'] = 41
        assert a.dd == 41
        del a.x
        assert d == {"y": 6, "zz": 7, 'dd': 41}
        d2 = d.copy()
        d2[1] = 2
        a.__dict__ = d2
        assert a.y == 6
        assert a.zz == 7
        assert a.dd == 41
        d['dd'] = 43
        assert a.dd == 41


    def test_slot_name_conflict(self):
        class A(object):
            __slots__ = 'slot1'
        class B(A):
            __slots__ = 'slot1'
        x = B()
        x.slot1 = 'child'             # using B.slot1
        A.slot1.__set__(x, 'parent')  # using A.slot1
        assert x.slot1 == 'child'     # B.slot1 should still have its old value
        assert A.slot1.__get__(x) == 'parent'
