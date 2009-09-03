from pypy.objspace.flow.model import Constant
from pypy.rpython.lltypesystem import lltype, rstr, rclass, rdict
from pypy.rpython.rclass import getinstancerepr
from pypy.rpython.rmodel import Repr
from pypy.rlib.rweakref import RWeakValueDictionary


class WeakValueDictRepr(Repr):
    def __init__(self, rtyper):
        self.rtyper = rtyper
        self.lowleveltype = lltype.Ptr(WEAKDICT)
        self.dict_cache = {}

    def convert_const(self, weakdict):
        if not isinstance(weakdict, RWeakValueDictionary):
            raise TyperError("expected an RWeakValueDictionary: %r" % (
                weakdict,))
        try:
            key = Constant(weakdict)
            return self.dict_cache[key]
        except KeyError:
            self.setup()
            l_dict = ll_new_weakdict()
            self.dict_cache[key] = l_dict
            bk = self.rtyper.annotator.bookkeeper
            classdef = bk.getuniqueclassdef(weakdict._valueclass)
            r_key = rstr.string_repr
            r_value = getinstancerepr(self.rtyper, classdef)
            for dictkey, dictvalue in weakdict._dict.items():
                llkey = r_key.convert_const(dictkey)
                llvalue = r_value.convert_const(dictvalue)
                if llvalue:
                    llvalue = lltype.cast_pointer(rclass.OBJECTPTR, llvalue)
                    ll_set(l_dict, llkey, llvalue)
            return l_dict

    def rtype_method_get(self, hop):
        v_d, v_key = hop.inputargs(self, rstr.string_repr)
        hop.exception_cannot_occur()
        v_result = hop.gendirectcall(ll_get, v_d, v_key)
        v_result = hop.genop("cast_pointer", [v_result],
                             resulttype=hop.r_result.lowleveltype)
        return v_result

    def rtype_method_set(self, hop):
        v_d, v_key, v_value = hop.inputargs(self, rstr.string_repr,
                                            hop.args_r[2])
        if hop.args_s[2].is_constant() and hop.args_s[2].const is None:
            value = lltype.nullptr(rclass.OBJECTPTR.TO)
            v_value = hop.inputconst(rclass.OBJECTPTR, value)
        else:
            v_value = hop.genop("cast_pointer", [v_value],
                                resulttype=rclass.OBJECTPTR)
        hop.exception_cannot_occur()
        hop.gendirectcall(ll_set, v_d, v_key, v_value)


def specialize_make_weakdict(hop):
    hop.exception_cannot_occur()
    v_d = hop.gendirectcall(ll_new_weakdict)
    return v_d

# ____________________________________________________________


pristine_marker = lltype.malloc(rstr.STR, 0, zero=True)
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

def ll_new_weakdict():
    d = lltype.malloc(WEAKDICT)
    d.entries = WEAKDICT.entries.TO.allocate(DICT_INITSIZE)
    d.num_pristine_entries = DICT_INITSIZE
    return d

def ll_get(d, llkey):
    hash = llkey.gethash()
    i = rdict.ll_dict_lookup(d, llkey, hash)
    llvalue = d.entries[i].value
    #print 'get', i, key, hash, llvalue
    return llvalue

def ll_set(d, llkey, llvalue):
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

WEAKDICT = lltype.GcStruct("weakdict",
                           ("num_items", lltype.Signed),
                           ("num_pristine_entries", lltype.Signed),
                           ("entries", lltype.Ptr(WEAKDICTENTRYARRAY)),
                           adtmeths=dictmeths)
