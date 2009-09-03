from pypy.rpython.lltypesystem import lltype, rstr, rclass, rdict
from pypy.rpython.controllerentry import Controller
from pypy.rpython.annlowlevel import llstr, cast_base_ptr_to_instance
from pypy.rpython.annlowlevel import cast_instance_to_base_ptr
from pypy.rlib.objectmodel import specialize
from pypy.rlib.rweakref import RWeakValueDictionary


class WeakDictController(Controller):
    knowntype = RWeakValueDictionary

    @specialize.arg(1)
    def new(self, valueclass):
        d = lltype.malloc(get_WEAKDICT(valueclass))
        entries = lltype.malloc(WEAKDICTENTRYARRAY, DICT_INITSIZE)
        for i in range(DICT_INITSIZE):
            entries[i].key = pristine_marker
        d.entries = entries
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

entrymeths = {
    'valid': ll_valid,
    'everused': ll_everused,
    }
WEAKDICTENTRYARRAY = lltype.GcArray(WEAKDICTENTRY,
                                    adtmeths=entrymeths,
                                    hints={'weakarray': 'value'})

def ll_get(d, key):
    llkey = llstr(key)
    i = rdict.ll_dict_lookup(d, llkey, llkey.gethash())
    llvalue = d.entries[i].value
    return cast_base_ptr_to_instance(d.valueclass, llvalue)

def ll_set(d, key, value):
    llkey = llstr(key)
    llvalue = cast_instance_to_base_ptr(value)
    i = rdict.ll_dict_lookup(d, llkey, llkey.gethash())
    d.entries[i].key = llkey
    d.entries[i].value = llvalue

dictmeths = {
    'll_get': ll_get,
    'll_set': ll_set,
    'keyeq': None,
    }

@specialize.memo()
def get_WEAKDICT(valueclass):
    adtmeths = dictmeths.copy()
    adtmeths['valueclass'] = valueclass
    WEAKDICT = lltype.GcStruct("weakdict",
                               ("entries", lltype.Ptr(WEAKDICTENTRYARRAY)),
                               adtmeths=adtmeths)
    return WEAKDICT
