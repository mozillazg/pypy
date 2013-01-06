from pypy.objspace.flow.model import Constant
from pypy.rpython.lltypesystem import lltype, llmemory, rclass, rdict
from pypy.rpython.lltypesystem.lloperation import llop
from pypy.rpython.lltypesystem.llmemory import weakref_create, weakref_deref
from pypy.rpython.rclass import getinstancerepr
from pypy.rpython.rmodel import Repr
from pypy.rlib.rweakref import RWeakKeyDictionary
from pypy.rlib import jit
from pypy.rlib.debug import ll_assert
from pypy.rlib.objectmodel import compute_identity_hash


# Warning: this implementation of RWeakKeyDictionary is not exactly
# leaking, but can keep around some values for a long time, even after
# the corresponding keys were freed.  They will be eventually freed if
# you continue to manipulate the dictionary.  Avoid to use this if the
# values are objects that might keep alive tons of memory.


class WeakKeyDictRepr(Repr):
    def __init__(self, rtyper):
        self.rtyper = rtyper
        self.lowleveltype = lltype.Ptr(WEAKDICT)
        self.dict_cache = {}

    def convert_const(self, weakdict):
        if not isinstance(weakdict, RWeakKeyDictionary):
            raise TypeError("expected an RWeakKeyDictionary: %r" % (
                weakdict,))
        try:
            key = Constant(weakdict)
            return self.dict_cache[key]
        except KeyError:
            self.setup()
            if weakdict.length() != 0:
                raise TypeError("got a non-empty prebuilt RWeakKeyDictionary")
            l_dict = ll_new_weakdict()
            self.dict_cache[key] = l_dict
            return l_dict

    def rtype_method_get(self, hop):
        r_object = getinstancerepr(self.rtyper, None)
        v_d, v_key = hop.inputargs(self, r_object)
        hop.exception_cannot_occur()
        v_result = hop.gendirectcall(ll_get, v_d, v_key)
        v_result = hop.genop("cast_pointer", [v_result],
                             resulttype=hop.r_result.lowleveltype)
        return v_result

    def rtype_method_set(self, hop):
        r_object = getinstancerepr(self.rtyper, None)
        v_d, v_key, v_value = hop.inputargs(self, r_object, r_object)
        hop.exception_cannot_occur()
        if hop.args_s[2].is_constant() and hop.args_s[2].const is None:
            hop.gendirectcall(ll_set_null, v_d, v_key)
        else:
            hop.gendirectcall(ll_set, v_d, v_key, v_value)

    def rtype_method_length(self, hop):
        v_d, = hop.inputargs(self)
        hop.exception_cannot_occur()
        return hop.gendirectcall(ll_length, v_d)


def specialize_make_weakdict(hop):
    hop.exception_cannot_occur()
    v_d = hop.gendirectcall(ll_new_weakdict)
    return v_d

# ____________________________________________________________


NULLVALUE = lltype.nullptr(rclass.OBJECTPTR.TO)
WEAKDICTENTRY = lltype.Struct("weakdictentry",
                              ("key", llmemory.WeakRefPtr),
                              ("value", rclass.OBJECTPTR),
                              ("f_hash", lltype.Signed))

def ll_debugrepr(x):
    if x:
        h = compute_identity_hash(x)
    else:
        h = 0
    return '<%x>' % (h,)

def ll_valid(entries, index):
    if index < 0:
        return False
    key = entries[index].key
    if not key:
        return False
    elif weakref_deref(rclass.OBJECTPTR, key):
        return True
    else:
        # The entry might be a dead weakref still holding a strong
        # reference to the value; for this case, we clear the old
        # value from the entry, if any.
        entries[index].value = NULLVALUE
        return False

entrymeths = {
    'allocate': lltype.typeMethod(rdict._ll_malloc_entries),
    'hash': rdict.ll_hash_from_cache,
    'no_direct_compare': True,
    'clear_key': lambda : llmemory.dead_wref,
    'clear_value': lambda : lltype.nullptr(rclass.OBJECTPTR.TO),
    'valid': ll_valid,
    }
WEAKDICTENTRYARRAY = lltype.GcArray(WEAKDICTENTRY,
                                    adtmeths=entrymeths,
                                    hints={'weakarray': 'key'})
# NB. the 'hints' is not used so far ^^^

@jit.dont_look_inside
def ll_new_weakdict():
    d = lltype.malloc(WEAKDICT)
    d.entries = WEAKDICT.entries.TO.allocate(rdict.DICT_ITEMS_INITSIZE)
    d.indexes = WEAKDICT.indexes.TO.allocate(rdict.DICT_INITSIZE)
    d.num_items = 0
    d.resize_counter = rdict.DICT_ITEMS_INITSIZE
    return d

@jit.dont_look_inside
def ll_get(d, llkey):
    hash = compute_identity_hash(llkey)
    llop.debug_print(lltype.Void, "computed key", ll_debugrepr(llkey),
                     hex(hash))
    i = rdict.ll_dict_lookup(d, llkey, hash) & rdict.MASK
    index = d.indexes[i]
    if index < 0:
        llop.debug_print(lltype.Void, i, 'get', hex(hash), "null")
        return NULLVALUE
    llop.debug_print(lltype.Void, i, "getting", index)
    llop.debug_print(lltype.Void, i, 'get', hex(hash),
                     ll_debugrepr(d.entries[index].key),
                     ll_debugrepr(d.entries[index].value))
    # NB. ll_valid() above was just called at least on entry i, so if
    # it is an invalid entry with a dead weakref, the value was reset
    # to NULLVALUE.
    return d.entries[index].value

@jit.dont_look_inside
def ll_set(d, llkey, llvalue):
    if llvalue:
        ll_set_nonnull(d, llkey, llvalue)
    else:
        ll_set_null(d, llkey)

@jit.dont_look_inside
def ll_set_nonnull(d, llkey, llvalue):
    hash = compute_identity_hash(llkey)
    keyref = weakref_create(llkey)    # GC effects here, before the rest
    i = rdict.ll_dict_lookup(d, llkey, hash) & rdict.MASK
    index = d.indexes[i]
    everused = index != rdict.FREE
    if index < 0:
        index = d.num_items
        d.indexes[i] = index
        d.num_items += 1
    d.entries[index].key = keyref
    d.entries[index].value = llvalue
    d.entries[index].f_hash = hash
    llop.debug_print(lltype.Void, i, 'stored', index, d.num_items, hex(hash),
                     ll_debugrepr(llkey),
                     ll_debugrepr(llvalue))
    if not everused:
        d.resize_counter -= 1
        if d.resize_counter <= 0:
            llop.debug_print(lltype.Void, 'RESIZE')
            ll_weakdict_resize(d)

@jit.dont_look_inside
def ll_set_null(d, llkey):
    hash = compute_identity_hash(llkey)
    i = rdict.ll_dict_lookup(d, llkey, hash) & rdict.MASK
    index = d.indexes[i]
    if d.entries.valid(index):
        d.entries[index].key = llmemory.dead_wref
        d.entries[index].value = NULLVALUE
        llop.debug_print(lltype.Void, i, index, 'zero')

def ll_weakdict_resize(d):
    llop.debug_print(lltype.Void, "weakdict resize")
    old_entries = d.entries
    old_indexes = d.indexes
    old_size = len(old_indexes)
    # make a 'new_size' estimate and shrink it if there are many
    # deleted entry markers.  See CPython for why it is a good idea to
    # quadruple the dictionary size as long as it's not too big.
    # count the number of valid entries
    i = 0
    num_items = 0
    while i < d.num_items:
        if old_entries.valid(i):
            num_items += 1
        i += 1
    if num_items > 50000: new_estimate = (num_items + 1) * 2
    else:                 new_estimate = (num_items + 1) * 4
    new_size = rdict.DICT_INITSIZE
    while new_size <= new_estimate:
        new_size *= 2
    #
    new_item_size = new_size // 3 * 2 + 1
    d.entries = lltype.typeOf(old_entries).TO.allocate(new_item_size)
    d.indexes = lltype.typeOf(d).TO.indexes.TO.allocate(new_size)
    d.resize_counter = new_item_size - num_items
    i = 0
    indexes = d.indexes
    j = 0
    while i < old_size:
        index = old_indexes[i]
        if old_entries.valid(index):
            hash = old_entries.hash(index)
            lookup_i = rdict.ll_dict_lookup_clean(d, hash)
            indexes[lookup_i] = j
            llop.debug_print(lltype.Void, "inserting", hex(hash), i,
                             "to", lookup_i, index, "=>", j)
            llop.debug_print(lltype.Void, hex(old_entries[index].f_hash))
            d.entries[j].key = old_entries[index].key
            d.entries[j].value = old_entries[index].value
            d.entries[j].f_hash = old_entries[index].f_hash
            j += 1
        i += 1
    d.num_items = j

def ll_keyeq(d, weakkey1, realkey2):
    # only called by ll_dict_lookup() with the first arg coming from an
    # entry.key, and the 2nd arg being the argument to ll_dict_lookup().
    if not weakkey1:
        assert bool(realkey2)
        return False
    realkey1 = weakref_deref(rclass.OBJECTPTR, weakkey1)
    llop.debug_print(lltype.Void, "comparison", realkey1, realkey2)
    return realkey1 == realkey2

@jit.dont_look_inside
def ll_length(d):
    # xxx slow, but it's only for debugging
    d.resize()
    llop.debug_print(lltype.Void, 'length:', d.num_items)
    return d.num_items

dictmeths = {
    'll_get': ll_get,
    'll_set': ll_set,
    'keyeq': ll_keyeq,
    'paranoia': False,
    'resize': ll_weakdict_resize,
    }

INDEXESARRAY = lltype.GcArray(lltype.Signed,
              adtmeths={'allocate' : lltype.typeMethod(rdict._ll_malloc_indexes)})

WEAKDICT = lltype.GcStruct("weakkeydict",
                           ("num_items", lltype.Signed),
                           ("resize_counter", lltype.Signed),
                           ("indexes", lltype.Ptr(INDEXESARRAY)),
                           ("entries", lltype.Ptr(WEAKDICTENTRYARRAY)),
                           adtmeths=dictmeths)
