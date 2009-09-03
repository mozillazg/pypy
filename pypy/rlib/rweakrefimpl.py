from pypy.rpython.lltypesystem import lltype, rstr, rclass, rdict
from pypy.rpython.controllerentry import Controller
from pypy.rpython.annlowlevel import cast_base_ptr_to_instance
from pypy.rpython.annlowlevel import cast_instance_to_base_ptr, llstr
from pypy.rlib.objectmodel import specialize
from pypy.rlib.rweakref import RWeakValueDictionary


class WeakDictController(Controller):
    knowntype = RWeakValueDictionary

    @specialize.arg(1)
    def new(self, valueclass):
        WEAKDICT = get_WEAKDICT(valueclass)
        d = lltype.malloc(WEAKDICT)
        d.entries = WEAKDICT.entries.TO.allocate(DICT_INITSIZE)
        d.num_pristine_entries = DICT_INITSIZE
        return d

    def get_get(self, d):
        return d.ll_get

    def get_set(self, d):
        return d.ll_set


pristine_marker = lltype.malloc(rstr.STR, 0)
DICT_INITSIZE = 8

WEAKDICTENTRY = lltype.Struct("weakdictentry",
                              ("key", lltype.Ptr(rstr.STR)),
                              ("value", rclass.OBJECTPTR))

def ll_valid(entries, i):
    key = entries[i].key
    return key != pristine_marker and bool(key)

def ll_everused(entries, i):
    key = entries[i].key
    return key != pristine_marker

str_fasthashfn = rstr.string_repr.get_ll_fasthash_function()

def ll_hash(entries, i):
    return str_fasthashfn(entries[i].key)

def ll_malloc_entries_and_initialize(ENTRIES, n):
    entries = lltype.malloc(ENTRIES, n, zero=True)
    for i in range(n):
        entries[i].key = pristine_marker
    return entries

entrymeths = {
    'allocate': lltype.typeMethod(ll_malloc_entries_and_initialize),
    'delete': rdict._ll_free_entries,
    'valid': ll_valid,
    'everused': ll_everused,
    'hash': ll_hash,
    }
WEAKDICTENTRYARRAY = lltype.GcArray(WEAKDICTENTRY,
                                    adtmeths=entrymeths,
                                    hints={'weakarray': 'value'})

def ll_get(d, key):
    llkey = llstr(key)
    hash = llkey.gethash()
    i = rdict.ll_dict_lookup(d, llkey, hash)
    llvalue = d.entries[i].value
    #print 'get', i, key, hash, llvalue
    return cast_base_ptr_to_instance(d.valueclass, llvalue)

def ll_set(d, key, value):
    llkey = llstr(key)
    llvalue = cast_instance_to_base_ptr(value)
    hash = llkey.gethash()
    i = rdict.ll_dict_lookup(d, llkey, hash)
    everused = d.entries.everused(i)
    #print 'set', i, key, hash, llvalue
    d.entries[i].key = llkey
    d.entries[i].value = llvalue
    if not everused:
        d.num_pristine_entries -= 1
        #print 'num_pristine_entries:', d.num_pristine_entries
        if d.num_pristine_entries <= len(d.entries) / 3:
            ll_weakdict_resize(d)
    else:
        pass   #print 'entry reused'

def ll_weakdict_resize(d):
    # first set num_items to its correct, up-to-date value
    #print 'in ll_weakdict_resize'
    entries = d.entries
    num_items = 0
    for i in range(len(entries)):
        if entries.valid(i):
            num_items += 1
    d.num_items = num_items
    #print 'num_items:', num_items
    rdict.ll_dict_resize(d)
    #print 'resized.'

str_keyeq = lltype.staticAdtMethod(rstr.string_repr.get_ll_eq_function())

dictmeths = {
    'll_get': ll_get,
    'll_set': ll_set,
    'keyeq': str_keyeq,
    'paranoia': False,
    }

@specialize.memo()
def get_WEAKDICT(valueclass):
    adtmeths = dictmeths.copy()
    adtmeths['valueclass'] = valueclass
    WEAKDICT = lltype.GcStruct("weakdict",
                               ("num_items", lltype.Signed),
                               ("num_pristine_entries", lltype.Signed),
                               ("entries", lltype.Ptr(WEAKDICTENTRYARRAY)),
                               adtmeths=adtmeths)
    return WEAKDICT
