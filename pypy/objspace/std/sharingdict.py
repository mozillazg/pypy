from pypy.objspace.std.dictmultiobject import IteratorImplementation
from pypy.objspace.std.dictmultiobject import W_DictMultiObject, _is_sane_hash
from pypy.rlib.jit import purefunction_promote, we_are_jitted, unroll_safe
from pypy.rlib.jit import purefunction
from pypy.rlib.rweakref import RWeakValueDictionary

NUM_DIGITS = 4

class SharedStructure(object):
    _immutable_fields_ = ["keys", "length", "back_struct", "other_structs",
                          "last_key"]

    def __init__(self, space, keys=None, length=0,
                 last_key=None,
                 back_struct=None):
        self.space = space
        if keys is None:
            keys = {}
        self.keys = keys
        self.length = length
        self.back_struct = back_struct
        other_structs = RWeakValueDictionary(SharedStructure)
        self.other_structs = other_structs
        self.last_key = last_key
        self._size_estimate = length << NUM_DIGITS
        if last_key is not None:
            assert back_struct is not None

    def new_structure(self, added_key):
        keys = self.keys.copy()
        keys[added_key] = AttributeShape(self.space, len(self.keys))
        new_structure = SharedStructure(self.space, keys, self.length + 1,
                                        added_key, self)
        self.other_structs.set(added_key, new_structure)
        return new_structure

    @purefunction_promote('0')
    def lookup_attribute(self, key):
        return self.keys.get(key, None)

    @purefunction_promote('0')
    def get_next_structure(self, key):
        new_structure = self.other_structs.get(key)
        if new_structure is None:
            new_structure = self.new_structure(key)
        self._size_estimate -= self.size_estimate()
        self._size_estimate += new_structure.size_estimate()
        return new_structure

    @purefunction_promote()
    def size_estimate(self):
        return self._size_estimate >> NUM_DIGITS

    def convert_to(self, new_structure, entries):
        if new_structure.length > len(entries):
            new_entries = [erase(self.space, None)] * new_structure.size_estimate()
            for i in range(len(entries)):
                new_entries[i] = entries[i]
            entries = new_entries
        assert self.length + 1 == new_structure.length
        return entries

    @purefunction_promote('0')
    def find_structure_del_key(self, num_back):
        keys = [None] * num_back
        for i in range(num_back):
            keys[i] = self.last_key
            self = self.back_struct
        # go back the structure that contains the deleted key
        self = self.back_struct
        for i in range(num_back - 1, -1, -1):
            self = self.get_next_structure(keys[i])
        return self


class AttributeShape(object):
    _immutable_ = True
    def __init__(self, space, index):
        self.space = space
        self.index = index

    def getfield(self, fields):
        return unerase(self.space, fields[self.index])
    def setfield(self, fields, val):
        fields[self.index] = erase(self.space, val)
    def delfield(self, fields, structure):
        struct_len = structure.length
        num_back = struct_len - self.index - 1
        if num_back > 0:
            for i in range(self.index, struct_len - 1):
                fields[i] = fields[i + 1]
        # don't make the entries list shorter, new keys might be added soon
        fields[struct_len - 1] = erase(self.space, None)
        return structure.find_structure_del_key(num_back)


        

def erase(space, w_value):
    if not space.config.objspace.std.withsharingtaggingdict:
        return w_value
    from pypy.rlib.rerased import erase
    if w_value is None:
        return erase(w_value)
    if space.is_true(space.isinstance(w_value, space.w_int)):
        try:
            return erase(space.int_w(w_value))
        except OverflowError:
            pass
    return erase(w_value)

def unerase(space, erased):
    if not space.config.objspace.std.withsharingtaggingdict:
        return erased
    from pypy.rlib.rerased import unerase, is_integer
    if is_integer(erased):
        return space.wrap(unerase(erased, int))
    return unerase(erased, space.roottype)


class State(object):
    def __init__(self, space):
        self.empty_structure = SharedStructure(space)
        self.emptylist = []


class SharedDictImplementation(W_DictMultiObject):

    def __init__(self, space):
        self.space = space
        self.structure = space.fromcache(State).empty_structure
        self.entries = space.fromcache(State).emptylist

    def impl_getitem(self, w_lookup):
        space = self.space
        w_lookup_type = space.type(w_lookup)
        if space.is_w(w_lookup_type, space.w_str):
            return self.impl_getitem_str(space.str_w(w_lookup))
        elif _is_sane_hash(space, w_lookup_type):
            return None
        else:
            return self._as_rdict().getitem(w_lookup)

    def impl_getitem_str(self, lookup):
        attr = self.structure.lookup_attribute(lookup)
        if attr is None:
            return None
        return attr.getfield(self.entries)

    def impl_setitem(self, w_key, w_value):
        space = self.space
        if space.is_w(space.type(w_key), space.w_str):
            self.impl_setitem_str(self.space.str_w(w_key), w_value)
        else:
            self._as_rdict().setitem(w_key, w_value)

    @unroll_safe
    def impl_setitem_str(self, key, w_value, shadows_type=True):
        attr = self.structure.lookup_attribute(key)
        if attr is not None:
            attr.setfield(self.space, w_value)
            return
        new_structure = self.structure.get_next_structure(key)
        self.entries = self.structure.convert_to(new_structure, self.entries)
        attr = new_structure.lookup_attribute(key)
        attr.setfield(self.entries, w_value)
        self.structure = new_structure
            
    def impl_delitem(self, w_key):
        space = self.space
        w_key_type = space.type(w_key)
        if space.is_w(w_key_type, space.w_str):
            key = space.str_w(w_key)
            attr = self.structure.lookup_attribute(key)
            if attr is None:
                raise KeyError
            self.structure = attr.delfield(self.entries, self.structure)
        elif _is_sane_hash(space, w_key_type):
            raise KeyError
        else:
            self._as_rdict().delitem(w_key)
        
    def impl_length(self):
        return self.structure.length

    def impl_iter(self):
        return SharedIteratorImplementation(self.space, self)

    def impl_keys(self):
        space = self.space
        return [space.wrap(key)
                    for (key, _) in self.structure.keys.iteritems()]

    def impl_values(self):
        return [unerase(self.space, self.entries[i])
                    for i in range(self.structure.length)]

    def impl_items(self):
        space = self.space
        return [space.newtuple([
                        space.wrap(key),
                        attr.getfield(self.entries)])
                    for (key, attr) in self.structure.keys.iteritems()]
    def impl_clear(self):
        space = self.space
        self.structure = space.fromcache(State).empty_structure
        self.entries = space.fromcache(State).emptylist
    def _as_rdict(self):
        r_dict_content = self.initialize_as_rdict()
        for k, attr in self.structure.keys.items():
            r_dict_content[self.space.wrap(k)] = attr.getfield(
                self.entries)
        self._clear_fields()
        return self

    def _clear_fields(self):
        self.structure = None
        self.entries = None

class SharedIteratorImplementation(IteratorImplementation):
    def __init__(self, space, dictimplementation):
        IteratorImplementation.__init__(self, space, dictimplementation)
        self.iterator = dictimplementation.structure.keys.iteritems()

    def next_entry(self):
        implementation = self.dictimplementation
        assert isinstance(implementation, SharedDictImplementation)
        for key, attr in self.iterator:
            w_value = attr.getfield(implementation.entries)
            return self.space.wrap(key), w_value
        else:
            return None, None
