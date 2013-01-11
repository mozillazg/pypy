
import sys
from pypy.tool.pairtype import pairtype
from pypy.objspace.flow.model import Constant
from pypy.rpython.rdict import (AbstractDictRepr, AbstractDictIteratorRepr,
                                rtype_newdict)
from pypy.rpython.lltypesystem import lltype, llmemory, rffi
from pypy.rpython.lltypesystem.lloperation import llop
from pypy.rlib import objectmodel, jit, rgc
from pypy.rlib.debug import ll_assert
from pypy.rlib.objectmodel import specialize
from pypy.rlib.rarithmetic import r_uint, intmask, LONG_BIT
from pypy.rpython import rmodel
from pypy.rpython.error import TyperError


HIGHEST_BIT = intmask(1 << (LONG_BIT - 1))
MASK = intmask(HIGHEST_BIT - 1)

FREE = -2
DELETED = -1

# ____________________________________________________________
#
#  generic implementation of RPython dictionary, with parametric DICTKEY and
#  DICTVALUE types.
#
#
#    struct dictentry {
#        DICTKEY key;
#        DICTVALUE value;
#        int f_hash;        # (optional) key hash, if hard to recompute
#    }
#
#    struct dicttable {
#        int num_items;
#        int size;
#        int resize_counter;
#        int *indexes; # note that this can be different int
#        Array *entries;
#        (Function DICTKEY, DICTKEY -> bool) *fnkeyeq;
#        (Function DICTKEY -> int) *fnkeyhash;
#    }
#
#

def get_ll_dict(DICTKEY, DICTVALUE, get_custom_eq_hash=None, DICT=None,
                ll_fasthash_function=None, ll_hash_function=None,
                ll_eq_function=None, method_cache={}):
    # get the actual DICT type. if DICT is None, it's created, otherwise
    # forward reference is becoming DICT
    if DICT is None:
        DICT = lltype.GcForwardReference()
    # compute the shape of the DICTENTRY structure
    entryfields = []
    entrymeths = {'allocate': lltype.typeMethod(_ll_malloc_entries),
                  'valid': ll_valid_entry,
                  'clear_key': (isinstance(DICTKEY, lltype.Ptr) and
                                DICTKEY._needsgc()),
                  'clear_value': (isinstance(DICTVALUE, lltype.Ptr) and
                                  DICTVALUE._needsgc()),
                  'getitem': ll_entry_getitem,
                  # no boundary checking versions
                  'getitem_clean': ll_entry_getitem_clean,
                  'popitem': ll_entry_popitem}

    # * the key
    entryfields.append(("key", DICTKEY))

    # * the value
    entryfields.append(("value", DICTVALUE))

    # * the hash, if needed
    if get_custom_eq_hash is not None:
        fasthashfn = None
    else:
        fasthashfn = ll_fasthash_function
    if fasthashfn is None:
        entryfields.append(("f_hash", lltype.Signed))
        entrymeths['hash'] = ll_hash_from_cache
    else:
        entrymeths['hash'] = ll_hash_recomputed
        entrymeths['fasthashfn'] = fasthashfn

    # Build the lltype data structures
    DICTENTRY = lltype.Struct("dictentry", *entryfields)
    DICTENTRYARRAY = lltype.GcArray(DICTENTRY,
                                    adtmeths=entrymeths)
    
    fields = [("num_items", lltype.Signed),
              ("resize_counter", lltype.Signed),
              ("size", lltype.Signed),
              ("entries", lltype.Ptr(DICTENTRYARRAY)),
              ("indexes", llmemory.GCREF)]
    if get_custom_eq_hash is not None:
        r_rdict_eqfn, r_rdict_hashfn = get_custom_eq_hash()
        fields.extend([ ("fnkeyeq", r_rdict_eqfn.lowleveltype),
                        ("fnkeyhash", r_rdict_hashfn.lowleveltype) ])
        adtmeths = {
            'keyhash':        ll_keyhash_custom,
            'keyeq':          ll_keyeq_custom,
            'r_rdict_eqfn':   r_rdict_eqfn,
            'r_rdict_hashfn': r_rdict_hashfn,
            'paranoia':       True,
            }
    else:
        # figure out which functions must be used to hash and compare
        ll_keyhash = ll_hash_function
        ll_keyeq = ll_eq_function  # can be None
        ll_keyhash = lltype.staticAdtMethod(ll_keyhash)
        if ll_keyeq is not None:
            ll_keyeq = lltype.staticAdtMethod(ll_keyeq)
        adtmeths = {
            'keyhash':  ll_keyhash,
            'keyeq':    ll_keyeq,
            'paranoia': False,
            }
    adtmeths['KEY']   = DICTKEY
    adtmeths['VALUE'] = DICTVALUE
    adtmeths['allocate'] = lltype.typeMethod(_ll_malloc_dict)
    adtmeths['resize'] = ll_dict_resize
    DICT.become(lltype.GcStruct("dicttable", adtmeths=adtmeths,
                                *fields))
    return DICT

class DictRepr(AbstractDictRepr):

    def __init__(self, rtyper, key_repr, value_repr, dictkey, dictvalue,
                 custom_eq_hash=None):
        self.rtyper = rtyper
        self.DICT = lltype.GcForwardReference()
        self.lowleveltype = lltype.Ptr(self.DICT)
        self.custom_eq_hash = custom_eq_hash
        if not isinstance(key_repr, rmodel.Repr):  # not computed yet, done by setup()
            assert callable(key_repr)
            self._key_repr_computer = key_repr
        else:
            self.external_key_repr, self.key_repr = self.pickkeyrepr(key_repr)
        if not isinstance(value_repr, rmodel.Repr):  # not computed yet, done by setup()
            assert callable(value_repr)
            self._value_repr_computer = value_repr
        else:
            self.external_value_repr, self.value_repr = self.pickrepr(value_repr)
        self.dictkey = dictkey
        self.dictvalue = dictvalue
        self.dict_cache = {}
        # setup() needs to be called to finish this initialization

    def _externalvsinternal(self, rtyper, item_repr):
        return rmodel.externalvsinternal(self.rtyper, item_repr)

    def _setup_repr(self):
        if 'key_repr' not in self.__dict__:
            key_repr = self._key_repr_computer()
            self.external_key_repr, self.key_repr = self.pickkeyrepr(key_repr)
        if 'value_repr' not in self.__dict__:
            self.external_value_repr, self.value_repr = self.pickrepr(self._value_repr_computer())
        if isinstance(self.DICT, lltype.GcForwardReference):
            DICTKEY = self.key_repr.lowleveltype
            DICTVALUE = self.value_repr.lowleveltype
            kwd = {}
            if self.custom_eq_hash:
                kwd['get_custom_eq_hash'] = self.custom_eq_hash
            else:
                kwd['ll_hash_function'] = self.key_repr.get_ll_hash_function()
                kwd['ll_eq_function'] = self.key_repr.get_ll_eq_function()
                kwd['ll_fasthash_function'] = self.key_repr.get_ll_fasthash_function()
            get_ll_dict(DICTKEY, DICTVALUE, DICT=self.DICT, **kwd)
            if self.custom_eq_hash is not None:
                self.r_rdict_eqfn, self.r_rdict_hashfn = self.custom_eq_hash()

    def convert_const(self, dictobj):
        from pypy.rpython.lltypesystem import llmemory
        # get object from bound dict methods
        #dictobj = getattr(dictobj, '__self__', dictobj)
        if dictobj is None:
            return lltype.nullptr(self.DICT)
        if not isinstance(dictobj, (dict, objectmodel.r_dict)):
            raise TypeError("expected a dict: %r" % (dictobj,))
        try:
            key = Constant(dictobj)
            return self.dict_cache[key]
        except KeyError:
            self.setup()
            l_dict = ll_newdict_size(self.DICT, len(dictobj))
            self.dict_cache[key] = l_dict
            r_key = self.key_repr
            if r_key.lowleveltype == llmemory.Address:
                raise TypeError("No prebuilt dicts of address keys")
            r_value = self.value_repr
            if isinstance(dictobj, objectmodel.r_dict):
                if self.r_rdict_eqfn.lowleveltype != lltype.Void:
                    l_fn = self.r_rdict_eqfn.convert_const(dictobj.key_eq)
                    l_dict.fnkeyeq = l_fn
                if self.r_rdict_hashfn.lowleveltype != lltype.Void:
                    l_fn = self.r_rdict_hashfn.convert_const(dictobj.key_hash)
                    l_dict.fnkeyhash = l_fn

                for dictkeycontainer, dictvalue in dictobj._dict.items():
                    llkey = r_key.convert_const(dictkeycontainer.key)
                    llvalue = r_value.convert_const(dictvalue)
                    # we cannot call normal ll_dict_setitem here
                    # because calling keyhash might potentially
                    # be illegal
                    ll_dict_insertclean(l_dict, llkey, llvalue,
                                        dictkeycontainer.hash)
                return l_dict

            else:
                for dictkey, dictvalue in dictobj.items():
                    llkey = r_key.convert_const(dictkey)
                    llvalue = r_value.convert_const(dictvalue)
                    ll_dict_setitem(l_dict, llkey, llvalue)
                return l_dict

    def rtype_len(self, hop):
        v_dict, = hop.inputargs(self)
        return hop.gendirectcall(ll_dict_len, v_dict)

    def rtype_is_true(self, hop):
        v_dict, = hop.inputargs(self)
        return hop.gendirectcall(ll_dict_is_true, v_dict)

    def make_iterator_repr(self, *variant):
        return DictIteratorRepr(self, *variant)

    def rtype_method_get(self, hop):
        v_dict, v_key, v_default = hop.inputargs(self, self.key_repr,
                                                 self.value_repr)
        hop.exception_cannot_occur()
        v_res = hop.gendirectcall(ll_get, v_dict, v_key, v_default)
        return self.recast_value(hop.llops, v_res)

    def rtype_method_setdefault(self, hop):
        v_dict, v_key, v_default = hop.inputargs(self, self.key_repr,
                                                 self.value_repr)
        hop.exception_cannot_occur()
        v_res = hop.gendirectcall(ll_setdefault, v_dict, v_key, v_default)
        return self.recast_value(hop.llops, v_res)

    def rtype_method_copy(self, hop):
        v_dict, = hop.inputargs(self)
        hop.exception_cannot_occur()
        return hop.gendirectcall(ll_copy, v_dict)

    def rtype_method_update(self, hop):
        v_dic1, v_dic2 = hop.inputargs(self, self)
        hop.exception_cannot_occur()
        return hop.gendirectcall(ll_update, v_dic1, v_dic2)

    def _rtype_method_kvi(self, hop, ll_func):
        v_dic, = hop.inputargs(self)
        r_list = hop.r_result
        cLIST = hop.inputconst(lltype.Void, r_list.lowleveltype.TO)
        hop.exception_cannot_occur()
        return hop.gendirectcall(ll_func, cLIST, v_dic)

    def rtype_method_keys(self, hop):
        return self._rtype_method_kvi(hop, ll_dict_keys)

    def rtype_method_values(self, hop):
        return self._rtype_method_kvi(hop, ll_dict_values)

    def rtype_method_items(self, hop):
        return self._rtype_method_kvi(hop, ll_dict_items)

    def rtype_method_iterkeys(self, hop):
        hop.exception_cannot_occur()
        return DictIteratorRepr(self, "keys").newiter(hop)

    def rtype_method_itervalues(self, hop):
        hop.exception_cannot_occur()
        return DictIteratorRepr(self, "values").newiter(hop)

    def rtype_method_iteritems(self, hop):
        hop.exception_cannot_occur()
        return DictIteratorRepr(self, "items").newiter(hop)

    def rtype_method_clear(self, hop):
        v_dict, = hop.inputargs(self)
        hop.exception_cannot_occur()
        return hop.gendirectcall(ll_clear, v_dict)

    def rtype_method_popitem(self, hop):
        v_dict, = hop.inputargs(self)
        r_tuple = hop.r_result
        cTUPLE = hop.inputconst(lltype.Void, r_tuple.lowleveltype)
        hop.exception_is_here()
        return hop.gendirectcall(ll_popitem, cTUPLE, v_dict)

    def rtype_method_pop(self, hop):
        if hop.nb_args == 2:
            v_args = hop.inputargs(self, self.key_repr)
            target = ll_pop
        elif hop.nb_args == 3:
            v_args = hop.inputargs(self, self.key_repr, self.value_repr)
            target = ll_pop_default
        hop.exception_is_here()
        v_res = hop.gendirectcall(target, *v_args)
        return self.recast_value(hop.llops, v_res)

class __extend__(pairtype(DictRepr, rmodel.Repr)):

    def rtype_getitem((r_dict, r_key), hop):
        v_dict, v_key = hop.inputargs(r_dict, r_dict.key_repr)
        if not r_dict.custom_eq_hash:
            hop.has_implicit_exception(KeyError)   # record that we know about it
        hop.exception_is_here()
        v_res = hop.gendirectcall(ll_dict_getitem, v_dict, v_key)
        return r_dict.recast_value(hop.llops, v_res)

    def rtype_delitem((r_dict, r_key), hop):
        v_dict, v_key = hop.inputargs(r_dict, r_dict.key_repr)
        if not r_dict.custom_eq_hash:
            hop.has_implicit_exception(KeyError)   # record that we know about it
        hop.exception_is_here()
        return hop.gendirectcall(ll_dict_delitem, v_dict, v_key)

    def rtype_setitem((r_dict, r_key), hop):
        v_dict, v_key, v_value = hop.inputargs(r_dict, r_dict.key_repr, r_dict.value_repr)
        if r_dict.custom_eq_hash:
            hop.exception_is_here()
        else:
            hop.exception_cannot_occur()
        hop.gendirectcall(ll_dict_setitem, v_dict, v_key, v_value)

    def rtype_contains((r_dict, r_key), hop):
        v_dict, v_key = hop.inputargs(r_dict, r_dict.key_repr)
        hop.exception_is_here()
        return hop.gendirectcall(ll_contains, v_dict, v_key)

class __extend__(pairtype(DictRepr, DictRepr)):
    def convert_from_to((r_dict1, r_dict2), v, llops):
        # check that we don't convert from Dicts with
        # different key/value types
        if r_dict1.dictkey is None or r_dict2.dictkey is None:
            return NotImplemented
        if r_dict1.dictkey is not r_dict2.dictkey:
            return NotImplemented
        if r_dict1.dictvalue is None or r_dict2.dictvalue is None:
            return NotImplemented
        if r_dict1.dictvalue is not r_dict2.dictvalue:
            return NotImplemented
        return v

# ____________________________________________________________
#
#  Low-level methods.  These can be run for testing, but are meant to
#  be direct_call'ed from rtyped flow graphs, which means that they will
#  get flowed and annotated, mostly with SomePtr.

# --------------------- indexes ------------------

DICTINDEX_SIGNED = lltype.Ptr(lltype.GcArray(lltype.Signed))
DICTINDEX_INT = lltype.Ptr(lltype.GcArray(rffi.INT_real))
DICTINDEX_SHORT = lltype.Ptr(lltype.GcArray(rffi.SHORT))
DICTINDEX_BYTE = lltype.Ptr(lltype.GcArray(rffi.SIGNEDCHAR))

def _ll_malloc_indexes(n):
    if IS_64BIT and n < 2 ** 31:
        res = lltype.cast_opaque_ptr(llmemory.GCREF,
                                     lltype.malloc(DICTINDEX_INT.TO, n,
                                                   zero=True))        
    else:
        res = lltype.cast_opaque_ptr(llmemory.GCREF,
                                     lltype.malloc(DICTINDEX_SIGNED.TO, n,
                                                   zero=True))
    return res

def ll_index_getitem_signed(size, indexes, i):
    return lltype.cast_opaque_ptr(DICTINDEX_SIGNED, indexes)[i] - 2

def ll_index_getitem_int(size, indexes, i):
    res = lltype.cast_opaque_ptr(DICTINDEX_INT, indexes)[i]
    return rffi.cast(lltype.Signed, res) - 2

def ll_index_setitem_signed(size, indexes, i, v):
    lltype.cast_opaque_ptr(DICTINDEX_SIGNED, indexes)[i] = v + 2

def ll_index_setitem_int(size, indexes, i, v):
    v = rffi.cast(rffi.INT_real, v + 2)
    lltype.cast_opaque_ptr(DICTINDEX_INT, indexes)[i] = v

IS_64BIT = sys.maxint != 2 ** 31 - 1

def _pick_index_setitem(d):
    if IS_64BIT and d.size < 2 ** 31:
        return ll_index_setitem_int            
    return ll_index_setitem_signed

def _pick_index_getitem(d):
    if IS_64BIT and d.size < 2 ** 31:
        return ll_index_getitem_int            
    return ll_index_getitem_signed

def d_signed_indexes(d):
    if IS_64BIT and d.size < 2 ** 31:
        return False
    return True

def ll_dict_copy_indexes(size, from_d, to_d):
    ll_index_getitem = _pick_index_getitem(from_d)
    ll_index_setitem = _pick_index_setitem(to_d)
    from_indexes = from_d.indexes
    to_indexes = to_d.indexes
    i = 0
    while i < size:
        v = ll_index_getitem(size, from_indexes, i)
        ll_index_setitem(size, to_indexes, i, v)
        i += 1

# ---------------------- entries -----------------------

def ll_entries_resize_up(d):
    lgt = len(d.entries)
    if lgt < 9:
        some = 4
    else:
        some = 7
    new_lgt = lgt + some + (lgt >> 2)
    new_entries = lltype.typeOf(d).TO.entries.TO.allocate(new_lgt)
    rgc.ll_arraycopy(d.entries, new_entries, 0, 0, lgt)
    d.entries = new_entries
    return new_entries
ll_entries_resize_up._never_inline_ = True

def ll_entry_getitem(entries, d, item):
    if len(entries) <= item:
        entries = ll_entries_resize_up(d)
    return entries[item]
ll_entry_getitem._always_inline_ = True

def ll_entry_getitem_clean(entries, item):
    return entries[item]
ll_entry_getitem_clean._always_inline_ = True

def ll_entry_popitem(d):
    pass

# ---------------------- hashes -------------------

def ll_hash_from_cache(entries, i):
    return entries[i].f_hash

def ll_valid_entry(entires, index):
    return index >= 0

def ll_hash_recomputed(entries, i):
    ENTRIES = lltype.typeOf(entries).TO
    return ENTRIES.fasthashfn(entries[i].key)

@specialize.ll_and_arg(2)
def ll_get_value(d, i, ll_index_getitem):
    return d.entries.getitem_clean(ll_index_getitem(d.size, d.indexes, i)).value

def ll_keyhash_custom(d, key):
    DICT = lltype.typeOf(d).TO
    return objectmodel.hlinvoke(DICT.r_rdict_hashfn, d.fnkeyhash, key)

def ll_keyeq_custom(d, key1, key2):
    DICT = lltype.typeOf(d).TO
    return objectmodel.hlinvoke(DICT.r_rdict_eqfn, d.fnkeyeq, key1, key2)

def ll_dict_len(d):
    return d.num_items

def ll_dict_is_true(d):
    # check if a dict is True, allowing for None
    return bool(d) and d.num_items != 0

def ll_dict_getitem(d, key):
    if d_signed_indexes(d):
        i = ll_dict_lookup(d, key, d.keyhash(key), ll_index_getitem_signed)
        if not i & HIGHEST_BIT:
            return ll_get_value(d, i, ll_index_getitem_signed)
        else:
            raise KeyError
    else:
        i = ll_dict_lookup(d, key, d.keyhash(key), ll_index_getitem_int)
        if not i & HIGHEST_BIT:
            return ll_get_value(d, i, ll_index_getitem_int)
        else:
            raise KeyError

def ll_dict_setitem(d, key, value):
    if d_signed_indexes(d):
        hash = d.keyhash(key)
        i = ll_dict_lookup(d, key, hash, ll_index_getitem_signed)
        _ll_dict_setitem_lookup_done(d, key, value, hash, i,
                                     ll_index_getitem_signed,
                                     ll_index_setitem_signed)
    else:
        hash = d.keyhash(key)
        i = ll_dict_lookup(d, key, hash, ll_index_getitem_int)
        _ll_dict_setitem_lookup_done(d, key, value, hash, i,
                                     ll_index_getitem_int,
                                     ll_index_setitem_int)

def ll_dict_insertclean(d, key, value, hash):
    if d_signed_indexes(d):
        i = ll_dict_lookup_clean(d, hash, ll_index_getitem_signed)
        _ll_dict_setitem_lookup_done(d, key, value, hash, i | HIGHEST_BIT,
                                     ll_index_getitem_signed)
    else:
        i = ll_dict_lookup_clean(d, hash, ll_index_getitem_int)
        _ll_dict_setitem_lookup_done(d, key, value, hash, i | HIGHEST_BIT,
                                     ll_index_getitem_int)

@specialize.ll_and_arg(2)
def ll_dict_lookup_clean(d, hash, ll_index_getitem):
    # a simplified version of ll_dict_lookup() which assumes that the
    # key is new, and the dictionary doesn't contain deleted entries.
    # It only finds the next free slot for the given hash.

    # this is crucial during convert_const, where we cannot call keyhash
    # directly.
    
    indexes = d.indexes
    mask = d.size - 1
    i = hash & mask
    perturb = r_uint(hash)
    while ll_index_getitem(d.size, indexes, i) >= 0:
        i = r_uint(i)
        i = (i << 2) + i + perturb + 1
        i = intmask(i) & mask
        perturb >>= PERTURB_SHIFT
    return i

def _look_inside_setitem(d, key, value, hash, i, _1, _2):
    return jit.isvirtual(d) and jit.isconstant(key)

# It may be safe to look inside always, it has a few branches though, and their
# frequencies needs to be investigated.
@jit.look_inside_iff(_look_inside_setitem)
@specialize.ll_and_arg(5, 6)
def _ll_dict_setitem_lookup_done(d, key, value, hash, i, ll_index_getitem,
                                 ll_index_setitem):
    valid = (i & HIGHEST_BIT) == 0
    i = i & MASK
    ENTRY = lltype.typeOf(d.entries).TO.OF
    index = ll_index_getitem(d.size, d.indexes, i)
    if index == FREE:
        index = d.num_items
        entry = d.entries.getitem(d, index)
        # a new entry that was never used before
        ll_assert(not valid, "valid but not everused")
        rc = d.resize_counter - 1
        if rc <= 0:       # if needed, resize the dict -- before the insertion
            d.resize()
            if d_signed_indexes(d):
                i = ll_dict_lookup_clean(d, hash, ll_index_getitem_signed)
            else:
                i = ll_dict_lookup_clean(d, hash, ll_index_getitem_int)
            # then redo the lookup for 'key'
            entry = d.entries.getitem(d, index)
            rc = d.resize_counter - 1
            ll_assert(rc > 0, "ll_dict_resize failed?")
        ll_assert(index < len(d.entries), "invalid insert")
        d.resize_counter = rc
        ll_index_setitem(d.size, d.indexes, i, index)
        entry.value = value
    elif index == DELETED:
        index = d.num_items
        entry = d.entries.getitem(d, index)
        ll_index_setitem(d.size, d.indexes, i, index)
        entry.value = value
    else:
        # override an existing or deleted entry
        entry = d.entries.getitem_clean(index)
        entry.value = value
        if valid:
            return
    entry.key = key
    if hasattr(ENTRY, 'f_hash'):  entry.f_hash = hash
    d.num_items += 1

def ll_dict_delitem(d, key):
    if d_signed_indexes(d):
        i = ll_dict_lookup(d, key, d.keyhash(key), ll_index_getitem_signed)
        if i & HIGHEST_BIT:
            raise KeyError
        _ll_dict_del(d, i, ll_index_getitem_signed, ll_index_setitem_signed)
    else:
        i = ll_dict_lookup(d, key, d.keyhash(key), ll_index_getitem_int)
        if i & HIGHEST_BIT:
            raise KeyError
        _ll_dict_del(d, i, ll_index_getitem_int, ll_index_setitem_int)

@jit.look_inside_iff(lambda d, i, _1, _2: jit.isvirtual(d) and
                     jit.isconstant(i))
@specialize.ll_and_arg(2, 3)
def _ll_dict_del(d, i, ll_index_getitem, ll_index_setitem):
    index = ll_index_getitem(d.size, d.indexes, i)
    ENTRIES = lltype.typeOf(d.entries).TO
    ENTRY = ENTRIES.OF
    if index != d.num_items - 1:
        old_entry = d.entries.getitem(d, d.num_items - 1)
        key = old_entry.key
        to_insert_i = ll_dict_lookup(d, key, d.keyhash(key), ll_index_getitem)
        ll_assert(not to_insert_i & HIGHEST_BIT, "invalid entry")
        ll_index_setitem(d.size, d.indexes, to_insert_i, index)
        # copy the value
        new_entry = d.entries.getitem_clean(index)
        new_entry.key = key
        new_entry.value = old_entry.value
        if hasattr(ENTRY, 'f_hash'):
            new_entry.f_hash = old_entry.f_hash
    # clear the key and the value if they are GC pointers
    ll_index_setitem(d.size, d.indexes, i, DELETED)
    d.num_items -= 1
    entry = d.entries.getitem_clean(d.num_items)
    if ENTRIES.clear_key:
        entry.key = lltype.nullptr(ENTRY.key.TO)
    if ENTRIES.clear_value:
        entry.value = lltype.nullptr(ENTRY.value.TO)
    ll_entry_popitem(d)
    #
    # The rest is commented out: like CPython we no longer shrink the
    # dictionary here.  It may shrink later if we try to append a number
    # of new items to it.  Unsure if this behavior was designed in
    # CPython or is accidental.  A design reason would be that if you
    # delete all items in a dictionary (e.g. with a series of
    # popitem()), then CPython avoids shrinking the table several times.
    #num_entries = len(d.entries)
    #if num_entries > DICT_INITSIZE and d.num_items <= num_entries / 4:
    #    ll_dict_resize(d)
    # A previous xxx: move the size checking and resize into a single
    # call which is opaque to the JIT when the dict isn't virtual, to
    # avoid extra branches.

def ll_dict_resize(d):
    old_entries = d.entries
    old_indexes = d.indexes
    old_size = d.size
    # make a 'new_size' estimate and shrink it if there are many
    # deleted entry markers.  See CPython for why it is a good idea to
    # quadruple the dictionary size as long as it's not too big.
    num_items = d.num_items + 1
    if num_items > 50000: new_estimate = num_items * 2
    else:                 new_estimate = num_items * 4
    new_size = DICT_INITSIZE
    while new_size <= new_estimate:
        new_size *= 2
    #
    new_item_size = new_size // 3 * 2 + 1
    ll_index_getitem = _pick_index_getitem(d)
    d.indexes = _ll_malloc_indexes(new_size)
    d.size = new_size
    d.resize_counter = new_item_size - d.num_items
    i = 0
    indexes = d.indexes
    ll_index_setitem = _pick_index_setitem(d)
    while i < old_size:
        index = ll_index_getitem(old_size, old_indexes, i)
        if old_entries.valid(index):
            # XXX we can do better here, but we have to remember about
            #     paranoia
            if d_signed_indexes(d):
                pos = ll_dict_lookup_clean(d, old_entries.hash(index),
                                           ll_index_getitem_signed)
            else:
                pos = ll_dict_lookup_clean(d, old_entries.hash(index),
                                           ll_index_getitem_int)
            ll_index_setitem(d.size, indexes, pos, index)
        i += 1

# ------- a port of CPython's dictobject.c's lookdict implementation -------
PERTURB_SHIFT = 5

_look_inside_lookup = lambda d, key, hash, _: jit.isvirtual(d) and jit.isconstant(key)
from pypy.rlib.objectmodel import compute_identity_hash

def ll_debugrepr(x):
    if x:
        h = compute_identity_hash(x)
    else:
        h = 0
    return '<%x>' % (h,)

@jit.look_inside_iff(_look_inside_lookup)
@specialize.ll_and_arg(3)
def ll_dict_lookup(d, key, hash, ll_index_getitem):
    entries = d.entries
    indexes = d.indexes
    mask = d.size - 1
    i = hash & mask
    # do the first try before any looping
    ENTRIES = lltype.typeOf(entries).TO
    direct_compare = not hasattr(ENTRIES, 'no_direct_compare')
    index = ll_index_getitem(d.size, indexes, i)
    if entries.valid(index):
        checkingkey = entries.getitem_clean(index).key
        if direct_compare and checkingkey == key:
            return i   # found the entry
        if d.keyeq is not None and entries.hash(index) == hash:
            # correct hash, maybe the key is e.g. a different pointer to
            # an equal object
            found = d.keyeq(checkingkey, key)
            #llop.debug_print(lltype.Void, "comparing keys", ll_debugrepr(checkingkey), ll_debugrepr(key), found)
            if d.paranoia:
                if (entries != d.entries or indexes != d.indexes or
                    not entries.valid(ll_index_getitem(d.size, indexes, i))
                    or entries.getitem_clean(index).key != checkingkey):
                    # the compare did major nasty stuff to the dict: start over
                    if d_signed_indexes(d):
                        return ll_dict_lookup(d, key, hash,
                                              ll_index_getitem_signed)
                    else:
                        return ll_dict_lookup(d, key, hash,
                                              ll_index_getitem_int)
            if found:
                return i   # found the entry
        freeslot = -1
    elif index == DELETED:
        freeslot = i
    else:
        return i | HIGHEST_BIT # pristine entry -- lookup failed

    # In the loop, a deleted entry (everused and not valid) is by far
    # (factor of 100s) the least likely outcome, so test for that last.
    perturb = r_uint(hash)
    while 1:
        # compute the next index using unsigned arithmetic
        i = r_uint(i)
        i = (i << 2) + i + perturb + 1
        i = intmask(i) & mask
        index = ll_index_getitem(d.size, indexes, i)
        # keep 'i' as a signed number here, to consistently pass signed
        # arguments to the small helper methods.
        if index == FREE:
            if freeslot == -1:
                freeslot = i
            return freeslot | HIGHEST_BIT
        elif entries.valid(index):
            checkingkey = entries.getitem_clean(index).key
            if direct_compare and checkingkey == key:
                return i
            if d.keyeq is not None and entries.hash(index) == hash:
                # correct hash, maybe the key is e.g. a different pointer to
                # an equal object
                found = d.keyeq(checkingkey, key)
                if d.paranoia:
                    if (entries != d.entries or indexes != d.indexes or
                        not entries.valid(ll_index_getitem(d.size, indexes, i)) or
                        entries.getitem_clean(index).key != checkingkey):
                        # the compare did major nasty stuff to the dict:
                        # start over
                        if d_signed_indexes(d):
                            return ll_dict_lookup(d, key, hash,
                                                  ll_index_getitem_signed)
                        else:
                            return ll_dict_lookup(d, key, hash,
                                                  ll_index_getitem_int)
                if found:
                    return i   # found the entry
        elif freeslot == -1:
            freeslot = i
        perturb >>= PERTURB_SHIFT

# ____________________________________________________________
#
#  Irregular operations.

DICT_INITSIZE = 8
DICT_ITEMS_INITSIZE = 3
DICT_RESIZE_START = 5

def ll_newdict(DICT):
    d = DICT.allocate()
    d.indexes = _ll_malloc_indexes(DICT_INITSIZE)
    d.size = DICT_INITSIZE
    d.num_items = 0
    d.entries = DICT.entries.TO.allocate(DICT_ITEMS_INITSIZE)    
    d.resize_counter = DICT_RESIZE_START
    return d

def ll_newdict_size(DICT, length_estimate):
    length_estimate = (length_estimate // 2) * 3
    n = DICT_INITSIZE
    while n < length_estimate:
        n *= 2
    items_size = n // 3 * 2 + 1
    d = DICT.allocate()
    d.entries = DICT.entries.TO.allocate(length_estimate)
    d.indexes = _ll_malloc_indexes(n)
    d.size = n
    d.num_items = 0
    d.resize_counter = items_size
    return d

# pypy.rpython.memory.lldict uses a dict based on Struct and Array
# instead of GcStruct and GcArray, which is done by using different
# 'allocate' and 'delete' adtmethod implementations than the ones below
def _ll_malloc_dict(DICT):
    return lltype.malloc(DICT)
def _ll_malloc_entries(ENTRIES, n):
    return lltype.malloc(ENTRIES, n, zero=True)

def rtype_r_dict(hop):
    r_dict = hop.r_result
    if not r_dict.custom_eq_hash:
        raise TyperError("r_dict() call does not return an r_dict instance")
    v_eqfn = hop.inputarg(r_dict.r_rdict_eqfn, arg=0)
    v_hashfn = hop.inputarg(r_dict.r_rdict_hashfn, arg=1)
    cDICT = hop.inputconst(lltype.Void, r_dict.DICT)
    hop.exception_cannot_occur()
    v_result = hop.gendirectcall(ll_newdict, cDICT)
    if r_dict.r_rdict_eqfn.lowleveltype != lltype.Void:
        cname = hop.inputconst(lltype.Void, 'fnkeyeq')
        hop.genop('setfield', [v_result, cname, v_eqfn])
    if r_dict.r_rdict_hashfn.lowleveltype != lltype.Void:
        cname = hop.inputconst(lltype.Void, 'fnkeyhash')
        hop.genop('setfield', [v_result, cname, v_hashfn])
    return v_result

# ____________________________________________________________
#
#  Iteration.

def get_ll_dictiter(DICT):
    return lltype.Ptr(lltype.GcStruct('dictiter',
                                      ('dict', DICT),
                                      ('index', lltype.Signed)))

class DictIteratorRepr(AbstractDictIteratorRepr):

    def __init__(self, r_dict, variant="keys"):
        self.r_dict = r_dict
        self.variant = variant
        self.lowleveltype = get_ll_dictiter(r_dict.lowleveltype)
        self.ll_dictiter = ll_dictiter
        self.ll_dictnext = ll_dictnext_group[variant]


def ll_dictiter(ITERPTR, d):
    iter = lltype.malloc(ITERPTR.TO)
    iter.dict = d
    iter.index = 0
    return iter

def _make_ll_dictnext(kind):
    # make three versions of the following function: keys, values, items
    @jit.look_inside_iff(lambda RETURNTYPE, iter: jit.isvirtual(iter)
                         and (iter.dict is None or
                              jit.isvirtual(iter.dict)))
    @jit.oopspec("dictiter.next%s(iter)" % kind)
    def ll_dictnext(RETURNTYPE, iter):
        # note that RETURNTYPE is None for keys and values
        dict = iter.dict
        if not dict or iter.index >= dict.num_items:
            # clear the reference to the dict and prevent restarts
            iter.dict = lltype.nullptr(lltype.typeOf(iter).TO.dict.TO)
            raise StopIteration
        entry = dict.entries.getitem_clean(iter.index)
        iter.index += 1
        if RETURNTYPE is lltype.Void:
            return None
        elif kind == 'items':
            r = lltype.malloc(RETURNTYPE.TO)
            r.item0 = recast(RETURNTYPE.TO.item0, entry.key)
            r.item1 = recast(RETURNTYPE.TO.item1, entry.value)
            return r
        elif kind == 'keys':
            return entry.key
        elif kind == 'values':
            return entry.value
    return ll_dictnext

ll_dictnext_group = {'keys'  : _make_ll_dictnext('keys'),
                     'values': _make_ll_dictnext('values'),
                     'items' : _make_ll_dictnext('items')}

# _____________________________________________________________
# methods

def ll_get(dict, key, default):
    if d_signed_indexes(dict):
        i = ll_dict_lookup(dict, key, dict.keyhash(key),
                           ll_index_getitem_signed)
        if not i & HIGHEST_BIT:
            return ll_get_value(dict, i, ll_index_getitem_signed)
        else:
            return default
    else:
        i = ll_dict_lookup(dict, key, dict.keyhash(key),
                           ll_index_getitem_int)
        if not i & HIGHEST_BIT:
            return ll_get_value(dict, i, ll_index_getitem_int)
        else:
            return default        

def ll_setdefault(dict, key, default):
    if d_signed_indexes(dict):
        hash = dict.keyhash(key)
        i = ll_dict_lookup(dict, key, hash, ll_index_getitem_signed)
        if not i & HIGHEST_BIT:
            return ll_get_value(dict, i, ll_index_getitem_signed)
        else:
            _ll_dict_setitem_lookup_done(dict, key, default, hash, i,
                                         ll_index_getitem_signed,
                                         ll_index_setitem_signed)
            return default
    else:
        hash = dict.keyhash(key)
        i = ll_dict_lookup(dict, key, hash, ll_index_getitem_int)
        if not i & HIGHEST_BIT:
            return ll_get_value(dict, i, ll_index_getitem_int)
        else:
            _ll_dict_setitem_lookup_done(dict, key, default, hash, i,
                                         ll_index_getitem_int,
                                         ll_index_setitem_int)
            return default


def ll_copy(dict):
    DICT = lltype.typeOf(dict).TO
    dictsize = dict.num_items
    d = DICT.allocate()
    d.entries = lltype.malloc(DICT.entries.TO, dictsize)
    d.indexes = _ll_malloc_indexes(dict.size)
    d.size = dict.size
    d.num_items = dict.num_items
    d.resize_counter = dict.resize_counter
    if hasattr(DICT, 'fnkeyeq'):   d.fnkeyeq   = dict.fnkeyeq
    if hasattr(DICT, 'fnkeyhash'): d.fnkeyhash = dict.fnkeyhash
    ll_dict_copy_indexes(d.size, dict, d)
    rgc.ll_arraycopy(dict.entries, d.entries, 0, 0, dict.num_items)
    return d

def ll_clear(d):
    if (d.size == DICT_INITSIZE and
        d.resize_counter == DICT_RESIZE_START):
        return
    old_entries = d.entries
    d.entries = lltype.typeOf(old_entries).TO.allocate(DICT_ITEMS_INITSIZE)
    d.indexes = _ll_malloc_indexes(DICT_INITSIZE)
    d.size = DICT_INITSIZE
    d.num_items = 0
    d.resize_counter = DICT_RESIZE_START

def ll_update(dic1, dic2):
    entries = dic2.entries
    d2len = dic2.num_items
    i = 0
    while i < d2len:
        entry = entries.getitem_clean(i)
        hash = entries.hash(i)
        key = entry.key
        if d_signed_indexes(dic1):
            j = ll_dict_lookup(dic1, key, hash, ll_index_getitem_signed)
        else:
            j = ll_dict_lookup(dic1, key, hash, ll_index_getitem_int)
        # a separate lookup since it might have changed
        if d_signed_indexes(dic1):
            _ll_dict_setitem_lookup_done(dic1, key, entry.value, hash, j,
                                         ll_index_getitem_signed,
                                         ll_index_setitem_signed)
        else:
            _ll_dict_setitem_lookup_done(dic1, key, entry.value, hash, j,
                                         ll_index_getitem_int,
                                         ll_index_setitem_int)
        i += 1

# this is an implementation of keys(), values() and items()
# in a single function.
# note that by specialization on func, three different
# and very efficient functions are created.

def recast(P, v):
    if isinstance(P, lltype.Ptr):
        return lltype.cast_pointer(P, v)
    else:
        return v

def _make_ll_keys_values_items(kind):
    def ll_kvi(LIST, dic):
        res = LIST.ll_newlist(dic.num_items)
        entries = dic.entries
        dlen = dic.num_items
        items = res.ll_items()
        i = 0
        while i < dlen:
            ELEM = lltype.typeOf(items).TO.OF
            if ELEM is not lltype.Void:
                entry = entries.getitem_clean(i)
                if kind == 'items':
                    r = lltype.malloc(ELEM.TO)
                    r.item0 = recast(ELEM.TO.item0, entry.key)
                    r.item1 = recast(ELEM.TO.item1, entry.value)
                    items[i] = r
                elif kind == 'keys':
                    items[i] = recast(ELEM, entry.key)
                elif kind == 'values':
                    items[i] = recast(ELEM, entry.value)
            i += 1
        return res
    return ll_kvi

ll_dict_keys   = _make_ll_keys_values_items('keys')
ll_dict_values = _make_ll_keys_values_items('values')
ll_dict_items  = _make_ll_keys_values_items('items')

def ll_contains(d, key):
    if d_signed_indexes(d):
        i = ll_dict_lookup(d, key, d.keyhash(key), ll_index_getitem_signed)
    else:
        i = ll_dict_lookup(d, key, d.keyhash(key), ll_index_getitem_int)
    return not i & HIGHEST_BIT

def ll_popitem(ELEM, dic):
    if dic.num_items == 0:
        raise KeyError
    entry = dic.entries.getitem_clean(dic.num_items - 1)
    r = lltype.malloc(ELEM.TO)
    r.item0 = recast(ELEM.TO.item0, entry.key)
    r.item1 = recast(ELEM.TO.item1, entry.value)
    ll_dict_delitem(dic, entry.key)
    return r

def ll_pop(dic, key):
    if d_signed_indexes(dic):
        i = ll_dict_lookup(dic, key, dic.keyhash(key), ll_index_getitem_signed)
        if not i & HIGHEST_BIT:
            value = ll_get_value(dic, i, ll_index_getitem_signed)
            _ll_dict_del(dic, i, ll_index_getitem_signed,
                         ll_index_setitem_signed)
            return value
        else:
            raise KeyError
    else:
        i = ll_dict_lookup(dic, key, dic.keyhash(key), ll_index_getitem_int)
        if not i & HIGHEST_BIT:
            value = ll_get_value(dic, i, ll_index_getitem_int)
            _ll_dict_del(dic, i, ll_index_getitem_int,
                         ll_index_setitem_int)
            return value
        else:
            raise KeyError

def ll_pop_default(dic, key, dfl):
    try:
        return ll_pop(dic, key)
    except KeyError:
        return dfl
