from pypy.rlib import jit
# ____________________________________________________________
# attribute shapes

NUM_DIGITS = 4

class AbstractAttribute(object):
    cache_attrs = None
    _size_estimate = 0

    def read(self, obj, selector):
        raise NotImplementedError("abstract base class")

    def write(self, obj, selector, w_value):
        raise NotImplementedError("abstract base class")

    def delete(self, obj, selector):
        return None

    def copy(self, obj):
        raise NotImplementedError("abstract base class")

    def length(self):
        raise NotImplementedError("abstract base class")

    def get_terminator(self):
        raise NotImplementedError("abstract base class")

    def set_terminator(self, obj, terminator):
        raise NotImplementedError("abstract base class")

    @jit.purefunction
    def size_estimate(self):
        return self._size_estimate >> NUM_DIGITS

    def search(self, attrtype):
        return None

    @jit.purefunction
    def _get_new_attr(self, name, index):
        selector = name, index
        cache = self.cache_attrs
        if cache is None:
            cache = self.cache_attrs = {}
        attr = cache.get(selector, None)
        if attr is None:
            attr = PlainAttribute(selector, self)
            cache[selector] = attr
        return attr

    @jit.unroll_safe
    def add_attr(self, obj, selector, w_value):
        # grumble, jit needs this
        attr = self._get_new_attr(selector[0], selector[1])
        oldattr = obj._get_mapdict_map()
        if not jit.we_are_jitted():
            oldattr._size_estimate += attr.size_estimate() - oldattr.size_estimate()
        if attr.length() > len(obj._get_mapdict_storage()):
            # note that attr.size_estimate() is always at least attr.length()
            new_storage = [None] * attr.size_estimate()
            for i in range(len(obj._get_mapdict_storage())):
                new_storage[i] = obj._get_mapdict_storage()[i]
            obj._set_mapdict_storage(new_storage)

        obj._get_mapdict_storage()[attr.position] = w_value
        obj._set_mapdict_map(attr)

    def materialize_r_dict(self, space, obj, w_d):
        raise NotImplementedError("abstract base class")

    def remove_dict_entries(self, obj):
        raise NotImplementedError("abstract base class")


class Terminator(AbstractAttribute):
    _immutable_ = True
    def __init__(self, w_cls, space):
        self.w_cls = w_cls
        self.space = space

    def read(self, obj, selector):
        return None

    def write(self, obj, selector, w_value):
        obj._get_mapdict_map().add_attr(obj, selector, w_value)
        return True

    def copy(self, obj):
        result = Object()
        result.space = self.space
        result._init_empty(self)
        return result

    def length(self):
        return 0

    def get_terminator(self):
        return self

    def set_terminator(self, obj, terminator):
        result = Object()
        result.space = self.space
        result._init_empty(terminator)
        return result

    def remove_dict_entries(self, obj):
        return self.copy(obj)

class DictTerminator(Terminator):
    _immutable_ = True
    def __init__(self, w_cls, space):
        Terminator.__init__(self, w_cls, space)
        self.devolved_dict_terminator = DevolvedDictTerminator(w_cls, space)

    def materialize_r_dict(self, space, obj, w_d):
        result = Object()
        result.space = space
        result._init_empty(self.devolved_dict_terminator)
        return result


class NoDictTerminator(Terminator):
    def write(self, obj, selector, w_value):
        if selector[1] == DICT:
            return False
        return Terminator.write(self, obj, selector, w_value)


class DevolvedDictTerminator(Terminator):
    def read(self, obj, selector):
        if selector[1] == DICT:
            w_dict = obj.getdict()
            space = self.space
            return space.finditem_str(w_dict, selector[0])
        return Terminator.read(self, obj, selector)

    def write(self, obj, selector, w_value):
        if selector[1] == DICT:
            w_dict = obj.getdict()
            space = self.space
            space.setitem_str(w_dict, selector[0], w_value)
            return True
        return Terminator.write(self, obj, selector, w_value)

    def delete(self, obj, selector):
        from pypy.interpreter.error import OperationError
        if selector[1] == DICT:
            w_dict = obj.getdict()
            space = self.space
            try:
                space.delitem(w_dict, space.wrap(selector[0]))
            except OperationError, ex:
                if not ex.match(space, space.w_KeyError):
                    raise
            return Terminator.copy(self, obj)
        return Terminator.delete(self, obj, selector)

    def remove_dict_entries(self, obj):
        assert 0, "should be unreachable"

    def set_terminator(self, obj, terminator):
        if not isinstance(terminator, DevolvedDictTerminator):
            assert isinstance(terminator, DictTerminator)
            terminator = terminator.devolved_dict_terminator
        return Terminator.set_terminator(self, obj, terminator)

class PlainAttribute(AbstractAttribute):
    _immutable_ = True
    def __init__(self, selector, back):
        self.selector = selector
        self.position = back.length()
        self.back = back
        self._size_estimate = self.length() << NUM_DIGITS

    def _copy_attr(self, obj, new_obj):
        w_value = self.read(obj, self.selector)
        new_obj._get_mapdict_map().add_attr(new_obj, self.selector, w_value)

    def read(self, obj, selector):
        if selector == self.selector:
            return obj._get_mapdict_storage()[self.position]
        return self.back.read(obj, selector)

    def write(self, obj, selector, w_value):
        if selector == self.selector:
            obj._get_mapdict_storage()[self.position] = w_value
            return True
        return self.back.write(obj, selector, w_value)

    def delete(self, obj, selector):
        if self.selector == selector:
            # ok, attribute is deleted
            return self.back.copy(obj)
        new_obj = self.back.delete(obj, selector)
        if new_obj is not None:
            self._copy_attr(obj, new_obj)
        return new_obj

    def copy(self, obj):
        new_obj = self.back.copy(obj)
        self._copy_attr(obj, new_obj)
        return new_obj

    def length(self):
        return self.position + 1

    def get_terminator(self):
        return self.back.get_terminator()

    def set_terminator(self, obj, terminator):
        new_obj = self.back.set_terminator(obj, terminator)
        self._copy_attr(obj, new_obj)
        return new_obj

    def search(self, attrtype):
        if self.selector[1] == attrtype:
            return self
        return self.back.search(attrtype)

    def materialize_r_dict(self, space, obj, w_d):
        new_obj = self.back.materialize_r_dict(space, obj, w_d)
        if self.selector[1] == DICT:
            w_attr = space.wrap(self.selector[0])
            w_d.r_dict_content[w_attr] = obj._get_mapdict_storage()[self.position]
        else:
            self._copy_attr(obj, new_obj)
        return new_obj

    def remove_dict_entries(self, obj):
        new_obj = self.back.remove_dict_entries(obj)
        if self.selector[1] != DICT:
            self._copy_attr(obj, new_obj)
        return new_obj

def _become(w_obj, new_obj):
    # this is like the _become method, really, but we cannot use that due to
    # RPython reasons
    w_obj._set_mapdict_map(new_obj.map)
    w_obj._set_mapdict_storage(new_obj.storage)
# ____________________________________________________________
# object implementation

DICT = 0
SPECIAL = 1
SLOTS_STARTING_FROM = 2

from pypy.interpreter.baseobjspace import W_Root

class Object(W_Root): # slightly evil to make it inherit from W_Root
    def _init_empty(self, map):
        from pypy.rlib.debug import make_sure_not_resized
        self.map = map
        self.storage = make_sure_not_resized([None] * map.size_estimate())
    def _become(self, new_obj):
        self.map = new_obj.map
        self.storage = new_obj.storage

    def _get_mapdict_map(self):
        return jit.hint(self.map, promote=True)
    def _get_mapdict_storage(self):
        return self.storage
    def _set_mapdict_map(self, map):
        self.map = map
    def _set_mapdict_storage(self, storage):
        self.storage = storage

    # _____________________________________________
    # objspace interface

    def getdictvalue(self, space, attrname):
        return self._get_mapdict_map().read(self, (attrname, DICT))

    def setdictvalue(self, space, attrname, w_value, shadows_type=True):
        return self._get_mapdict_map().write(self, (attrname, DICT), w_value)

    def deldictvalue(self, space, w_name):
        attrname = space.str_w(w_name)
        new_obj = self._get_mapdict_map().delete(self, (attrname, DICT))
        if new_obj is None:
            return False
        self._become(new_obj)
        return True

    def getdict(self):
        w_dict = self._get_mapdict_map().read(self, ("dict", SPECIAL))
        if w_dict is not None:
            assert isinstance(w_dict, W_DictMultiObject)
            return w_dict
        w_dict = MapDictImplementation(self.space, self)
        flag = self._get_mapdict_map().write(self, ("dict", SPECIAL), w_dict)
        assert flag
        return w_dict

    def setdict(self, space, w_dict):
        from pypy.interpreter.typedef import check_new_dictionary
        w_dict = check_new_dictionary(space, w_dict)
        w_olddict = self.getdict()
        assert isinstance(w_dict, W_DictMultiObject)
        w_olddict._as_rdict()
        flag = self._get_mapdict_map().write(self, ("dict", SPECIAL), w_dict)
        assert flag

    def getclass(self, space):
        return self._get_mapdict_map().get_terminator().w_cls

    def setclass(self, space, w_cls):
        new_obj = self._get_mapdict_map().set_terminator(self, w_cls.terminator)
        self._become(new_obj)

    def user_setup(self, space, w_subtype):
        self.space = space
        assert not self.typedef.hasdict
        self._init_empty(w_subtype.terminator)

    def getslotvalue(self, index):
        key = ("slot", SLOTS_STARTING_FROM + index)
        return self._get_mapdict_map().read(self, key)

    def setslotvalue(self, index, w_value):
        key = ("slot", SLOTS_STARTING_FROM + index)
        self._get_mapdict_map().write(self, key, w_value)

    # used by _weakref implemenation

    def getweakref(self):
        from pypy.module._weakref.interp__weakref import WeakrefLifeline
        lifeline = self._get_mapdict_map().read(self, ("weakref", SPECIAL))
        if lifeline is None:
            return None
        assert isinstance(lifeline, WeakrefLifeline)
        return lifeline

    def setweakref(self, space, weakreflifeline):
        from pypy.module._weakref.interp__weakref import WeakrefLifeline
        assert isinstance(weakreflifeline, WeakrefLifeline)
        self._get_mapdict_map().write(self, ("weakref", SPECIAL), weakreflifeline)


# ____________________________________________________________
# dict implementation

from pypy.objspace.std.dictmultiobject import W_DictMultiObject
from pypy.objspace.std.dictmultiobject import IteratorImplementation
from pypy.objspace.std.dictmultiobject import _is_sane_hash

class MapDictImplementation(W_DictMultiObject):
    def __init__(self, space, w_obj):
        self.space = space
        self.w_obj = w_obj

    def impl_getitem(self, w_lookup):
        space = self.space
        w_lookup_type = space.type(w_lookup)
        if space.is_w(w_lookup_type, space.w_str):
            return self.impl_getitem_str(space.str_w(w_lookup))
        elif _is_sane_hash(space, w_lookup_type):
            return None
        else:
            return self._as_rdict().impl_fallback_getitem(w_lookup)

    def impl_getitem_str(self, key):
        return self.w_obj.getdictvalue(self.space, key)

    def impl_setitem_str(self,  key, w_value, shadows_type=True):
        flag = self.w_obj.setdictvalue(self.space, key, w_value, shadows_type)
        assert flag

    def impl_setitem(self,  w_key, w_value):
        space = self.space
        if space.is_w(space.type(w_key), space.w_str):
            self.impl_setitem_str(self.space.str_w(w_key), w_value)
        else:
            self._as_rdict().impl_fallback_setitem(w_key, w_value)

    def impl_delitem(self, w_key):
        space = self.space
        w_key_type = space.type(w_key)
        if space.is_w(w_key_type, space.w_str):
            flag = self.w_obj.deldictvalue(space, w_key)
            if not flag:
                raise KeyError
        elif _is_sane_hash(space, w_key_type):
            raise KeyError
        else:
            self._as_rdict().impl_fallback_delitem(w_key)

    def impl_length(self):
        res = 0
        curr = self.w_obj._get_mapdict_map().search(DICT)
        while curr is not None:
            curr = curr.back
            curr = curr.search(DICT)
            res += 1
        return res

    def impl_iter(self):
        return MapDictIteratorImplementation(self.space, self)

    def impl_clear(self):
        w_obj = self.w_obj
        new_obj = w_obj._get_mapdict_map().remove_dict_entries(w_obj)
        _become(w_obj, new_obj)

    def _clear_fields(self):
        self.w_obj = None

    def _as_rdict(self):
        self.initialize_as_rdict()
        space = self.space
        w_obj = self.w_obj
        materialize_r_dict(space, w_obj, self)
        self._clear_fields()
        return self


def materialize_r_dict(space, obj, w_d):
    map = obj._get_mapdict_map()
    assert obj.getdict() is w_d
    new_obj = map.materialize_r_dict(space, obj, w_d)
    _become(obj, new_obj)

class MapDictIteratorImplementation(IteratorImplementation):
    def __init__(self, space, dictimplementation):
        IteratorImplementation.__init__(self, space, dictimplementation)
        w_obj = dictimplementation.w_obj
        self.w_obj = w_obj
        self.orig_map = self.curr_map = w_obj._get_mapdict_map()

    def next_entry(self):
        implementation = self.dictimplementation
        assert isinstance(implementation, MapDictImplementation)
        if self.orig_map is not self.w_obj._get_mapdict_map():
            return None, None
        if self.curr_map:
            curr_map = self.curr_map.search(DICT)
            if curr_map:
                self.curr_map = curr_map.back
                attr = curr_map.selector[0]
                w_attr = self.space.wrap(attr)
                return w_attr, self.w_obj.getdictvalue(self.space, attr)
        return None, None
