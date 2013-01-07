from pypy.objspace.flow.model import Constant
from pypy.rpython.lltypesystem import lltype, llmemory, rstr, rclass, rdict
from pypy.rpython.lltypesystem.llmemory import weakref_create, weakref_deref
from pypy.rpython.lltypesystem.lloperation import llop
from pypy.rpython.rclass import getinstancerepr
from pypy.rpython.rint import signed_repr
from pypy.rpython.rmodel import Repr
from pypy.rlib.rweakref import RWeakValueDictionary
from pypy.rlib import jit


class WeakValueDictRepr(Repr):
    def __init__(self, rtyper, r_key):
        self.rtyper = rtyper
        self.r_key = r_key

        fasthashfn = r_key.get_ll_fasthash_function()
        self.ll_keyhash = r_key.get_ll_hash_function()
        ll_keyeq = lltype.staticAdtMethod(r_key.get_ll_eq_function())

        def ll_valid(entries, index):
            if index < 0:
                return False
            value = entries[index].value
            return bool(value) and bool(weakref_deref(rclass.OBJECTPTR, value))

        def ll_everused(entries, i):
            return bool(entries[i].value)

        def ll_hash(entries, i):
            return fasthashfn(entries[i].key)

        entrymeths = {
            'allocate': lltype.typeMethod(rdict._ll_malloc_entries),
            'valid': ll_valid,
            'everused': ll_everused,
            'hash': ll_hash,
            }
        WEAKDICTENTRY = lltype.Struct("weakdictentry",
                                      ("key", r_key.lowleveltype),
                                      ("value", llmemory.WeakRefPtr))
        WEAKDICTENTRYARRAY = lltype.GcArray(WEAKDICTENTRY,
                                            adtmeths=entrymeths,
                                            hints={'weakarray': 'value'})

        WEAKINDEXESARRAY = lltype.GcArray(lltype.Signed,
           adtmeths={'allocate': lltype.typeMethod(rdict._ll_malloc_indexes)})
        # NB. the 'hints' is not used so far ^^^

        dictmeths = {
            'll_get': self.ll_get,
            'll_set': self.ll_set,
            'keyeq': ll_keyeq,
            'paranoia': False,
            'resize': self.ll_weakdict_resize,
            }

        self.WEAKDICT = lltype.GcStruct(
            "weakvaldict",
            ("num_items", lltype.Signed),
            ("resize_counter", lltype.Signed),
            ('indexes', lltype.Ptr(WEAKINDEXESARRAY)),
            ("entries", lltype.Ptr(WEAKDICTENTRYARRAY)),
            adtmeths=dictmeths)

        self.lowleveltype = lltype.Ptr(self.WEAKDICT)
        self.dict_cache = {}

    def convert_const(self, weakdict):
        if not isinstance(weakdict, RWeakValueDictionary):
            raise TypeError("expected an RWeakValueDictionary: %r" % (
                weakdict,))
        try:
            key = Constant(weakdict)
            return self.dict_cache[key]
        except KeyError:
            self.setup()
            l_dict = self.ll_new_weakdict()
            self.dict_cache[key] = l_dict
            bk = self.rtyper.annotator.bookkeeper
            classdef = bk.getuniqueclassdef(weakdict._valueclass)
            r_value = getinstancerepr(self.rtyper, classdef)
            for dictkey, dictvalue in weakdict._dict.items():
                llkey = self.r_key.convert_const(dictkey)
                llvalue = r_value.convert_const(dictvalue)
                if llvalue:
                    llvalue = lltype.cast_pointer(rclass.OBJECTPTR, llvalue)
                    self.ll_set_nonnull(l_dict, llkey, llvalue)
            return l_dict

    def rtype_method_get(self, hop):
        v_d, v_key = hop.inputargs(self, self.r_key)
        hop.exception_cannot_occur()
        v_result = hop.gendirectcall(self.ll_get, v_d, v_key)
        v_result = hop.genop("cast_pointer", [v_result],
                             resulttype=hop.r_result.lowleveltype)
        return v_result

    def rtype_method_set(self, hop):
        r_object = getinstancerepr(self.rtyper, None)
        v_d, v_key, v_value = hop.inputargs(self, self.r_key, r_object)
        hop.exception_cannot_occur()
        if hop.args_s[2].is_constant() and hop.args_s[2].const is None:
            hop.gendirectcall(self.ll_set_null, v_d, v_key)
        else:
            hop.gendirectcall(self.ll_set, v_d, v_key, v_value)


    # ____________________________________________________________

    @jit.dont_look_inside
    def ll_new_weakdict(self):
        d = lltype.malloc(self.WEAKDICT)
        d.entries = self.WEAKDICT.entries.TO.allocate(rdict.DICT_ITEMS_INITSIZE)
        d.indexes = self.WEAKDICT.indexes.TO.allocate(rdict.DICT_INITSIZE)
        d.num_items = 0
        d.resize_counter = rdict.DICT_ITEMS_INITSIZE
        return d

    @jit.dont_look_inside
    def ll_get(self, d, llkey):
        hash = self.ll_keyhash(llkey)
        i = rdict.ll_dict_lookup(d, llkey, hash) & rdict.MASK
        #llop.debug_print(lltype.Void, i, 'get')
        index = d.indexes[i]
        if index >= 0:
            valueref = d.entries[index].value
            if not valueref:
                return lltype.nullptr(rclass.OBJECTPTR.TO)
            return weakref_deref(rclass.OBJECTPTR, valueref)
        else:
            return lltype.nullptr(rclass.OBJECTPTR.TO)

    @jit.dont_look_inside
    def ll_set(self, d, llkey, llvalue):
        if llvalue:
            self.ll_set_nonnull(d, llkey, llvalue)
        else:
            self.ll_set_null(d, llkey)
    
    @jit.dont_look_inside
    def ll_set_nonnull(self, d, llkey, llvalue):
        hash = self.ll_keyhash(llkey)
        valueref = weakref_create(llvalue)    # GC effects here, before the rest
        i = rdict.ll_dict_lookup(d, llkey, hash) & rdict.MASK
        index = d.indexes[i]
        everused = index != rdict.FREE
        if index < 0:
            index = d.num_items
            d.indexes[i] = index
            d.num_items += 1
        d.entries[index].key = llkey
        d.entries[index].value = valueref
        llop.debug_print(lltype.Void, "set nonnull", i, index)
        #llop.debug_print(lltype.Void, i, 'stored', index, d.num_items, hex(hash),
        #                 ll_debugrepr(llkey),
        #                 ll_debugrepr(llvalue))
        if not everused:
            d.resize_counter -= 1
            if d.resize_counter <= 0:
                #llop.debug_print(lltype.Void, 'RESIZE')
                self.ll_weakdict_resize(d)

    @jit.dont_look_inside
    def ll_set_null(self, d, llkey):
        hash = self.ll_keyhash(llkey)
        i = rdict.ll_dict_lookup(d, llkey, hash) & rdict.MASK
        index = d.indexes[i]
        if d.entries.valid(index):
            # If the entry was ever used, clean up its key and value.
            # We don't store a NULL value, but a dead weakref, because
            # the entry must still be marked as everused().
            d.entries[index].value = llmemory.dead_wref
            if isinstance(self.r_key.lowleveltype, lltype.Ptr):
                d.entries[index].key = self.r_key.convert_const(None)
            else:
                d.entries[index].key = self.r_key.convert_const(0)
            #llop.debug_print(lltype.Void, i, 'zero')

    def ll_weakdict_resize(self, d):
        #llop.debug_print(lltype.Void, "weakdict resize")
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
        i = 0
        indexes = d.indexes
        j = 0
        while i < old_size:
            index = old_indexes[i]
            if old_entries.valid(index):
                hash = old_entries.hash(index)
                lookup_i = rdict.ll_dict_lookup_clean(d, hash)
                indexes[lookup_i] = j
                #llop.debug_print(lltype.Void, "inserting", hex(hash), i,
                #                 "to", lookup_i, index, "=>", j)
                #llop.debug_print(lltype.Void, hex(old_entries[index].f_hash))
                d.entries[j].key = old_entries[index].key
                d.entries[j].value = old_entries[index].value
                j += 1
            i += 1
        d.num_items = j
        d.resize_counter = new_item_size - j

def specialize_make_weakdict(hop):
    hop.exception_cannot_occur()
    v_d = hop.gendirectcall(hop.r_result.ll_new_weakdict)
    return v_d

