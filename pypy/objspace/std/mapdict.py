

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
        raise NotImplementedError("abstract base class")

    def length(self):
        raise NotImplementedError("abstract base class")

    def get_terminator(self):
        raise NotImplementedError("abstract base class")

    def set_terminator(self, obj, terminator):
        raise NotImplementedError("abstract base class")

    def size_estimate(self):
        return self._size_estimate >> NUM_DIGITS

    def search(self, attrtype):
        return None

    def add_attr(self, obj, selector, w_value):
        cache = self.cache_attrs
        if cache is None:
            cache = self.cache_attrs = {}
        attr = cache.get(selector, None)
        if attr is None:
            attr = PlainAttribute(selector, self)
            cache[selector] = attr
        oldattr = obj.map
        oldattr._size_estimate += attr.size_estimate() - oldattr.size_estimate()
        if attr.length() > len(obj.storage):
            new_storage = [None] * attr.size_estimate()
            for i in range(len(obj.storage)):
                new_storage[i] = obj.storage[i]
            obj.storage = new_storage

        obj.storage[attr.position] = w_value
        obj.map = attr


class Terminator(AbstractAttribute):
    def __init__(self, w_cls=None):
        self.w_cls = w_cls

    def read(self, obj, selector):
        return None

    def write(self, obj, selector, w_value):
        obj.map.add_attr(obj, selector, w_value)
        return True

    def delete(self, obj, selector):
        result = Object()
        result._init_empty(self)
        return result

    def length(self):
        return 0

    def get_terminator(self):
        return self

    def set_terminator(self, obj, terminator):
        result = Object()
        result._init_empty(terminator)
        return result

class NoDictTerminator(Terminator):
    def write(self, obj, selector, w_value):
        if selector[1] == DICT:
            return False
        return Terminator.write(self, obj, selector, w_value)

class PlainAttribute(AbstractAttribute):
    def __init__(self, selector, back):
        self.selector = selector
        self.position = back.length()
        self.back = back
        self._size_estimate = self.length() << NUM_DIGITS

    def _copy_attr(self, obj, new_obj):
        w_value = self.read(obj, self.selector)
        new_obj.map.add_attr(new_obj, self.selector, w_value)

    def read(self, obj, selector):
        if selector == self.selector:
            return obj.storage[self.position]
        return self.back.read(obj, selector)

    def write(self, obj, selector, w_value):
        if selector == self.selector:
            obj.storage[self.position] = w_value
            return True
        return self.back.write(obj, selector, w_value)

    def delete(self, obj, selector):
        new_obj = self.back.delete(obj, selector)
        if self.selector != selector:
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


# ____________________________________________________________
# object implementation

DICT = 6
SLOT = 1
SPECIAL = 2

class Object(object):
    def _init_empty(self, map):
        self.map = map
        self.storage = [None] * map.size_estimate()
    def _become(self, new_obj):
        self.map = new_obj.map
        self.storage = new_obj.storage

    # _____________________________________________
    # objspace interface

    def getdictvalue(self, space, attrname):
        return self.map.read(self, (attrname, DICT))

    def setdictvalue(self, space, attrname, w_value, shadows_type=True):
        return self.map.write(self, (attrname, DICT), w_value)

    def deldictvalue(self, space, w_name):
        attrname = space.str_w(w_name)
        new_obj = self.map.delete(self, (attrname, DICT))
        # XXX too slow?
        if new_obj.map is self.map and new_obj.storage == self.storage:
            return False
        self._become(new_obj)
        return True

    def getdict(self):
        w_dict = self.map.read(self, ("dict", SPECIAL))
        if w_dict is not None:
            return w_dict
        w_dict = MapDictImplementation(self.space, self)
        self.map.write(self, ("dict", SPECIAL), w_dict)
        return w_dict

    def setdict(self, space, w_dict):
        XXX_here_be_monster
        typename = space.type(self).getname(space, '?')
        raise operationerrfmt(space.w_TypeError,
                              "attribute '__dict__' of %s objects "
                              "is not writable", typename)

    def getclass(self, space):
        return self.map.get_terminator().w_cls

    def setclass(self, space, w_cls):
        new_obj = self.map.set_terminator(self, w_cls.terminator)
        self._become(new_obj)

    def user_setup(self, space, w_subtype):
        self.space = space
        self._init_empty(w_subtype.terminator)

    def getslotvalue(self, member):
        return self.map.read(self, (member.name, SLOT))

    def setslotvalue(self, member, w_value):
        self.map.write(self, (member.name, SLOT), w_value)

    # used by _weakref implemenation

    def getweakref(self):
        return self.map.read(self, ("weakref", SPECIAL))

    def setweakref(self, space, weakreflifeline):
        self.map.write(self, ("weakref", SPECIAL), weakreflifeline)

# ____________________________________________________________
# dict implementation

from pypy.objspace.std.dictmultiobject import W_DictMultiObject
from pypy.objspace.std.dictmultiobject import IteratorImplementation

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
            return self._as_rdict().getitem(w_lookup)

    def impl_getitem_str(self, key):
        return self.w_obj.getdictvalue(self.space, key)

    def impl_setitem_str(self,  key, w_value, shadows_type=True):
        flag = self.w_obj.setdictvalue(self.space, key, w_value)
        assert flag

    def impl_setitem(self,  w_key, w_value):
        space = self.space
        if space.is_w(space.type(w_key), space.w_str):
            self.impl_setitem_str(self.space.str_w(w_key), w_value)
        else:
            self._as_rdict().setitem(w_key, w_value)

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
            self._as_rdict().delitem(w_key)

    def impl_length(self):
        res = 0
        # XXX not RPython yet
        curr = self.w_obj.map.search(DICT)
        while curr is not None:
            curr = curr.back
            curr = curr.search(DICT)
            res += 1
        return res

    def impl_iter(self):
        return MapDictIteratorImplementation(self.space, self)

    def impl_clear(self):
        raise NotImplementedError("abstract base class")

    def _clear_fields(self):
        self.w_obj = None

    def _as_rdict(self):
        r_dict_content = self.initialize_as_rdict()
        space = self.space
        w_obj = self.w_obj
        curr = w_obj.map.search(DICT)
        while curr is not None:
            attr = curr.selector[0]
            r_dict_content[space.wrap(attr)] = w_obj.getdictvalue(space, attr)
            curr = curr.back
            curr = curr.search(DICT)
        self._clear_fields()
        return self


def _materialize_r_dict(space, obj, w_d):
    assert isinstance(w_d, MapDictImplementation)
    #XXX

class MapDictIteratorImplementation(IteratorImplementation):
    def __init__(self, space, dictimplementation):
        IteratorImplementation.__init__(self, space, dictimplementation)
        w_obj = dictimplementation.w_obj
        self.w_obj = w_obj
        # XXX
        self.orig_map = self.curr_map = w_obj.map

    def next_entry(self):
        implementation = self.dictimplementation
        assert isinstance(implementation, MapDictImplementation)
        if self.orig_map is not self.w_obj.map:
            return None, None
        if self.curr_map:
            curr_map = self.curr_map.search(DICT)
            if curr_map:
                self.curr_map = curr_map.back
                attr = curr_map.selector[0]
                return attr, self.w_obj.getdictvalue(self.space, attr)
        return None, None
