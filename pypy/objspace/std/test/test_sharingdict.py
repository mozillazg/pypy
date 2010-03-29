import py
from pypy.conftest import gettestobjspace
from pypy.objspace.std.sharingdict import SharedStructure, NUM_DIGITS, SharedDictImplementation
from pypy.objspace.std.sharingdict import erase, unerase
from pypy.interpreter import gateway
from pypy.objspace.std.test.test_dictmultiobject import FakeSpace

def instance_with_keys(structure, *keys):
    for key in keys:
        structure = structure.get_next_structure(key)
    return structure

def test_size_estimate():
    empty_structure = SharedStructure(None)
    instances = []
    for i in range(100):
        instances.append(instance_with_keys(empty_structure, "a", "b", "c", "d", "e", "f"))
        instances.append(instance_with_keys(empty_structure, "x", "y"))
    assert empty_structure.size_estimate() == 4
    assert empty_structure.other_structs.get("a").size_estimate() == 6
    assert empty_structure.other_structs.get("x").size_estimate() == 2

def test_size_estimate2():
    empty_structure = SharedStructure(None)
    instances = []
    for i in range(100):
        instances.append(instance_with_keys(empty_structure, "a", "b", "c", "d", "e", "f"))
        instances.append(instance_with_keys(empty_structure, "x", "y"))
        instances.append(instance_with_keys(empty_structure, "x", "y"))
    assert empty_structure.size_estimate() == 3
    assert empty_structure.other_structs.get("a").size_estimate() == 6
    assert empty_structure.other_structs.get("x").size_estimate() == 2

def unerase_entries(space, d):
    return [unerase(space, e) for e in d.entries]
def key_positions(d):
    return dict([(key, attr.index) for key, attr in d.structure.keys.items()])

def test_delete():
    space = FakeSpace()
    d = SharedDictImplementation(space)
    d.setitem_str("a", 1)
    d.setitem_str("b", 2)
    d.setitem_str("c", 3)
    d.delitem("b")
    assert d.r_dict_content is None
    assert unerase_entries(space, d) == [1, 3, None]
    assert key_positions(d) == {"a": 0, "c": 1}
    assert d.getitem("a") == 1
    assert d.getitem("c") == 3
    assert d.getitem("b") is None
    py.test.raises(KeyError, d.delitem, "b")

    d.delitem("c")
    assert unerase_entries(space, d) == [1, None, None]
    assert key_positions(d) == {"a": 0}

    d.delitem("a")
    assert unerase_entries(space, d) == [None, None, None]
    assert key_positions(d) == {}

    d = SharedDictImplementation(space)
    d.setitem_str("a", 1)
    d.setitem_str("b", 2)
    d.setitem_str("c", 3)
    d.setitem_str("d", 4)
    d.setitem_str("e", 5)
    d.setitem_str("f", 6)
    d.setitem_str("g", 7)
    d.setitem_str("h", 8)
    d.setitem_str("i", 9)
    d.delitem("d")
    assert unerase_entries(space, d) == [1, 2, 3, 5, 6, 7, 8, 9, None]
    assert key_positions(d) == {"a": 0, "b": 1, "c": 2, "e": 3, "f": 4, "g": 5, "h": 6, "i": 7}
